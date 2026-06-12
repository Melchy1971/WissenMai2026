"""Tests for MetadataDriftDetector.

Runs against in-memory SQLite -- no TEST_DATABASE_URL required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models.documents import Base, Document, DocumentVersion, Workspace  # noqa: F401
from app.models.drift import DriftFinding, DriftRun, DriftSnapshot  # noqa: F401
from app.services.drift.metadata_drift_detector import MetadataDriftDetector

UTC = timezone.utc
WS_ID = "ws-meta-drift"
OWNER_ID = "user-001"


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
    def _fk_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        s.add(Workspace(id=WS_ID, name="Meta Drift WS", is_default=True, created_at=datetime.now(UTC)))
        s.commit()
        yield s


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _doc(title="Valid Title"):
    now = datetime.now(UTC)
    return Document(
        id=str(uuid.uuid4()),
        workspace_id=WS_ID,
        owner_user_id=OWNER_ID,
        current_version_id=None,
        title=title,
        source_type="upload",
        content_hash=str(uuid.uuid4()),
        import_status="chunked",
        lifecycle_status="active",
        created_at=now,
        updated_at=now,
    )


def _ver(doc_id, metadata=None, version_number=1):
    return DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        version_number=version_number,
        normalized_markdown="# Title\n\nContent",
        markdown_hash=str(uuid.uuid4()),
        parser_version="1.0",
        ocr_used=False,
        metadata_=metadata if metadata is not None else {"category": "tech", "summary": "A summary"},
        created_at=datetime.now(UTC),
    )


def _add_doc_with_version(session, title="Valid Title", metadata=None):
    doc = _doc(title=title)
    session.add(doc)
    session.flush()
    ver = _ver(doc.id, metadata=metadata)
    session.add(ver)
    session.flush()
    doc.current_version_id = ver.id
    session.commit()
    return doc, ver


def _detect(session):
    return MetadataDriftDetector().detect(session, WS_ID)


# ---------------------------------------------------------------------------
# Check 1: Fehlender Titel
# ---------------------------------------------------------------------------

class TestMissingTitle:
    def test_empty_title(self, session):
        doc = _doc(title="")
        session.add(doc)
        session.commit()

        findings = _detect(session)
        assert any(
            f.finding_type == "METADATA_DRIFT"
            and f.detail.get("check") == "missing_title"
            and f.severity == "error"
            for f in findings
        )

    def test_whitespace_only_title(self, session):
        doc = _doc(title="   ")
        session.add(doc)
        session.commit()

        findings = _detect(session)
        assert any(
            f.detail.get("check") == "missing_title"
            for f in findings
        )

    def test_valid_title_no_finding(self, session):
        doc, ver = _add_doc_with_version(session, title="A real title")
        findings = _detect(session)
        title_findings = [f for f in findings if f.detail and f.detail.get("check") == "missing_title"]
        assert len(title_findings) == 0


# ---------------------------------------------------------------------------
# Check 2: Fehlende Kategorie
# ---------------------------------------------------------------------------

class TestMissingCategory:
    def test_no_category_key(self, session):
        doc, ver = _add_doc_with_version(session, metadata={"summary": "A summary"})
        findings = _detect(session)
        assert any(
            f.detail.get("check") == "missing_category"
            and f.entity_id == ver.id
            for f in findings
        )

    def test_empty_category_value(self, session):
        doc, ver = _add_doc_with_version(session, metadata={"category": "", "summary": "A summary"})
        findings = _detect(session)
        assert any(f.detail.get("check") == "missing_category" for f in findings)

    def test_whitespace_category(self, session):
        doc, ver = _add_doc_with_version(session, metadata={"category": "  ", "summary": "A summary"})
        findings = _detect(session)
        assert any(f.detail.get("check") == "missing_category" for f in findings)

    def test_present_category_no_finding(self, session):
        doc, ver = _add_doc_with_version(session, metadata={"category": "tech", "summary": "ok"})
        findings = _detect(session)
        cat_findings = [f for f in findings if f.detail and f.detail.get("check") == "missing_category"]
        assert len(cat_findings) == 0


# ---------------------------------------------------------------------------
# Check 3: Fehlende Zusammenfassung
# ---------------------------------------------------------------------------

class TestMissingSummary:
    def test_no_summary_key(self, session):
        doc, ver = _add_doc_with_version(session, metadata={"category": "tech"})
        findings = _detect(session)
        assert any(
            f.detail.get("check") == "missing_summary"
            and f.entity_id == ver.id
            for f in findings
        )

    def test_empty_summary_value(self, session):
        doc, ver = _add_doc_with_version(session, metadata={"category": "tech", "summary": ""})
        findings = _detect(session)
        assert any(f.detail.get("check") == "missing_summary" for f in findings)

    def test_present_summary_no_finding(self, session):
        doc, ver = _add_doc_with_version(session, metadata={"category": "tech", "summary": "A summary"})
        findings = _detect(session)
        sum_findings = [f for f in findings if f.detail and f.detail.get("check") == "missing_summary"]
        assert len(sum_findings) == 0

    def test_null_metadata_triggers_all_required_keys(self, session):
        doc = _doc()
        session.add(doc)
        session.flush()
        ver = _ver(doc.id, metadata={})
        session.add(ver)
        session.flush()
        doc.current_version_id = ver.id
        session.commit()

        findings = _detect(session)
        checks = {f.detail.get("check") for f in findings if f.detail}
        assert "missing_category" in checks
        assert "missing_summary" in checks


# ---------------------------------------------------------------------------
# Check 4: Inkonsistente Metadaten
# ---------------------------------------------------------------------------

class TestInconsistentMetadata:
    def test_single_version_no_inconsistency(self, session):
        doc, ver = _add_doc_with_version(session)
        findings = _detect(session)
        incon = [f for f in findings if f.detail and f.detail.get("check") == "inconsistent_metadata"]
        assert len(incon) == 0

    def test_two_versions_same_keys_no_finding(self, session):
        doc = _doc()
        session.add(doc)
        session.flush()

        v1 = _ver(doc.id, metadata={"category": "tech", "summary": "s1"}, version_number=1)
        v2 = _ver(doc.id, metadata={"category": "finance", "summary": "s2"}, version_number=2)
        session.add_all([v1, v2])
        session.flush()
        doc.current_version_id = v2.id
        session.commit()

        findings = _detect(session)
        incon = [f for f in findings if f.detail and f.detail.get("check") == "inconsistent_metadata"]
        assert len(incon) == 0

    def test_two_versions_different_keys(self, session):
        doc = _doc()
        session.add(doc)
        session.flush()

        v1 = _ver(doc.id, metadata={"category": "tech", "summary": "s1"}, version_number=1)
        v2 = _ver(doc.id, metadata={"category": "finance", "summary": "s2", "extra_key": "x"}, version_number=2)
        session.add_all([v1, v2])
        session.flush()
        doc.current_version_id = v2.id
        session.commit()

        findings = _detect(session)
        assert any(
            f.detail.get("check") == "inconsistent_metadata"
            and f.entity_id == doc.id
            for f in findings
        )

    def test_inconsistency_detail_contains_diff(self, session):
        doc = _doc()
        session.add(doc)
        session.flush()

        v1 = _ver(doc.id, metadata={"category": "tech", "summary": "s1"}, version_number=1)
        v2 = _ver(doc.id, metadata={"category": "finance"}, version_number=2)
        session.add_all([v1, v2])
        session.flush()
        doc.current_version_id = v2.id
        session.commit()

        findings = _detect(session)
        incon = [f for f in findings if f.detail and f.detail.get("check") == "inconsistent_metadata"]
        assert len(incon) == 1
        detail = incon[0].detail
        assert "inconsistent_versions" in detail
        assert len(detail["inconsistent_versions"]) > 0


# ---------------------------------------------------------------------------
# All findings are METADATA_DRIFT
# ---------------------------------------------------------------------------

class TestFindingType:
    def test_all_findings_are_metadata_drift(self, session):
        doc = _doc(title="")
        session.add(doc)
        session.flush()
        ver = _ver(doc.id, metadata={})
        session.add(ver)
        session.commit()

        findings = _detect(session)
        assert len(findings) > 0
        assert all(f.finding_type == "METADATA_DRIFT" for f in findings)

    def test_empty_workspace_no_findings(self, session):
        findings = _detect(session)
        assert findings == []

    def test_clean_document_no_findings(self, session):
        doc, ver = _add_doc_with_version(
            session, title="Good Title",
            metadata={"category": "tech", "summary": "A proper summary"}
        )
        findings = _detect(session)
        assert findings == []
