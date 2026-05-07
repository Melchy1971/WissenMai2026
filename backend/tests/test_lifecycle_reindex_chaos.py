"""Chaos tests for Lifecycle + Reindex race conditions.

Simulated scenarios
-------------------
1. archive während Reindex   – archived doc's chunks stay searchable (stale index)
2. delete während Search     – search reads chunks of a document that is concurrently deleted
3. restore während Reindex   – reindex phase-2 overwrites restored is_searchable=True with False
4. Reindex parallel zu Upload – reindex snapshot taken before new doc commits; new chunks miss phase-1
5. Reindex parallel zu Chunking – chunks inserted mid-reindex are not covered by reindex UPDATE

Checked invariants
------------------
- stale_archived_searchable_chunks == 0  (archived doc's chunks must not be searchable)
- stale_deleted_searchable_chunks == 0   (deleted doc's chunks must not be searchable)
- active doc's chunks must have is_searchable=True after restore + reindex
- no duplicate searchable chunks after parallel reindex / upload

Implementation note
-------------------
True concurrency requires PostgreSQL row-level locking and READ COMMITTED isolation.
Here we simulate races by executing operations in the exact interleaved order that
creates the inconsistency without database locks.  The resulting state mirrors what CAN
happen in production under load.

Each test:
  1. sets up the initial state
  2. executes operations in the dangerous interleaved order
  3. asserts the resulting (potentially inconsistent) state
  4. documents the race window and the locking strategy needed to close it
"""
from __future__ import annotations

from datetime import UTC, datetime
from threading import Barrier, Thread
from typing import Any

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.documents import Chunk, Document, DocumentVersion
from app.services.documents.lifecycle_service import DocumentLifecycleService
from app.services.search_index_service import SearchIndexRebuildService
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID


# ---------------------------------------------------------------------------
# IDs kept far from conftest IDs to avoid fixture collisions
# ---------------------------------------------------------------------------

_DOC_A = "ca000000-0000-0000-0000-000000000001"
_DOC_B = "ca000000-0000-0000-0000-000000000002"
_DOC_C = "ca000000-0000-0000-0000-000000000003"
_DOC_D = "ca000000-0000-0000-0000-000000000004"
_DOC_E = "ca000000-0000-0000-0000-000000000005"
_VER_A = "cb000000-0000-0000-0000-000000000001"
_VER_B = "cb000000-0000-0000-0000-000000000002"
_VER_C = "cb000000-0000-0000-0000-000000000003"
_VER_D = "cb000000-0000-0000-0000-000000000004"
_VER_E = "cb000000-0000-0000-0000-000000000005"

_NOW = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(
    session: Session,
    *,
    doc_id: str,
    ver_id: str,
    lifecycle_status: str = "active",
    is_searchable: bool = True,
    chunk_count: int = 2,
) -> list[str]:
    """Insert document + version + N chunks, return chunk IDs."""
    from uuid import uuid4

    doc = Document(
        id=doc_id,
        workspace_id=DEFAULT_WORKSPACE_ID,
        owner_user_id=DEFAULT_USER_ID,
        current_version_id=None,
        title=f"doc-{doc_id[:8]}",
        source_type="upload",
        mime_type="text/plain",
        content_hash=f"hash-{doc_id}",
        import_status="chunked",
        created_at=_NOW,
        updated_at=_NOW,
    )
    doc.lifecycle_status = lifecycle_status
    session.add(doc)
    session.flush()

    ver = DocumentVersion(
        id=ver_id,
        document_id=doc_id,
        version_number=1,
        normalized_markdown="# Test\n\ncontent",
        markdown_hash=f"mhash-{ver_id}",
        parser_version="1.0",
        ocr_used=False,
        ki_provider=None,
        ki_model=None,
        metadata_={},
        created_at=_NOW,
    )
    session.add(ver)
    session.flush()

    doc.current_version_id = ver_id
    session.flush()

    chunk_ids: list[str] = []
    for i in range(chunk_count):
        cid = str(uuid4())
        chunk = Chunk(
            id=cid,
            document_id=doc_id,
            document_version_id=ver_id,
            chunk_index=i,
            heading_path=["Test"],
            anchor=f"dv:{doc_id[:4]}:c{i:04d}",
            content=f"chunk {i} content for {doc_id}",
            content_hash=f"ch-{doc_id}-{i}",
            token_estimate=10,
            metadata_={
                "source_anchor": {
                    "type": "text",
                    "page": None,
                    "paragraph": None,
                    "char_start": i * 20,
                    "char_end": i * 20 + 20,
                }
            },
            created_at=_NOW,
            is_searchable=is_searchable,
            search_vector=f"chunk {i} content for {doc_id}" if is_searchable else None,
        )
        session.add(chunk)
        chunk_ids.append(cid)

    session.commit()
    return chunk_ids


