from types import SimpleNamespace

from app.core.errors import ServiceUnavailableApiError
from app.models.documents import Chunk, Document
from app.services.search_index_service import SEARCH_VECTOR_INDEX, SearchIndexRebuildService


class FakeExecuteResult:
    def __init__(self, *, rowcount: int = 0, scalar_value=None) -> None:
        self.rowcount = rowcount
        self._scalar_value = scalar_value

    def scalar(self):
        return self._scalar_value


class FakeSession:
    def __init__(self, *, index_exists: bool = True) -> None:
        self._bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
        self.scalar_values = [13, 11]
        self.index_exists = index_exists
        self.executed: list[tuple[object, dict | None]] = []
        self.committed = False

    def get_bind(self):
        return self._bind

    def scalar(self, statement):
        self.executed.append((statement, None))
        return self.scalar_values.pop(0)

    def scalars(self, statement):
        self.executed.append((statement, None))
        return iter(())

    def execute(self, statement, params=None):
        self.executed.append((statement, params))
        rendered = str(statement)
        if "pg_try_advisory_xact_lock" in rendered:
            return FakeExecuteResult(scalar_value=True)
        if "SELECT EXISTS" in rendered:
            return FakeExecuteResult(scalar_value=self.index_exists)
        if "CREATE INDEX" in rendered or "REINDEX INDEX" in rendered:
            return FakeExecuteResult()
        return FakeExecuteResult(rowcount=13)

    def commit(self) -> None:
        self.committed = True


class FakeNonPostgresSession:
    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))


def test_rebuild_search_index_rejects_non_postgresql() -> None:
    service = SearchIndexRebuildService(FakeNonPostgresSession())

    try:
        service.rebuild_search_index()
    except ServiceUnavailableApiError as exc:
        assert exc.message == "Search index rebuild requires PostgreSQL"
    else:
        raise AssertionError("Expected PostgreSQL requirement error")


def test_rebuild_search_index_syncs_searchability_and_reindexes() -> None:
    session = FakeSession(index_exists=True)
    service = SearchIndexRebuildService(session)

    result = service.rebuild_search_index(workspace_id="workspace-1")

    assert result == {
        "workspace_id": "workspace-1",
        "reindexed_chunk_count": 13,
        "reindexed_document_count": 11,
        "index_name": SEARCH_VECTOR_INDEX,
        "index_action": "reindexed",
        "status": "completed",
    }
    rendered = [str(statement) for statement, _ in session.executed]
    assert any("is_searchable" in statement for statement in rendered)
    assert any("REINDEX INDEX" in statement for statement in rendered)
    assert session.committed is True


def test_inspect_inconsistencies_rejects_non_postgresql() -> None:
    service = SearchIndexRebuildService(FakeNonPostgresSession())

    try:
        service.inspect_inconsistencies()
    except ServiceUnavailableApiError as exc:
        assert exc.message == "Search index consistency checks require PostgreSQL"
    else:
        raise AssertionError("Expected PostgreSQL requirement error")


def test_inspect_drift_rejects_non_postgresql() -> None:
    service = SearchIndexRebuildService(FakeNonPostgresSession())

    try:
        service.inspect_drift()
    except ServiceUnavailableApiError as exc:
        assert exc.message == "Search index drift checks require PostgreSQL"
    else:
        raise AssertionError("Expected PostgreSQL requirement error")


