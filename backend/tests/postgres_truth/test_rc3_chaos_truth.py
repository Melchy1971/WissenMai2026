"""
RC-3 Advisory Lock Chaos Tests

Verifies that pg_try_advisory_xact_lock prevents race conditions for the 5 lock scopes:
  1. document import by content_hash + workspace_id
  2. document lifecycle transition by document_id
  3. reindex by workspace_id
  4. queue job claim by job_id
  5. retry/dead-letter replay by job_id

Each test simulates concurrent access using separate psycopg connections.
"""
from __future__ import annotations

import threading
from datetime import UTC, datetime
import json
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ResourceLockedApiError
from app.services.advisory_lock import AdvisoryLockService, advisory_lock_on_connection, _SCOPE_IDS, _stable_int32
from app.services.documents.lifecycle_service import DocumentLifecycleService
from app.services.jobs.background_jobs import BackgroundJobAlreadyClaimedError, BackgroundJobService
from app.services.search_index_service import SearchIndexRebuildService
from tests.postgres_truth.support import TruthIds


pytestmark = pytest.mark.postgres_truth

def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def json_payload(truth_ids: TruthIds, filename: str) -> str:
    return json.dumps(
        {
            "filename": f"{truth_ids.slug}-{filename}",
            "mime_type": "text/plain",
            "temp_file_path": f"/tmp/{truth_ids.slug}-{filename}",
        }
    )


def _acquire_lock_on_raw_connection(
    connection: psycopg.Connection,
    *,
    scope_name: str,
    resource_key: str,
) -> bool:
    """Returns True if advisory lock was acquired on the given connection."""
    scope_id = _SCOPE_IDS[scope_name]
    resource_id = _stable_int32(resource_key)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_xact_lock(%s, %s)", (scope_id, resource_id))
        row = cursor.fetchone()
        return bool(row[0]) if row else False


def test_chaos_cleanup_starts_without_stale_state(truth_ids: TruthIds, truth_session: Session) -> None:
    """Baseline: no chaos test rows from previous runs."""
    chaos_doc_id = truth_ids.document_id("chaos-cleanup")
    chaos_job_id = truth_ids.job_id("chaos-cleanup")
    count = truth_session.execute(
        text("SELECT count(*) FROM documents WHERE id = :id"),
        {"id": chaos_doc_id},
    ).scalar_one()
    assert count == 0

    count = truth_session.execute(
        text("SELECT count(*) FROM background_jobs WHERE id = :id"),
        {"id": chaos_job_id},
    ).scalar_one()
    assert count == 0


def test_chaos_advisory_lock_document_import_scope_blocks_concurrent_session(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    postgres_truth_database_url: str,
) -> None:
    """
    Scenario 1 (partial): Two psycopg sessions compete for the document_import advisory lock.
    The first session holds it; the second session must fail to acquire it.
    Verifies: RESOURCE_LOCKED is correctly raised for concurrent import attempts.
    """
    raw_url = _psycopg_url(postgres_truth_database_url)
    resource_key = f"{truth_seed['workspace_id']}:{truth_ids.content_hash('chaos-import-lock')}"

    with psycopg.connect(raw_url) as session1, psycopg.connect(raw_url) as session2:
        session1.autocommit = False
        session2.autocommit = False

        # Session 1 acquires the lock (start a transaction)
        session1.execute("BEGIN")
        acquired_by_1 = _acquire_lock_on_raw_connection(
            session1, scope_name="document_import", resource_key=resource_key
        )
        assert acquired_by_1, "Session 1 should acquire document_import lock"

        # Session 2 tries the same lock while session 1 holds it
        session2.execute("BEGIN")
        acquired_by_2 = _acquire_lock_on_raw_connection(
            session2, scope_name="document_import", resource_key=resource_key
        )
        assert not acquired_by_2, "Session 2 must NOT acquire lock held by session 1"

        # advisory_lock_on_connection raises ResourceLockedApiError when lock is unavailable
        with pytest.raises(ResourceLockedApiError) as exc_info:
            with advisory_lock_on_connection(
                session2,
                scope_name="document_import",
                resource_key=resource_key,
            ):
                pass
        assert exc_info.value.code == "RESOURCE_LOCKED"
        assert "document_import" in exc_info.value.message

        # Release session 1's lock by rolling back
        session1.rollback()
        session2.rollback()

        # After session 1 releases, session 2 can acquire
        session2.execute("BEGIN")
        acquired_after_release = _acquire_lock_on_raw_connection(
            session2, scope_name="document_import", resource_key=resource_key
        )
        assert acquired_after_release, "Session 2 should acquire lock after session 1 releases it"
        session2.rollback()