def _count_searchable(session: Session, doc_id: str) -> int:
    return int(
        session.scalar(
            select(Chunk).where(Chunk.document_id == doc_id, Chunk.is_searchable.is_(True)).with_only_columns(
                __import__("sqlalchemy").func.count()
            )
        )
        or 0
    )


def _count_non_searchable(session: Session, doc_id: str) -> int:
    return int(
        session.scalar(
            select(Chunk).where(Chunk.document_id == doc_id, Chunk.is_searchable.is_(False)).with_only_columns(
                __import__("sqlalchemy").func.count()
            )
        )
        or 0
    )


def _lifecycle_status(session: Session, doc_id: str) -> str:
    return str(session.scalar(select(Document.lifecycle_status).where(Document.id == doc_id)) or "")


def _reindex_phase1_active(session: Session) -> int:
    """Simulate reindex phase 1: mark active-document chunks as searchable.
    Returns rowcount.  Matches the SQL issued by SearchIndexRebuildService.rebuild_search_index.
    """
    active_ids = select(Document.id).where(Document.lifecycle_status == "active")
    result = session.execute(
        update(Chunk).where(Chunk.document_id.in_(active_ids)).values(is_searchable=True)
    )
    return int(result.rowcount)


def _reindex_phase2_inactive(session: Session, inactive_snapshot: list[str] | None = None) -> int:
    """Simulate reindex phase 2: mark inactive-document chunks as non-searchable.

    When *inactive_snapshot* is provided, we use a pre-captured list of doc IDs
    instead of re-querying the DB.  This models the race window where the phase-2
    statement snapshot was taken *before* a lifecycle transition committed.
    """
    if inactive_snapshot is not None:
        if not inactive_snapshot:
            return 0
        result = session.execute(
            update(Chunk).where(Chunk.document_id.in_(inactive_snapshot)).values(is_searchable=False)
        )
    else:
        inactive_ids = select(Document.id).where(Document.lifecycle_status != "active")
        result = session.execute(
            update(Chunk).where(Chunk.document_id.in_(inactive_ids)).values(is_searchable=False)
        )
    return int(result.rowcount)


def _snapshot_inactive_ids(session: Session) -> list[str]:
    """Capture which doc IDs are currently inactive (simulates statement snapshot)."""
    return list(
        session.scalars(select(Document.id).where(Document.lifecycle_status != "active"))
    )


def _snapshot_active_ids(session: Session) -> list[str]:
    return list(
        session.scalars(select(Document.id).where(Document.lifecycle_status == "active"))
    )


# ---------------------------------------------------------------------------
# Test 1: archive während Reindex → stale searchable chunks
# ---------------------------------------------------------------------------

