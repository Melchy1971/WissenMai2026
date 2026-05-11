from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from sqlalchemy import text
from sqlalchemy.orm import Session


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:48] or "postgres-truth"


def _digest(*parts: str) -> str:
    return hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest()


def _uuid_with_prefix(prefix: str, namespace: str, label: str) -> str:
    tail = _digest(namespace, label)
    return f"{prefix}-{tail[:4]}-{tail[4:8]}-{tail[8:12]}-{tail[12:24]}"


@dataclass(frozen=True)
class TruthIds:
    namespace: str
    slug: str
    workspace_id: str
    other_workspace_id: str
    user_id: str
    other_user_id: str
    session_token: str
    other_session_token: str
    membership_id: str
    other_membership_id: str
    session_id: str
    other_session_id: str

    def document_id(self, label: str) -> str:
        return _uuid_with_prefix("f3000000", self.namespace, f"document:{label}")

    def version_id(self, label: str) -> str:
        return _uuid_with_prefix("f5000000", self.namespace, f"version:{label}")

    def chunk_id(self, label: str) -> str:
        return _uuid_with_prefix("f4000000", self.namespace, f"chunk:{label}")

    def job_id(self, label: str) -> str:
        return f"truth-{self.slug}-job-{label}"

    def chat_session_id(self, label: str) -> str:
        return f"truth-{self.slug}-chat-session-{label}"

    def chat_message_id(self, label: str) -> str:
        return f"truth-{self.slug}-chat-message-{label}"

    def citation_id(self, label: str) -> str:
        return f"truth-{self.slug}-citation-{label}"

    def content_hash(self, label: str) -> str:
        return f"truth-{self.slug}-hash-{label}-{_digest(self.namespace, label)[:12]}"

    def term(self, label: str = "retrieval") -> str:
        return f"truth{_digest(self.namespace, label)[:20]}"


def make_truth_ids(nodeid: str) -> TruthIds:
    namespace = _digest(nodeid)[:20]
    slug = _slug(nodeid)
    return TruthIds(
        namespace=namespace,
        slug=slug,
        workspace_id=_uuid_with_prefix("f1000000", namespace, "workspace"),
        other_workspace_id=_uuid_with_prefix("f1000000", namespace, "other-workspace"),
        user_id=_uuid_with_prefix("f2000000", namespace, "user"),
        other_user_id=_uuid_with_prefix("f2000000", namespace, "other-user"),
        session_token=f"postgres-truth-session-token-{namespace}",
        other_session_token=f"postgres-truth-other-session-token-{namespace}",
        membership_id=f"truth-{slug}-membership-1",
        other_membership_id=f"truth-{slug}-membership-2",
        session_id=f"truth-{slug}-session-1",
        other_session_id=f"truth-{slug}-session-2",
    )


def assert_no_truth_rows(session: Session) -> None:
    checks = {
        "workspaces": "select count(*) from workspaces where id::text like 'f1000000-%'",
        "users": "select count(*) from users where id::text like 'f2000000-%'",
        "documents": "select count(*) from documents where id::text like 'f3000000-%' or workspace_id::text like 'f1000000-%'",
        "document_versions": """
            select count(*)
            from document_versions v
            left join documents d on d.id = v.document_id
            where v.id::text like 'f5000000-%' or d.workspace_id::text like 'f1000000-%'
        """,
        "document_chunks": """
            select count(*)
            from document_chunks c
            left join documents d on d.id = c.document_id
            where c.id::text like 'f4000000-%' or d.workspace_id::text like 'f1000000-%'
        """,
        "chat_sessions": "select count(*) from chat_sessions where id::text like 'truth-%'",
        "background_jobs": "select count(*) from background_jobs where id::text like 'truth-%' or workspace_id::text like 'f1000000-%'",
    }
    stale = {name: session.execute(text(query)).scalar_one() for name, query in checks.items()}
    assert stale == {name: 0 for name in checks}
