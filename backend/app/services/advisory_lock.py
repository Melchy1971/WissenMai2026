from __future__ import annotations

from hashlib import sha256
from typing import Generator
from contextlib import contextmanager

import psycopg
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ResourceLockedApiError


_SCOPE_IDS = {
    "document_import": 1,
    "lifecycle_transition": 2,
    "reindex": 3,
    "job_claim": 4,
    "job_replay": 5,
}


def _stable_int32(value: str) -> int:
    digest = sha256(value.encode()).digest()
    raw = int.from_bytes(digest[:4], "big", signed=False)
    return raw - 0x100000000 if raw > 0x7FFFFFFF else raw


def _is_postgresql(session: Session) -> bool:
    bind = session.get_bind()
    return bind is not None and getattr(bind, "dialect", None) is not None and bind.dialect.name == "postgresql"


class AdvisoryLockService:
    """
    PostgreSQL transaction-scoped advisory locks (pg_try_advisory_xact_lock).
    Locks are released automatically when the enclosing transaction commits or rolls back.
    On non-PostgreSQL backends the acquire calls are silently skipped.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def from_session(cls, session: Session) -> "AdvisoryLockService":
        return cls(session)

    def acquire_document_import_lock(self, *, workspace_id: str, content_hash: str) -> None:
        self._acquire("document_import", f"{workspace_id}:{content_hash}")

    def acquire_lifecycle_lock(self, *, document_id: str) -> None:
        self._acquire("lifecycle_transition", document_id)

    def acquire_reindex_lock(self, *, workspace_id: str, document_id: str | None = None) -> None:
        key = f"{workspace_id}:{document_id}" if document_id else workspace_id
        self._acquire("reindex", key)

    def acquire_job_claim_lock(self, *, job_id: str) -> None:
        self._acquire("job_claim", job_id)

    def acquire_job_replay_lock(self, *, job_id: str) -> None:
        self._acquire("job_replay", job_id)

    def _acquire(self, scope_name: str, resource_key: str) -> None:
        if not _is_postgresql(self._session):
            return
        scope_id = _SCOPE_IDS[scope_name]
        resource_id = _stable_int32(resource_key)
        acquired = self._session.execute(
            text("SELECT pg_try_advisory_xact_lock(:scope, :resource)"),
            {"scope": scope_id, "resource": resource_id},
        ).scalar()
        if not acquired:
            raise ResourceLockedApiError(
                message=f"Resource is currently locked: {scope_name}",
                details={"scope": scope_name, "resource": resource_key},
            )


@contextmanager
def advisory_lock_on_connection(
    connection: psycopg.Connection,
    *,
    scope_name: str,
    resource_key: str,
    wait: bool = False,
) -> Generator[None, None, None]:
    """
    Acquire a transaction-scoped advisory lock on a raw psycopg connection.
    Raises ResourceLockedApiError if the lock cannot be acquired.
    Non-psycopg connections (test fakes) are passed through without locking.
    """
    if not isinstance(connection, psycopg.Connection):
        yield
        return

    scope_id = _SCOPE_IDS[scope_name]
    resource_id = _stable_int32(resource_key)
    with connection.cursor() as cursor:
        if wait:
            cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", (scope_id, resource_id))
            acquired = True
        else:
            cursor.execute("SELECT pg_try_advisory_xact_lock(%s, %s)", (scope_id, resource_id))
            row = cursor.fetchone()
            acquired = row[0] if row else False
    if not acquired:
        raise ResourceLockedApiError(
            message=f"Resource is currently locked: {scope_name}",
            details={"scope": scope_name, "resource": resource_key},
        )
    yield