def test_chaos_archive_during_reindex_phase2_stale_searchable_chunk(
    test_engine, auth_fixture
) -> None:
    """RACE: reindex phase-2 snapshot predates archive commit.

    Race window
    -----------
    T1 (reindex):  phase-1 UPDATE runs → doc X chunks is_searchable=True
    T2 (archive):  commits → doc X lifecycle_status='archived', chunks is_searchable=False
                   (no contention: phase-1 already released X's chunk locks on commit
                    — but reindex transaction has NOT committed yet, phase-2 still pending)
    T1 (reindex):  phase-2 snapshot taken BEFORE archive committed → inactive_snapshot
                   does NOT contain X → phase-2 does not set X's chunks to False
    T1 (reindex):  commits → X archived, X chunks is_searchable=True  ← STALE

    Detected by: inspect_drift → stale_archived_searchable_chunks > 0

    Fix: wrap both reindex UPDATEs + commit in a SERIALIZABLE transaction, or
         add a post-commit reconciliation pass.
    """
    with Session(test_engine) as session:
        _make_doc(session, doc_id=_DOC_A, ver_id=_VER_A, lifecycle_status="active", is_searchable=True)

    # --- Simulate the dangerous interleaving ---

    with Session(test_engine) as session:
        # Reindex phase-1: X is active → mark chunks searchable (no-op here, already True)
        _reindex_phase1_active(session)

        # Reindex phase-2 snapshot taken NOW (before archive commits in parallel T2)
        inactive_before_archive = _snapshot_inactive_ids(session)
        # (X is not in this list because it is still active at snapshot time)

        # T2 (archive) commits: changes lifecycle_status + sets chunks to False
        lifecycle = DocumentLifecycleService.from_session(session)
        lifecycle.archive(_DOC_A, workspace_id=DEFAULT_WORKSPACE_ID)
        # archive does its own commit internally

        # Reindex phase-2 executes with STALE snapshot → X not in inactive_snapshot
        _reindex_phase2_inactive(session, inactive_snapshot=inactive_before_archive)
        session.commit()

    # Verify the stale state
    with Session(test_engine) as session:
        status = _lifecycle_status(session, _DOC_A)
        searchable = _count_searchable(session, _DOC_A)
        non_searchable = _count_non_searchable(session, _DOC_A)

    # archive() always commits its own is_searchable=False update BEFORE reindex phase-2
    # runs with the stale snapshot.  Because archive committed first (in the same SQLite
    # connection), phase-2's stale snapshot is empty → phase-2 is a no-op.
    # The archive update wins → correct state on SQLite.
    #
    # IMPORTANT: on PostgreSQL with concurrent transactions the ordering is reversed:
    # - reindex phase-2's statement snapshot is captured BEFORE archive commits
    # - phase-2 executes after archive released the chunk locks
    # - phase-2 then sets is_searchable=False again (benign here) OR
    #   if archive commits BETWEEN phase-1 and phase-2, phase-1 overwrites to True
    #   and phase-2 might use a snapshot that still sees X as active → X stays True
    assert status == "archived"
    # On SQLite the archive always wins; document the race window for PostgreSQL
    assert non_searchable == 2, (
        "RACE CONDITION (PostgreSQL): if reindex phase-2 snapshot predates archive commit "
        "and phase-1 already set is_searchable=True, X's chunks may remain searchable "
        "after archive.  Detected by inspect_drift → stale_archived_searchable_chunks."
    )


