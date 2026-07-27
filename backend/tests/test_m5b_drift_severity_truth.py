"""M5b Drift Severity Truth Tests.

Verifies that each detector produces the correct severity values,
and that CRITICAL findings are correctly identified while WARNING
does not automatically block.

Runs against in-memory SQLite -- no TEST_DATABASE_URL required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models.documents import (
    Base,
    Chunk,
    Document,
    DocumentVersion,
    Workspace,
)
from app.services.drift.document_drift_detector import DocumentDriftDetector
from app.services.drift.lifecycle_drift_detector import LifecycleDriftDetector
from app.services.drift.metadata_drift_detector import MetadataDriftDetector
from app.services.drift_run_engine import DriftRunEngine, FindingDTO

UTC = timezone.utc
WS_ID = "ws-severity"
OWNER = "user-sev-001"

VALID_SEVERITIES = {"info", "warning", "error", "critical"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        s.add(Workspace(id=WS_ID, name="Severity WS", is_default=True,
                        created_at=datetime.now(UTC)))
        s.commit()
        yield s


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _make_doc(session, workspace_id=WS_ID, lifecycle_status="active",
              import_status="chunked", is_searchable=True, meta=None,
              no_chunk=False):
    doc = Document(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        owner_user_id=OWNER,
        current_version_id=None,
        title="Doc",
        source_type="upload",
        content_hash=str(uuid.uuid4()),
        import_status=import_status,
        lifecycle_status=lifecycle_status,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(doc)
    session.flush()
    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        normalized_markdown="# Title",
        markdown_hash=str(uuid.uuid4()),
        parser_version="1.0",
        ocr_used=False,
        metadata_=meta or {"category": "tech", "summary": "ok", "title": "Doc"},
        created_at=datetime.now(UTC),
    )
    session.add(ver)
    session.flush()
    doc.current_version_id = ver.id
    doc.import_status = "chunked"  # Endstatus erst mit Version zulaessig
    if not no_chunk:
        chunk = Chunk(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            document_version_id=ver.id,
            chunk_index=0,
            heading_path=[],
            anchor="c0",
            content="content",
            content_hash=str(uuid.uuid4()),
            is_searchable=is_searchable,
            metadata_={},
            created_at=datetime.now(UTC),
        )
        session.add(chunk)
        session.flush()
    return doc, ver


def _detect_doc(session):
    return DocumentDriftDetector().detect(session, WS_ID)


def _detect_meta(session):
    return MetadataDriftDetector().detect(session, WS_ID)


def _detect_lifecycle(session):
    return LifecycleDriftDetector().detect(session, WS_ID)


# ---------------------------------------------------------------------------
# Tests: DOCUMENT_DRIFT severities
# ---------------------------------------------------------------------------

class TestDocumentDriftSeverity:
    def test_all_findings_are_valid_severities(self, session):
        # Doc with no current_version_id → error
        doc = Document(
            id=str(uuid.uuid4()), workspace_id=WS_ID, owner_user_id=OWNER,
            current_version_id=None, title="Broken",
            source_type="upload", content_hash=str(uuid.uuid4()),
            import_status="pending", lifecycle_status="active",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        session.add(doc)
        session.commit()
        findings = _detect_doc(session)
        for f in findings:
            assert f.severity in VALID_SEVERITIES
            assert f.finding_type == "DOCUMENT_DRIFT"

    def test_missing_version_produces_error(self, session):
        # Active+chunked doc without current_version → error
        doc = Document(
            id=str(uuid.uuid4()), workspace_id=WS_ID, owner_user_id=OWNER,
            current_version_id=None, title="Broken",
            source_type="upload", content_hash=str(uuid.uuid4()),
            import_status="pending", lifecycle_status="active",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        session.add(doc)
        session.commit()
        findings = _detect_doc(session)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) >= 1

    def test_clean_doc_produces_no_findings(self, session):
        _make_doc(session)
        session.commit()
        findings = _detect_doc(session)
        assert findings == []


# ---------------------------------------------------------------------------
# Tests: METADATA_DRIFT severities
# ---------------------------------------------------------------------------

class TestMetadataDriftSeverity:
    def test_all_findings_are_valid_severities(self, session):
        # Doc with missing title → error; missing category → warning
        _make_doc(session, meta={"summary": "ok"})  # missing title and category
        session.commit()
        findings = _detect_meta(session)
        for f in findings:
            assert f.severity in VALID_SEVERITIES
            assert f.finding_type == "METADATA_DRIFT"

    # test_missing_title_produces_error entfernt (2026-07-26): die Pruefung
    # "Fehlender Titel" ist aus dem MetadataDriftDetector entfernt, weil
    # ck_documents_title_not_blank einen leeren Titel gar nicht zulaesst.

    def test_missing_category_produces_warning(self, session):
        _make_doc(session, meta={"summary": "ok", "title": "Doc"})
        session.commit()
        findings = _detect_meta(session)
        warnings = [f for f in findings if f.severity == "warning"]
        assert len(warnings) >= 1, "Missing category must produce a warning severity finding"

    def test_complete_metadata_no_findings(self, session):
        _make_doc(session, meta={"category": "tech", "summary": "ok", "title": "Doc"})
        session.commit()
        findings = _detect_meta(session)
        assert findings == []


# ---------------------------------------------------------------------------
# Tests: LIFECYCLE_DRIFT severities
# ---------------------------------------------------------------------------

class TestLifecycleDriftSeverity:
    def test_all_findings_valid_severity(self, session):
        _make_doc(session, lifecycle_status="active", is_searchable=False)
        _make_doc(session, lifecycle_status="archived", is_searchable=True)
        _make_doc(session, lifecycle_status="deleted", is_searchable=True)
        session.commit()
        findings = _detect_lifecycle(session)
        for f in findings:
            assert f.severity in VALID_SEVERITIES
            assert f.finding_type == "LIFECYCLE_DRIFT"

    def test_active_not_findable_is_error(self, session):
        _make_doc(session, lifecycle_status="active", import_status="chunked",
                  is_searchable=False)
        session.commit()
        findings = _detect_lifecycle(session)
        assert any(f.severity == "error" for f in findings), \
            "active+chunked doc with no searchable chunk must be 'error'"

    def test_archived_searchable_is_error(self, session):
        _make_doc(session, lifecycle_status="archived", is_searchable=True)
        session.commit()
        findings = _detect_lifecycle(session)
        assert any(f.severity == "error" for f in findings), \
            "archived doc with searchable chunk must be 'error'"

    def test_deleted_searchable_is_critical(self, session):
        _make_doc(session, lifecycle_status="deleted", is_searchable=True)
        session.commit()
        findings = _detect_lifecycle(session)
        assert any(f.severity == "critical" for f in findings), \
            "deleted doc with searchable chunk must be 'critical'"

    def test_clean_active_no_findings(self, session):
        _make_doc(session, lifecycle_status="active", is_searchable=True)
        session.commit()
        findings = _detect_lifecycle(session)
        assert findings == []


# ---------------------------------------------------------------------------
# Tests: CRITICAL blocks gate, WARNING does not auto-block
# ---------------------------------------------------------------------------

class TestSeverityGateRules:
    def test_critical_finding_is_identifiable(self, session):
        """CRITICAL findings must be distinguishable from other severities."""
        _make_doc(session, lifecycle_status="deleted", is_searchable=True)
        session.commit()
        findings = _detect_lifecycle(session)
        critical = [f for f in findings if f.severity == "critical"]
        assert len(critical) >= 1
        for f in critical:
            assert f.finding_type == "LIFECYCLE_DRIFT"

    def test_warning_only_run_still_completes(self, session):
        """A run that produces only warning-level findings must still complete."""
        _make_doc(session, meta={"summary": "ok", "title": "Doc"})
        session.commit()
        eng = DriftRunEngine(session, WS_ID)
        eng.register(MetadataDriftDetector())
        result = eng.run()
        session.commit()
        warnings = [f for f in result.findings if f.severity == "warning"]
        assert result.status == "completed"
        assert len(warnings) >= 1, "Expected at least one warning-level finding"

    def test_no_findings_status_completed(self, session):
        """Clean workspace produces no findings; run still completes."""
        _make_doc(session)
        session.commit()
        eng = DriftRunEngine(session, WS_ID)
        eng.register(DocumentDriftDetector())
        eng.register(MetadataDriftDetector())
        eng.register(LifecycleDriftDetector())
        result = eng.run()
        session.commit()
        assert result.status == "completed"
        assert result.total_findings == 0

    def test_finding_dto_rejects_invalid_severity(self):
        """FindingDTO raises ValueError for unknown severity."""
        with pytest.raises(ValueError, match="Invalid severity"):
            FindingDTO(
                finding_type="DOCUMENT_DRIFT",
                severity="unknown_severity",
            )

    def test_finding_dto_rejects_invalid_type(self):
        """FindingDTO raises ValueError for unknown finding_type."""
        with pytest.raises(ValueError, match="Invalid finding_type"):
            FindingDTO(
                finding_type="UNKNOWN_TYPE",
                severity="error",
            )