def test_inspect_inconsistencies_detects_deleted_and_archived_chunks(db_session, document_fixture) -> None:
    bind = db_session.get_bind()
    original_dialect_name = bind.dialect.name
    bind.dialect.name = "postgresql"
    try:
        active_document = db_session.get(Document, document_fixture["document_id"])
        active_chunk = db_session.get(Chunk, document_fixture["chunk_id"])
        assert active_document is not None
        assert active_chunk is not None

        active_chunk.is_searchable = True
        active_chunk.search_vector = "vertragsentwurf"

        archived_document = Document(
            id="00000000-0000-0000-0000-000000000710",
            workspace_id=document_fixture["workspace_id"],
            owner_user_id="user-1",
            current_version_id=None,
            title="Archived indexed",
            source_type="upload",
            mime_type="text/plain",
            content_hash="archived-indexed",
            import_status="chunked",
            lifecycle_status="archived",
            created_at=active_document.created_at,
            updated_at=active_document.updated_at,
        )
        deleted_document = Document(
            id="00000000-0000-0000-0000-000000000711",
            workspace_id=document_fixture["workspace_id"],
            owner_user_id="user-1",
            current_version_id=None,
            title="Deleted indexed",
            source_type="upload",
            mime_type="text/plain",
            content_hash="deleted-indexed",
            import_status="chunked",
            lifecycle_status="deleted",
            created_at=active_document.created_at,
            updated_at=active_document.updated_at,
        )
        db_session.add_all([archived_document, deleted_document])
        db_session.flush()

        archived_chunk = Chunk(
            id="00000000-0000-0000-0000-000000000712",
            document_id=archived_document.id,
            document_version_id=document_fixture["version_id"],
            chunk_index=1,
            heading_path=[],
            anchor="archived-anchor",
            content="archived content",
            is_searchable=True,
            search_vector="archived",
            content_hash="archived-content-hash",
            token_estimate=5,
            metadata_={},
            created_at=active_document.created_at,
        )
        deleted_chunk = Chunk(
            id="00000000-0000-0000-0000-000000000713",
            document_id=deleted_document.id,
            document_version_id=document_fixture["version_id"],
            chunk_index=2,
            heading_path=[],
            anchor="deleted-anchor",
            content="deleted content",
            is_searchable=True,
            search_vector="deleted",
            content_hash="deleted-content-hash",
            token_estimate=5,
            metadata_={},
            created_at=active_document.created_at,
        )
        missing_index_chunk = Chunk(
            id="00000000-0000-0000-0000-000000000714",
            document_id=active_document.id,
            document_version_id=document_fixture["version_id"],
            chunk_index=3,
            heading_path=[],
            anchor="missing-anchor",
            content="missing index",
            is_searchable=True,
            search_vector=None,
            content_hash="missing-index-hash",
            token_estimate=5,
            metadata_={},
            created_at=active_document.created_at,
        )
        db_session.add_all([archived_chunk, deleted_chunk, missing_index_chunk])
        db_session.commit()

        report = SearchIndexRebuildService(db_session).inspect_inconsistencies()
    finally:
        bind.dialect.name = original_dialect_name

    assert report["status"] == "inconsistent"
    assert report["missing_index_entries"]["count"] >= 1
    assert "00000000-0000-0000-0000-000000000714" in report["missing_index_entries"]["sample_chunk_ids"]
    assert report["deleted_documents_in_index"]["count"] == 1
    assert report["deleted_documents_in_index"]["sample_document_ids"] == ["00000000-0000-0000-0000-000000000711"]
    assert report["archived_documents_in_active_index"]["count"] == 1
    assert report["archived_documents_in_active_index"]["sample_document_ids"] == ["00000000-0000-0000-0000-000000000710"]
    assert report["orphan_index_entries"]["status"] == "not_applicable"