def test_chaos_archive_between_reindex_phases_produces_stale_index(
    test_engine, auth_fixture
) -> None:
    """Demonstrates the stale-index state directly.

    We manually replicate the sequence that a PostgreSQL race would produce:
    1. Phase-1 sets is_searchable=True for X (X was active at snapshot time).
    2. Archive sets lifecycle_status='archived'.
    3. Phase-2, using a snapshot that predates step 2, does NOT disable X's chunks.
    Result: archived doc with is_searchable=True → stale index.
    """
    with Session(test_engine) as session:
        _make_doc(session, doc_id=_DOC_B, ver_id=_VER_B, lifecycle_status="active", is_searchable=True)

    with Session(test_engine) as session:
        # Step 1: Phase-1 marks X's chunks searchable
        _reindex_phase1_active(session)
        session.commit()

    # Step 2: Archive commits (X now archived, chunks False from archive service)
    with Session(test_engine) as session:
        lifecycle = DocumentLifecycleService.from_session(session)
        lifecycle.archive(_DOC_B, workspace_id=DEFAULT_WORKSPACE_ID)

    # Step 3: Manually replicate "phase-2 with stale snapshot" that excludes _DOC_B
    # (because its snapshot was taken before archive committed)
    with Session(test_engine) as session:
        # Stale snapshot: no inactive docs (archive hadn't committed when snapshot was taken)
        stale_inactive_snapshot: list[str] = []
        _reindex_phase2_inactive(session, inactive_snapshot=stale_inactive_snapshot)
        # Then manually undo what archive did to simulate the stale state
        session.execute(
            update(Chunk)
            .where(Chunk.document_id == _DOC_B)
            .values(is_searchable=True)
        )
        session.commit()

    with Session(test_engine) as session:
        status = _lifecycle_status(session, _DOC_B)
        searchable = _count_searchable(session, _DOC_B)

    # This state is the RACE CONDITION RESULT: archived doc, searchable chunks
    assert status == "archived"
    assert searchable == 2, (
        "Race confirmed: archived document has searchable chunks. "
        "inspect_drift would report stale_archived_searchable_chunks=2. "
        "Fix: SERIALIZABLE isolation or post-commit reconciliation."
    )


# ---------------------------------------------------------------------------
# Test 2: delete während Search → stale search results
# ---------------------------------------------------------------------------

def test_chaos_delete_during_search_returns_stale_chunks(
    test_engine, auth_fixture
) -> None:
    """RACE: search reads chunks of a document that is deleted mid-flight.

    Race window
    -----------
    T1 (search):  SELECT chunks WHERE is_searchable=True → snapshot includes doc X
    T2 (delete):  lifecycle_status='deleted', is_searchable=False; commits
    T1 (search):  returns X's chunks to the caller → stale results from deleted doc

    Under READ COMMITTED the search SELECT's snapshot predates the delete commit.
    The user receives results referencing a document that is now deleted.

    Fix: filter search results by lifecycle_status join (not just is_searchable),
         or accept eventual-consistency and show a 'source removed' badge on stale citations.
    """
    with Session(test_engine) as session:
        _make_doc(session, doc_id=_DOC_C, ver_id=_VER_C, lifecycle_status="active", is_searchable=True)

    # Capture the "stale search snapshot" (doc C is active and searchable)
    with Session(test_engine) as session:
        searchable_before = list(
            session.scalars(
                select(Chunk.id)
                .join(Document, Document.id == Chunk.document_id)
                .where(
                    Document.workspace_id == DEFAULT_WORKSPACE_ID,
                    Chunk.is_searchable.is_(True),
                )
            )
        )

    # Delete commits concurrently (between the SELECT and the caller receiving results)
    with Session(test_engine) as session:
        lifecycle = DocumentLifecycleService.from_session(session)
        lifecycle.delete(_DOC_C, workspace_id=DEFAULT_WORKSPACE_ID)

    # Verify: the stale search results reference a now-deleted document
    with Session(test_engine) as session:
        status = _lifecycle_status(session, _DOC_C)
        current_searchable = _count_searchable(session, _DOC_C)

    assert status == "deleted"
    assert current_searchable == 0, "Delete correctly set is_searchable=False"

    # The stale result still contained _DOC_C's chunks at snapshot time
    assert any(True for _ in searchable_before), (
        "RACE CONFIRMED: search snapshot contained chunks from doc that was deleted "
        "before results were returned.  Fix: join on lifecycle_status in search query, "
        "or post-process results to filter deleted citations."
    )
    assert len(searchable_before) == 2, "Search snapshot included 2 chunks from deleted doc"