def test_chaos_lifecycle_lock_blocks_concurrent_session(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    postgres_truth_database_url: str,
) -> None:
    """
    Scenario 2: Two sessions compete for a lifecycle lock on the same document.
    The first holds it; the second must fail (RESOURCE_LOCKED).
    Verifies advisory lock enforces serialized lifecycle transitions.
    """
    raw_url = _psycopg_url(postgres_truth_database_url)
    chaos_doc_id = truth_ids.document_id("chaos-lifecycle-lock")

    with psycopg.connect(raw_url) as session1, psycopg.connect(raw_url) as session2:
        session1.autocommit = False
        session2.autocommit = False

        session1.execute("BEGIN")
        locked = _acquire_lock_on_raw_connection(
            session1, scope_name="lifecycle_transition", resource_key=chaos_doc_id
        )
        assert locked

        session2.execute("BEGIN")
        blocked = _acquire_lock_on_raw_connection(
            session2, scope_name="lifecycle_transition", resource_key=chaos_doc_id
        )
        assert not blocked, "Lifecycle lock must block concurrent access to same document"

        session1.rollback()
        session2.rollback()


def test_chaos_reindex_lock_blocks_concurrent_session(
    truth_seed: dict[str, str],
    postgres_truth_database_url: str,
) -> None:
    """
    Scenario 3: Two sessions compete for a reindex lock on the same workspace.
    Verifies only one reindex can run at a time per workspace.
    """
    raw_url = _psycopg_url(postgres_truth_database_url)

    with psycopg.connect(raw_url) as session1, psycopg.connect(raw_url) as session2:
        session1.autocommit = False
        session2.autocommit = False

        session1.execute("BEGIN")
        locked = _acquire_lock_on_raw_connection(
            session1, scope_name="reindex", resource_key=truth_seed["workspace_id"]
        )
        assert locked

        session2.execute("BEGIN")
        blocked = _acquire_lock_on_raw_connection(
            session2, scope_name="reindex", resource_key=truth_seed["workspace_id"]
        )
        assert not blocked, "Reindex lock must block concurrent reindex for same workspace"

        # Global reindex uses different key and does NOT block
        global_key = "__global__"
        not_blocked = _acquire_lock_on_raw_connection(
            session2, scope_name="reindex", resource_key=global_key
        )
        assert not_blocked, "Reindex lock on different key must NOT block"

        session1.rollback()
        session2.rollback()


def test_chaos_lifecycle_and_reindex_locks_are_independent(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    postgres_truth_database_url: str,
) -> None:
    """
    Scenario: Lifecycle lock and reindex lock are different scopes and do NOT block each other.
    Verifies: archive-during-reindex and delete-during-search do not deadlock.
    """
    raw_url = _psycopg_url(postgres_truth_database_url)
    chaos_doc_id = truth_ids.document_id("chaos-lifecycle-reindex")

    with psycopg.connect(raw_url) as session1, psycopg.connect(raw_url) as session2:
        session1.autocommit = False
        session2.autocommit = False

        session1.execute("BEGIN")
        got_lifecycle = _acquire_lock_on_raw_connection(
            session1, scope_name="lifecycle_transition", resource_key=chaos_doc_id
        )
        assert got_lifecycle

        session2.execute("BEGIN")
        # Reindex on same workspace uses a DIFFERENT scope → not blocked
        got_reindex = _acquire_lock_on_raw_connection(
            session2, scope_name="reindex", resource_key=truth_seed["workspace_id"]
        )
        assert got_reindex, "Lifecycle and reindex locks are independent scopes"

        session1.rollback()
        session2.rollback()


