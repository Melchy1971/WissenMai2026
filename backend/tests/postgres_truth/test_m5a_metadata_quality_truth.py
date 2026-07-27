"""M5a Metadata Quality Detector — PostgreSQL Truth Tests.

Markers: postgres_truth, m5_truth
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.documents import Document, DocumentVersion
from app.models.data_quality import DataQualityFinding, DataQualityRun
from app.services.metadata_quality_detector import MetadataQualityDetector, MetadataQualityConfig

pytestmark = [pytest.mark.postgres_truth, pytest.mark.m5_truth]


def _now():
    return datetime.now(UTC)


def _doc(session, workspace_id, title="doc", lifecycle_status="active"):
    did = str(uuid.uuid4())
    session.add(Document(
        id=did, workspace_id=workspace_id, owner_user_id="u", title=title,
        source_type="upload", content_hash=uuid.uuid4().hex,
        import_status="pending", lifecycle_status=lifecycle_status,
        created_at=_now(), updated_at=_now(),
    ))
    session.flush()
    return did


def _version(session, doc_id, metadata=None):
    vid = str(uuid.uuid4())
    session.add(DocumentVersion(
        id=vid, document_id=doc_id, version_number=1,
        normalized_markdown="text", markdown_hash=uuid.uuid4().hex,
        parser_version="1.0", ocr_used=False,
        metadata_=metadata if metadata is not None else {},
        created_at=_now(),
    ))
    session.flush()
    doc = session.get(Document, doc_id)
    doc.current_version_id = vid
    doc.import_status = "chunked"  # Endstatus erst mit Version zulaessig
    session.flush()
    return vid


# ---------------------------------------------------------------------------

def test_detector_returns_list_on_clean_workspace(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    result = MetadataQualityDetector(truth_session, truth_seed["workspace_id"]).detect()
    assert isinstance(result, list)


def test_mq1_empty_title_detected(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    did = _doc(truth_session, wid, title="")
    truth_session.commit()
    findings = MetadataQualityDetector(truth_session, wid).detect()
    mq1 = [f for f in findings if f["document_id"] == did and f["severity"] == "error"]
    assert len(mq1) >= 1


def test_all_four_missing_metadata_detected(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    did = _doc(truth_session, wid)
    _version(truth_session, did, metadata={})
    truth_session.commit()
    findings = [f for f in MetadataQualityDetector(truth_session, wid).detect()
                if f["document_id"] == did]
    assert len(findings) == 4


def test_complete_metadata_no_findings(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    did = _doc(truth_session, wid)
    _version(truth_session, did, metadata={
        "tags": ["a"], "category": "c", "doc_type": "r", "summary": "s"
    })
    truth_session.commit()
    findings = [f for f in MetadataQualityDetector(truth_session, wid).detect()
                if f["document_id"] == did]
    assert len(findings) == 0


def test_archived_doc_not_detected(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    _doc(truth_session, wid, title="", lifecycle_status="archived")
    truth_session.commit()
    findings = MetadataQualityDetector(truth_session, wid).detect()
    assert all(f.get("severity") != "error" or f.get("title") != "Leerer Dokumenttitel"
               for f in findings), "Archived doc produced MQ-1 finding"


def test_findings_pass_db_constraints(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    did = _doc(truth_session, wid, title="")
    _version(truth_session, did, metadata={})
    truth_session.commit()

    run_id = str(uuid.uuid4())
    truth_session.add(DataQualityRun(
        id=run_id, workspace_id=wid, status="running", started_at=_now()
    ))
    truth_session.flush()

    now = _now()
    for f in MetadataQualityDetector(truth_session, wid).detect():
        truth_session.add(DataQualityFinding(
            id=str(uuid.uuid4()), run_id=run_id, workspace_id=wid,
            finding_type=f["finding_type"], severity=f["severity"],
            document_id=f.get("document_id"), version_id=f.get("version_id"),
            chunk_id=f.get("chunk_id"), title=f["title"],
            description=f["description"], remediation=f["remediation"],
            created_at=now,
        ))
    truth_session.commit()  # triggers all DB constraints


def test_no_document_mutations(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    did = _doc(truth_session, wid, title="")
    truth_session.commit()
    snap_before = truth_session.execute(
        text("SELECT id, title, lifecycle_status FROM documents WHERE workspace_id=:w"),
        {"w": wid}).fetchall()
    MetadataQualityDetector(truth_session, wid).detect()
    truth_session.commit()
    snap_after = truth_session.execute(
        text("SELECT id, title, lifecycle_status FROM documents WHERE workspace_id=:w"),
        {"w": wid}).fetchall()
    assert set(snap_before) == set(snap_after)