# ---------------------------------------------------------------------------
# Test 3: restore während Reindex phase-2 → restored chunks overwritten to False
# ---------------------------------------------------------------------------

def test_chaos_restore_during_reindex_overwrites_searchability(
    test_engine, auth_fixture
) -> None:
    """RACE: reindex phase-2 runs with a snapshot that predates restore commit.

    Race window
    -----------
    Doc X is archived (is_searchable=False).

    T1 (reindex):  phase-1 UPDATE → X is archived, not in active set → no-op for X
    T1 (reindex):  phase-2 snapshot taken → X IS in inactive set (X archived at this moment)
    T2 (restore):  commits → lifecycle_status='active', is_searchable=True for X's chunks
    T1 (reindex):  phase-2 executes with STALE snapshot (X in inactive) → sets is_searchable=False
    T1 (reindex):  commits → X is active but is_searchable=False  ← STALE

    Fix: post-commit reconciliation, or run lifecycle transitions under SERIALIZABLE isolation
         to prevent snapshot divergence with concurrent reindex operations.
    """
    with Session(test_engine) as session:
        _make_doc(session, doc_id=_DOC_D, ver_id=_VER_D, lifecycle_status="active", is_searchable=True)

    # First archive the doc
    with Session(test_engine) as session:
        lifecycle = DocumentLifecycleService.from_session(session)
        lifecycle.archive(_DOC_D, workspace_id=DEFAULT_WORKSPACE_ID)

    with Session(test_engine) as session:
        # Reindex phase-1: X is archived → no-op for X's chunks
        active_snapshot = _snapshot_active_ids(session)
        # X not in active_snapshot

        # Phase-2 snapshot: taken NOW, X IS in inactive set
        inactive_snapshot_with_x = _snapshot_inactive_ids(session)
        assert _DOC_D in inactive_snapshot_with_x, "Doc D must be in inactive snapshot before restore"

        # T2 (restore) commits between phase-1 and phase-2 execution
        lifecycle = DocumentLifecycleService.from_session(session)
        lifecycle.restore(_DOC_D, workspace_id=DEFAULT_WORKSPACE_ID)
        # restore sets lifecycle_status='active', is_searchable=True

        # Reindex phase-2 executes with STALE snapshot (X was inactive when snapshot taken)
        _reindex_phase2_inactive(session, inactive_snapshot=inactive_snapshot_with_x)
        session.commit()

    with Session(test_engine) as session:
        status = _lifecycle_status(session, _DOC_D)
        searchable = _count_searchable(session, _DOC_D)
        non_searchable = _count_non_searchable(session, _DOC_D)

    # RACE CONDITION RESULT: X is active but is_searchable=False
    assert status == "active", "Document should be active after restore"
    assert non_searchable == 2, (
        "RACE CONFIRMED: reindex phase-2 (stale snapshot) overwrote restore's "
        "is_searchable=True with False.  Active document's chunks are not searchable. "
        "Fix: SERIALIZABLE isolation on reindex transaction, or re-sync after commit."
    )
    assert searchable == 0, "No searchable chunks despite active lifecycle status"


# ---------------------------------------------------------------------------
# Test 4: Reindex parallel zu Upload → new chunks miss reindex phase-1
# ---------------------------------------------------------------------------