@pytest.mark.m4b_gate
def test_chaos_two_workers_claiming_same_job_only_one_succeeds(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    """
    Scenario 6: Two background workers race to claim the same pending job.
    The advisory lock (scope: job_claim) ensures only one worker can claim.
    The losing worker raises BackgroundJobAlreadyClaimedError.
    """
    now = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    chaos_job_id = truth_ids.job_id("chaos-claim")
    truth_session.execute(
        text(
            """
            insert into background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) values (
                :id, 'document_import', 'pending', :workspace_id, :user_id,
                cast(:payload as jsonb), null,
                0, 1, 'pending', null, null,
                0, null, null, :now, null, null
            )
            """
        ),
        {
            "id": chaos_job_id,
            "workspace_id": truth_seed["workspace_id"],
            "user_id": truth_seed["user_id"],
            "payload": json_payload(truth_ids, "chaos-test.txt"),
            "now": now,
        },
    )
    truth_session.commit()

    results: list[str] = []
    errors: list[Exception] = []
    barrier = threading.Barrier(2, timeout=10)

    def claim_job(worker_id: str) -> None:
        from app.db.session import get_engine
        from sqlalchemy.orm import Session as SA_Session

        with SA_Session(get_engine()) as session:
            service = BackgroundJobService.from_session(session)
            barrier.wait()
            try:
                service.claim_job(job_id=chaos_job_id, worker_id=worker_id)
                results.append(f"claimed-{worker_id}")
            except BackgroundJobAlreadyClaimedError:
                results.append(f"blocked-{worker_id}")
            except Exception as exc:
                errors.append(exc)

    t1 = threading.Thread(target=claim_job, args=("worker-A",))
    t2 = threading.Thread(target=claim_job, args=("worker-B",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not errors, f"Unexpected errors: {errors}"
    claimed = [r for r in results if r.startswith("claimed-")]
    blocked = [r for r in results if r.startswith("blocked-")]
    assert len(claimed) == 1, f"Exactly one worker must claim the job, got: {results}"
    assert len(blocked) == 1, f"Exactly one worker must be blocked, got: {results}"


def test_chaos_dead_letter_replay_blocks_concurrent_session(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    postgres_truth_database_url: str,
) -> None:
    """
    Scenario 7: Two sessions compete for a job_replay advisory lock.
    Verifies: dead-letter replay is serialized — no double-replay is possible.
    """
    raw_url = _psycopg_url(postgres_truth_database_url)
    job_id = truth_ids.job_id("chaos-replay-lock")

    with psycopg.connect(raw_url) as session1, psycopg.connect(raw_url) as session2:
        session1.autocommit = False
        session2.autocommit = False

        session1.execute("BEGIN")
        locked = _acquire_lock_on_raw_connection(
            session1, scope_name="job_replay", resource_key=job_id
        )
        assert locked, "Session 1 must acquire replay lock"

        session2.execute("BEGIN")
        blocked = _acquire_lock_on_raw_connection(
            session2, scope_name="job_replay", resource_key=job_id
        )
        assert not blocked, "Session 2 must NOT acquire replay lock while session 1 holds it"

        session1.rollback()
        session2.rollback()


def test_chaos_job_claim_and_replay_locks_are_independent(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    postgres_truth_database_url: str,
) -> None:
    """
    Verifies: job_claim and job_replay are different scopes — claiming a job
    does not block replaying a DIFFERENT job.
    """
    raw_url = _psycopg_url(postgres_truth_database_url)
    claim_job_id = truth_ids.job_id("chaos-independent-claim")
    replay_job_id = truth_ids.job_id("chaos-independent-replay")

    with psycopg.connect(raw_url) as session1, psycopg.connect(raw_url) as session2:
        session1.autocommit = False
        session2.autocommit = False

        session1.execute("BEGIN")
        got_claim = _acquire_lock_on_raw_connection(
            session1, scope_name="job_claim", resource_key=claim_job_id
        )
        assert got_claim

        session2.execute("BEGIN")
        got_replay = _acquire_lock_on_raw_connection(
            session2, scope_name="job_replay", resource_key=replay_job_id
        )
        assert got_replay, "job_claim and job_replay on different jobs are fully independent"

        session1.rollback()
        session2.rollback()


@pytest.mark.m4c_gate
def test_chaos_source_status_live_lookup_reflects_lifecycle_transitions(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    """
    Scenario 4/source_status: Live source_status lookup returns current document lifecycle state.
    Verifies: list_document_live_statuses correctly reflects transitions active → archived → deleted,
    and returns 'missing' for non-existent documents.
    """
    from app.services.chat.persistence_service import ChatPersistenceService

    doc_id = truth_ids.document_id("chaos-live-status")
    fake_id = truth_ids.document_id("chaos-live-status-missing")

    # Insert a minimal document in active state
    # import_status='pending' satisfies ck_documents_readable_status_requires_current_version
    truth_session.execute(
        text(
            """
            insert into documents (id, workspace_id, owner_user_id, title, source_type, mime_type,
                content_hash, import_status, lifecycle_status)
            values (:id, :workspace_id, :user_id, 'Chaos Live', 'upload', 'text/plain',
                'chaos-live-hash', 'pending', 'active')
            """
        ),
        {"id": doc_id, "workspace_id": truth_seed["workspace_id"], "user_id": truth_seed["user_id"]},
    )
    truth_session.commit()

    svc = ChatPersistenceService.from_session(truth_session)

    # Live lookup returns "active"
    statuses = svc.list_document_live_statuses([doc_id])
    assert statuses.get(doc_id) == "active", f"Expected active, got {statuses}"

    # Missing document returns "missing"
    missing = svc.list_document_live_statuses([fake_id])
    assert missing.get(fake_id) == "missing", f"Expected missing, got {missing}"

    # Batch lookup: active + missing in one call
    batch = svc.list_document_live_statuses([doc_id, fake_id])
    assert batch[doc_id] == "active"
    assert batch[fake_id] == "missing"

    # Transition to archived → live lookup reflects new state
    truth_session.execute(
        text("UPDATE documents SET lifecycle_status = 'archived' WHERE id = :id"),
        {"id": doc_id},
    )
    truth_session.commit()
    truth_session.expire_all()

    statuses_archived = svc.list_document_live_statuses([doc_id])
    assert statuses_archived.get(doc_id) == "archived", f"Expected archived, got {statuses_archived}"

    # Transition to deleted → live lookup reflects new state
    truth_session.execute(
        text("UPDATE documents SET lifecycle_status = 'deleted' WHERE id = :id"),
        {"id": doc_id},
    )
    truth_session.commit()
    truth_session.expire_all()

    statuses_deleted = svc.list_document_live_statuses([doc_id])
    assert statuses_deleted.get(doc_id) == "deleted", f"Expected deleted, got {statuses_deleted}"
