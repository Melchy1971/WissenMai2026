"""Unit tests for MetadataQualityDetector — SQLite in-memory."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models.documents import Base, Document, DocumentVersion, Workspace
from app.services.metadata_quality_detector import (
    MetadataQualityConfig,
    MetadataQualityDetector,
    _FINDING_TYPE,
)

pytestmark = pytest.mark.m3a_truth


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    @event.listens_for(eng, "connect")
    def fk(conn, _): conn.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        yield s


def _now():
    return datetime.now(timezone.utc)


def _wid():
    return str(uuid.uuid4())


def _seed_ws(session, wid):
    session.add(Workspace(id=wid, name="ws", is_default=False, created_at=_now()))
    session.flush()


def _doc(session, wid, title="doc", lifecycle_status="active", content_hash=None):
    did = str(uuid.uuid4())
    session.add(Document(
        id=did, workspace_id=wid, owner_user_id="u", title=title,
        source_type="upload", content_hash=content_hash or uuid.uuid4().hex,
        import_status="pending", lifecycle_status=lifecycle_status,
        created_at=_now(), updated_at=_now(),
    ))
    session.flush()
    return did


def _version(session, doc_id, metadata=None):
    vid = str(uuid.uuid4())
    v = DocumentVersion(
        id=vid, document_id=doc_id, version_number=1,
        normalized_markdown="text", markdown_hash=uuid.uuid4().hex,
        parser_version="1.0", ocr_used=False,
        metadata_=metadata if metadata is not None else {},
        created_at=_now(),
    )
    session.add(v)
    session.flush()
    # Link version to document
    doc = session.get(Document, doc_id)
    doc.current_version_id = vid
    doc.import_status = "parsed"  # Endstatus erst mit Version zulaessig
    session.flush()
    return vid


def _full_metadata():
    return {"tags": ["a", "b"], "category": "cat", "doc_type": "report", "summary": "Some summary text"}


def _detect(session, wid, **kwargs):
    config = MetadataQualityConfig(**kwargs) if kwargs else None
    return MetadataQualityDetector(session, wid, config).detect()


# ---------------------------------------------------------------------------
# MQ-1: empty title
# ---------------------------------------------------------------------------


class TestVersionMetadata:
    def test_missing_tags_produces_warning(self, session, engine):
        wid = _wid(); _seed_ws(session, wid)
        did = _doc(session, wid)
        _version(session, did, metadata={"category": "c", "doc_type": "t", "summary": "s"})
        session.commit()
        findings = [f for f in _detect(session, wid) if f["document_id"] == did]
        assert any(f["title"] == "Fehlende Tags" and f["severity"] == "warning" for f in findings)

    def test_empty_tags_list_produces_warning(self, session, engine):
        wid = _wid(); _seed_ws(session, wid)
        did = _doc(session, wid)
        _version(session, did, metadata={"tags": [], "category": "c", "doc_type": "t", "summary": "s"})
        session.commit()
        findings = [f for f in _detect(session, wid) if f["document_id"] == did]
        assert any(f["title"] == "Fehlende Tags" for f in findings)

    def test_missing_category_produces_warning(self, session, engine):
        wid = _wid(); _seed_ws(session, wid)
        did = _doc(session, wid)
        _version(session, did, metadata={"tags": ["t"], "doc_type": "r", "summary": "s"})
        session.commit()
        findings = [f for f in _detect(session, wid) if f["document_id"] == did]
        assert any(f["title"] == "Fehlende Kategorie" for f in findings)

    def test_missing_doc_type_produces_warning(self, session, engine):
        wid = _wid(); _seed_ws(session, wid)
        did = _doc(session, wid)
        _version(session, did, metadata={"tags": ["t"], "category": "c", "summary": "s"})
        session.commit()
        findings = [f for f in _detect(session, wid) if f["document_id"] == did]
        assert any(f["title"] == "Fehlender Dokumenttyp" for f in findings)

    def test_missing_summary_produces_info(self, session, engine):
        wid = _wid(); _seed_ws(session, wid)
        did = _doc(session, wid)
        _version(session, did, metadata={"tags": ["t"], "category": "c", "doc_type": "r"})
        session.commit()
        findings = [f for f in _detect(session, wid) if f["document_id"] == did]
        assert any(f["title"] == "Fehlende Zusammenfassung" and f["severity"] == "info" for f in findings)

    def test_all_four_missing_produces_four_findings(self, session, engine):
        wid = _wid(); _seed_ws(session, wid)
        did = _doc(session, wid)
        _version(session, did, metadata={})  # all four missing
        session.commit()
        findings = [f for f in _detect(session, wid) if f["document_id"] == did]
        assert len(findings) == 4

    def test_complete_metadata_no_findings(self, session, engine):
        wid = _wid(); _seed_ws(session, wid)
        did = _doc(session, wid)
        _version(session, did, metadata=_full_metadata())
        session.commit()
        assert len(_detect(session, wid)) == 0

    def test_no_version_skips_mq2_to_5(self, session, engine):
        """Dokument ohne current_version_id → MQ-2..5 werden übersprungen."""
        wid = _wid(); _seed_ws(session, wid)
        _doc(session, wid, title="Has Title")  # no version linked
        session.commit()
        assert len(_detect(session, wid)) == 0


# ---------------------------------------------------------------------------
# Workspace isolation
# ---------------------------------------------------------------------------

class TestWorkspaceIsolation:
    def test_findings_scoped_to_workspace(self, session, engine):
        wa, wb = _wid(), _wid()
        _seed_ws(session, wa); _seed_ws(session, wb)
        _version(session, _doc(session, wa), metadata={})   # finding in wa
        _version(session, _doc(session, wb), metadata={})   # finding in wb
        session.commit()
        fa = _detect(session, wa)
        fb = _detect(session, wb)
        assert all(f["document_id"] != "" for f in fa)
        # Seit dem Entfernen von MQ-1 gibt es keine error-Severity mehr;
        # MQ-2..4 sind warning, MQ-5 ist info.
        assert all(f["severity"] in ("warning", "info") for f in fa)
        # Each WS only sees own documents
        wa_docs = {r.id for r in session.scalars(
            __import__("sqlalchemy").select(Document).where(Document.workspace_id == wa)).all()}
        wb_docs = {r.id for r in session.scalars(
            __import__("sqlalchemy").select(Document).where(Document.workspace_id == wb)).all()}
        assert all(f["document_id"] in wa_docs for f in fa)
        assert all(f["document_id"] in wb_docs for f in fb)


# ---------------------------------------------------------------------------
# No mutations
# ---------------------------------------------------------------------------

class TestNoMutations:
    def test_detect_does_not_mutate_documents(self, session, engine):
        from sqlalchemy import select as sa_select, text
        wid = _wid(); _seed_ws(session, wid)
        did = _doc(session, wid)
        _version(session, did, metadata={})
        session.commit()
        snap_before = session.execute(
            text("SELECT id, title, lifecycle_status FROM documents WHERE workspace_id=:w"),
            {"w": wid}).fetchall()
        _detect(session, wid)
        session.commit()
        snap_after = session.execute(
            text("SELECT id, title, lifecycle_status FROM documents WHERE workspace_id=:w"),
            {"w": wid}).fetchall()
        assert set(snap_before) == set(snap_after)


# ---------------------------------------------------------------------------
# Configurable limit
# ---------------------------------------------------------------------------

class TestConfigurableLimit:
    def test_limit_caps_findings_per_rule(self, session, engine):
        """limit_per_rule begrenzt die geprueften Dokumente, nicht die Regeln.

        Frueher gegen MQ-1 formuliert. MQ-1 ist entfernt; der Grenzwert wirkt
        jetzt ueber MQ-2..5, die pro Dokument je ein Finding erzeugen.
        """
        wid = _wid(); _seed_ws(session, wid)
        for _ in range(10):
            _version(session, _doc(session, wid), metadata={})
        session.commit()
        findings = _detect(session, wid, limit_per_rule=3)
        betroffene_dokumente = {f["document_id"] for f in findings}
        assert len(betroffene_dokumente) <= 3


# ---------------------------------------------------------------------------
# Finding shape (runner compatibility)
# ---------------------------------------------------------------------------

class TestFindingShape:
    def test_all_required_keys_present(self, session, engine):
        wid = _wid(); _seed_ws(session, wid)
        _version(session, _doc(session, wid), metadata={})
        session.commit()
        required = {"finding_type", "severity", "document_id", "version_id",
                    "chunk_id", "title", "description", "remediation"}
        for f in _detect(session, wid):
            assert required <= set(f.keys())

    def test_no_run_id_in_finding(self, session, engine):
        wid = _wid(); _seed_ws(session, wid)
        _version(session, _doc(session, wid), metadata={})
        session.commit()
        for f in _detect(session, wid):
            assert "run_id" not in f

    def test_finding_type_is_missing_metadata(self, session, engine):
        wid = _wid(); _seed_ws(session, wid)
        _version(session, _doc(session, wid), metadata={})
        session.commit()
        for f in _detect(session, wid):
            assert f["finding_type"] == _FINDING_TYPE

    def test_severity_in_allowed_set(self, session, engine):
        wid = _wid(); _seed_ws(session, wid)
        did = _doc(session, wid)
        _version(session, did, metadata={})
        session.commit()
        for f in _detect(session, wid):
            assert f["severity"] in ("error", "warning", "info")