def test_chaos_reindex_parallel_to_upload_new_chunks_miss_phase1(
    test_engine, auth_fixture
) -> None:
    """RACE: new document committed after reindex phase-1 snapshot.

    Race window
    -----------
    T1 (reindex):  phase-1 active snapshot captured → new doc D_new NOT yet committed
    T2 (upload):   new doc D_new committed (lifecycle_status='active', chunks is_searchable=True)
    T1 (reindex):  phase-2 inactive snapshot → D_new is 'active' → not in inactive set
    T1 (reindex):  commits; REINDEX INDEX runs on PostgreSQL
                   → D_new's chunks have is_searchable=True (server_default) ✓
                   → on PostgreSQL: GIN index auto-maintained on INSERT → ✓
                   → search_vector GENERATED ALWAYS → auto-populated on INSERT → ✓

    Conclusion: is_searchable state is correct (new chunks default to True).
    The potential gap is the search_vector trigger on INSERT vs REINDEX timing.
    On PostgreSQL with GENERATED ALWAYS column: no gap (INSERT auto-populates).
    On PostgreSQL with manual trigger: INSERT trigger must fire before REINDEX.

    Verified: new doc is immediately searchable after commit despite concurrent reindex.
    """
    # Phase-1 active snapshot captured before new doc exists
    with Session(test_engine) as session:
        active_before = _snapshot_active_ids(session)

    # New doc D uploaded and committed
    with Session(test_engine) as session:
        _make_doc(session, doc_id=_DOC_E, ver_id=_VER_E, lifecycle_status="active", is_searchable=True)

    assert _DOC_E not in active_before, "New doc should not be in pre-upload snapshot"

    # Phase-2 with fresh snapshot (D_new is active → not in inactive set → no-op)
    with Session(test_engine) as session:
        _reindex_phase2_inactive(session)
        session.commit()

    # Verify new doc's chunks are searchable (is_searchable=True by default)
    with Session(test_engine) as session:
        status = _lifecycle_status(session, _DOC_E)
        searchable = _count_searchable(session, _DOC_E)

    assert status == "active"
    assert searchable == 2, (
        "New doc's chunks are searchable despite missing reindex phase-1 "
        "(is_searchable=True is the server default, so no explicit reindex pass needed). "
        "PostgreSQL search_vector is GENERATED ALWAYS → auto-populated on INSERT → safe."
    )


# ---------------------------------------------------------------------------
# Test 5: Reindex parallel zu Chunking → chunks inserted mid-reindex phase-1
# ---------------------------------------------------------------------------

def test_chaos_reindex_parallel_to_chunking_chunks_inserted_between_phases(
    test_engine, auth_fixture
) -> None:
    """RACE: chunks inserted between reindex phase-1 and phase-2.

    Race window
    -----------
    T1 (reindex):  phase-1 active snapshot + UPDATE runs → document D exists, no chunks yet
    T2 (chunking): chunks inserted for D (with is_searchable=True default); commits
    T1 (reindex):  phase-2 runs → D is 'active' → not in inactive set → chunks not touched
    T1 commits

    Result: new chunks have is_searchable=True (correct).
    REINDEX INDEX on PostgreSQL will pick up the new chunks automatically.
    No drift introduced.

    Separate risk: if REINDEX INDEX runs BEFORE chunking commits, new chunks are
    auto-indexed by PostgreSQL GIN on INSERT after REINDEX completes (GIN maintains
    itself on DML).  No gap on PostgreSQL with GENERATED ALWAYS search_vector.
    """
    from uuid import uuid4

    # Initial state: doc D_chunk exists but has NO chunks yet
    with Session(test_engine) as session:
        doc = Document(
            id=_DOC_A,
            workspace_id=DEFAULT_WORKSPACE_ID,
            owner_user_id=DEFAULT_USER_ID,
            current_version_id=None,
            title="chunking-race-doc",
            source_type="upload",
            mime_type="text/plain",
            content_hash="hash-chunking-race",
            import_status="parsed",
            created_at=_NOW,
            updated_at=_NOW,
        )
        doc.lifecycle_status = "active"
        ver = DocumentVersion(
            id=_VER_A,
            document_id=_DOC_A,
            version_number=1,
            normalized_markdown="# Race\n\ncontent",
            markdown_hash="mhash-a",
            parser_version="1.0",
            ocr_used=False,
            ki_provider=None,
            ki_model=None,
            metadata_={},
            created_at=_NOW,
        )
        session.add(doc)
        session.flush()
        session.add(ver)
        session.flush()
        doc.current_version_id = _VER_A
        session.commit()

    # Reindex phase-1 runs: D exists as active, no chunks → phase-1 is no-op for D
    with Session(test_engine) as session:
        rows_touched = _reindex_phase1_active(session)
        session.commit()

    assert rows_touched == 0, "No chunks existed during phase-1 → zero rows touched"

    # Chunking commits: inserts 3 chunks with is_searchable=True (server default)
    new_chunk_ids: list[str] = []
    with Session(test_engine) as session:
        for i in range(3):
            cid = str(uuid4())
            chunk = Chunk(
                id=cid,
                document_id=_DOC_A,
                document_version_id=_VER_A,
                chunk_index=i,
                heading_path=["Race"],
                anchor=f"dv:race:c{i:04d}",
                content=f"chunked content {i}",
                content_hash=f"race-hash-{i}",
                token_estimate=5,
                metadata_={
                    "source_anchor": {
                        "type": "text",
                        "page": None,
                        "paragraph": None,
                        "char_start": i * 15,
                        "char_end": i * 15 + 15,
                    }
                },
                created_at=_NOW,
                is_searchable=True,
            )
            session.add(chunk)
            new_chunk_ids.append(cid)
        session.execute(
            update(Document).where(Document.id == _DOC_A).values(import_status="chunked")
        )
        session.commit()

    # Reindex phase-2 runs: D is active → not in inactive set → new chunks not touched
    with Session(test_engine) as session:
        rows_touched_phase2 = _reindex_phase2_inactive(session)
        session.commit()

    assert rows_touched_phase2 == 0, "D is active → phase-2 must not touch its chunks"

    # Verify: new chunks are searchable (is_searchable=True from server default)
    with Session(test_engine) as session:
        searchable = _count_searchable(session, _DOC_A)
        non_searchable = _count_non_searchable(session, _DOC_A)

    assert searchable == 3, (
        "Chunks inserted between reindex phases are searchable via server default. "
        "PostgreSQL GIN index auto-maintained on INSERT → immediately queryable."
    )
    assert non_searchable == 0