def test_inspect_drift_detects_missing_deleted_archived_duplicate_and_lifecycle_mismatches(db_session, document_fixture) -> None:
    bind = db_session.get_bind()
    original_dialect_name = bind.dialect.name
    bind.dialect.name = "postgresql"
    try:
        active_document = db_session.get(Document, document_fixture["document_id"])
        active_chunk = db_session.get(Chunk, document_fixture["chunk_id"])
        assert active_document is not None
        assert active_chunk is not None

        active_chunk.is_searchable = False
        active_chunk.search_vector = "active-hidden"

        archived_document = Document(
            id="00000000-0000-0000-0000-000000000810",
            workspace_id=document_fixture["workspace_id"],
            owner_user_id="user-1",
            current_version_id=None,
            title="Archived indexed",
            source_type="upload",
            mime_type="text/plain",
            content_hash="archived-drift",
            import_status="chunked",
            lifecycle_status="archived",
            created_at=active_document.created_at,
            updated_at=active_document.updated_at,
        )
        deleted_document = Document(
            id="00000000-0000-0000-0000-000000000811",
            workspace_id=document_fixture["workspace_id"],
            owner_user_id="user-1",
            current_version_id=None,
            title="Deleted indexed",
            source_type="upload",
            mime_type="text/plain",
            content_hash="deleted-drift",
            import_status="chunked",
            lifecycle_status="deleted",
            created_at=active_document.created_at,
            updated_at=active_document.updated_at,
        )
        duplicate_document = Document(
            id="00000000-0000-0000-0000-000000000812",
            workspace_id=document_fixture["workspace_id"],
            owner_user_id="user-1",
            current_version_id=None,
            title="Duplicate indexed",
            source_type="upload",
            mime_type="text/plain",
            content_hash="duplicate-drift",
            import_status="chunked",
            lifecycle_status="active",
            created_at=active_document.created_at,
            updated_at=active_document.updated_at,
        )
        db_session.add_all([archived_document, deleted_document, duplicate_document])
        db_session.flush()

        archived_chunk = Chunk(
            id="00000000-0000-0000-0000-000000000813",
            document_id=archived_document.id,
            document_version_id=document_fixture["version_id"],
            chunk_index=1,
            heading_path=[],
            anchor="archived-anchor",
            content="archived content",
            is_searchable=True,
            search_vector="archived",
            content_hash="archived-content-hash",
            token_estimate=5,
            metadata_={},
            created_at=active_document.created_at,
        )
        deleted_chunk = Chunk(
            id="00000000-0000-0000-0000-000000000814",
            document_id=deleted_document.id,
            document_version_id=document_fixture["version_id"],
            chunk_index=1,
            heading_path=[],
            anchor="deleted-anchor",
            content="deleted content",
            is_searchable=True,
            search_vector="deleted",
            content_hash="deleted-content-hash",
            token_estimate=5,
            metadata_={},
            created_at=active_document.created_at,
        )
        missing_index_chunk = Chunk(
            id="00000000-0000-0000-0000-000000000815",
            document_id=duplicate_document.id,
            document_version_id=document_fixture["version_id"],
            chunk_index=1,
            heading_path=[],
            anchor="dup-anchor",
            content="missing index",
            is_searchable=True,
            search_vector=None,
            content_hash="dup-shared-hash",
            token_estimate=5,
            metadata_={},
            created_at=active_document.created_at,
        )
        duplicate_chunk_a = Chunk(
            id="00000000-0000-0000-0000-000000000816",
            document_id=duplicate_document.id,
            document_version_id=document_fixture["version_id"],
            chunk_index=2,
            heading_path=[],
            anchor="dup-anchor",
            content="duplicate content a",
            is_searchable=True,
            search_vector="duplicate",
            content_hash="dup-shared-hash",
            token_estimate=5,
            metadata_={},
            created_at=active_document.created_at,
        )
        duplicate_chunk_b = Chunk(
            id="00000000-0000-0000-0000-000000000817",
            document_id=duplicate_document.id,
            document_version_id=document_fixture["version_id"],
            chunk_index=3,
            heading_path=[],
            anchor="dup-anchor",
            content="duplicate content b",
            is_searchable=True,
            search_vector="duplicate",
            content_hash="dup-shared-hash",
            token_estimate=5,
            metadata_={},
            created_at=active_document.created_at,
        )
        db_session.add_all([
            archived_chunk,
            deleted_chunk,
            missing_index_chunk,
            duplicate_chunk_a,
            duplicate_chunk_b,
        ])
        db_session.commit()

        report = SearchIndexRebuildService(db_session).inspect_drift()
    finally:
        bind.dialect.name = original_dialect_name

    assert report["status"] == "drifted"
    assert report["severity"] == "critical"
    assert report["drift_score"] == 0
    assert report["chunks_without_index"]["count"] >= 1
    assert "00000000-0000-0000-0000-000000000815" in report["chunks_without_index"]["sample_chunk_ids"]
    assert report["index_without_chunk"]["status"] == "not_applicable"
    assert report["deleted_documents_in_index"]["count"] == 1
    assert report["archived_documents_in_active_index"]["count"] == 1
    assert report["duplicate_index_entries"]["count"] == 1
    assert "00000000-0000-0000-0000-000000000816" in report["duplicate_index_entries"]["sample_chunk_ids"]
    assert "00000000-0000-0000-0000-000000000817" in report["duplicate_index_entries"]["sample_chunk_ids"]
    assert report["invalid_lifecycle_status"]["count"] >= 3
    assert report["invalid_lifecycle_status"]["severity"] == "medium"
    assert "reindexing the workspace" in report["repair_recommendation"]