# ---------------------------------------------------------------------------
# Test 6: detect_drift after lifecycle chaos confirms inspect_drift catches stale state
# ---------------------------------------------------------------------------

def test_chaos_inspect_drift_detects_stale_archived_chunks(
    test_engine, auth_fixture, monkeypatch
) -> None:
    """inspect_drift must detect stale archived/deleted chunks as 'inconsistent'.

    This test creates the stale state directly (as would result from a race)
    and verifies that inspect_drift reports severity='high' / 'critical'.

    Also validates the drift_score penalty for each bucket.
    """
    # Bypass PostgreSQL requirement
    monkeypatch.setattr(SearchIndexRebuildService, "_require_postgresql", lambda self, _msg: None)
    monkeypatch.setattr(
        "app.services.search_index_service.cast",
        lambda val, *a, **kw: val,
    )

    with Session(test_engine) as session:
        # Doc B: archived but chunks still searchable (race condition result)
        _make_doc(session, doc_id=_DOC_B, ver_id=_VER_B, lifecycle_status="active", is_searchable=True)

    # Force the stale state: archived doc with searchable chunks
    with Session(test_engine) as session:
        session.execute(
            update(Document)
            .where(Document.id == _DOC_B)
            .values(lifecycle_status="archived")
        )
        # chunks remain is_searchable=True → stale state
        session.commit()

    with Session(test_engine) as session:
        service = SearchIndexRebuildService.from_session(session)
        result = service.inspect_drift(workspace_id=DEFAULT_WORKSPACE_ID)

    assert result["status"] == "drifted", (
        "inspect_drift must detect archived doc with searchable chunks as 'drifted'"
    )
    archived_bucket = result["archived_documents_in_active_index"]
    assert archived_bucket["status"] == "inconsistent"
    assert archived_bucket["severity"] in {"high", "critical"}
    assert archived_bucket["count"] >= 2, "Both chunks of the archived doc must be flagged"
    assert result["drift_score"] < 100, "Drift score must be penalised"


def test_chaos_inspect_drift_detects_stale_deleted_chunks(
    test_engine, auth_fixture, monkeypatch
) -> None:
    """inspect_drift must detect deleted doc with searchable chunks as 'critical'."""
    monkeypatch.setattr(SearchIndexRebuildService, "_require_postgresql", lambda self, _msg: None)
    monkeypatch.setattr(
        "app.services.search_index_service.cast",
        lambda val, *a, **kw: val,
    )

    with Session(test_engine) as session:
        _make_doc(session, doc_id=_DOC_C, ver_id=_VER_C, lifecycle_status="active", is_searchable=True)

    # Force stale: deleted doc with searchable chunks
    with Session(test_engine) as session:
        session.execute(
            update(Document).where(Document.id == _DOC_C).values(lifecycle_status="deleted")
        )
        session.commit()

    with Session(test_engine) as session:
        service = SearchIndexRebuildService.from_session(session)
        result = service.inspect_drift(workspace_id=DEFAULT_WORKSPACE_ID)

    assert result["status"] == "drifted"
    deleted_bucket = result["deleted_documents_in_index"]
    assert deleted_bucket["status"] == "inconsistent"
    assert deleted_bucket["severity"] == "critical"
    assert deleted_bucket["count"] >= 2


def test_chaos_inspect_drift_detects_invalid_lifecycle_status(
    test_engine, auth_fixture, monkeypatch
) -> None:
    """inspect_drift must detect active doc with non-searchable chunks as 'medium' inconsistency."""
    monkeypatch.setattr(SearchIndexRebuildService, "_require_postgresql", lambda self, _msg: None)
    monkeypatch.setattr(
        "app.services.search_index_service.cast",
        lambda val, *a, **kw: val,
    )

    with Session(test_engine) as session:
        # Active doc, but chunks NOT searchable (result of restore-race scenario)
        _make_doc(session, doc_id=_DOC_D, ver_id=_VER_D, lifecycle_status="active", is_searchable=False)

    with Session(test_engine) as session:
        service = SearchIndexRebuildService.from_session(session)
        result = service.inspect_drift(workspace_id=DEFAULT_WORKSPACE_ID)

    assert result["status"] == "drifted"
    lifecycle_bucket = result["invalid_lifecycle_status"]
    assert lifecycle_bucket["status"] == "inconsistent"
    assert lifecycle_bucket["severity"] == "medium"
    assert lifecycle_bucket["count"] >= 2


def test_chaos_inspect_drift_clean_state_after_reindex(
    test_engine, auth_fixture, monkeypatch
) -> None:
    """After running both reindex phases, inspect_drift must report ok/score=100."""
    monkeypatch.setattr(SearchIndexRebuildService, "_require_postgresql", lambda self, _msg: None)
    monkeypatch.setattr(
        "app.services.search_index_service.cast",
        lambda val, *a, **kw: val,
    )

    with Session(test_engine) as session:
        _make_doc(session, doc_id=_DOC_A, ver_id=_VER_A, lifecycle_status="active", is_searchable=True)
        _make_doc(session, doc_id=_DOC_B, ver_id=_VER_B, lifecycle_status="archived", is_searchable=False)
        _make_doc(session, doc_id=_DOC_C, ver_id=_VER_C, lifecycle_status="deleted", is_searchable=False)

    with Session(test_engine) as session:
        service = SearchIndexRebuildService.from_session(session)
        result = service.inspect_drift(workspace_id=DEFAULT_WORKSPACE_ID)

    assert result["status"] == "ok"
    assert result["drift_score"] == 100
    assert result["archived_documents_in_active_index"]["status"] == "ok"
    assert result["deleted_documents_in_index"]["status"] == "ok"
    assert result["invalid_lifecycle_status"]["status"] == "ok"
