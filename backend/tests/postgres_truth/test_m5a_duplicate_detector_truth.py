"""M5a Duplicate Detector V1 — PostgreSQL Truth Tests.

Markers: postgres_truth, m5_truth
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.documents import Document
from app.services.duplicate_detector import DuplicateDetector

pytestmark = [pytest.mark.postgres_truth, pytest.mark.m5_truth]


def _doc(
    session: Session,
    workspace_id: str,
    *,
    content_hash: str,
    lifecycle_status: str = "active",
) -> str:
    doc_id = str(uuid.uuid4())
    session.add(Document(
        id=doc_id,
        workspace_id=workspace_id,
        owner_user_id="u1",
        title="truth-doc",
        source_type="upload",
        content_hash=content_hash,
        import_status="parsed",
        lifecycle_status=lifecycle_status,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    ))
    session.flush()
    return doc_id


# ---------------------------------------------------------------------------

def test_detector_returns_list_on_clean_workspace(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    result = DuplicateDetector(truth_session, truth_seed["workspace_id"]).detect()
    assert isinstance(result, list)


def test_detector_finds_active_content_hash_duplicates(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    wid = truth_seed["workspace_id"]
    h = f"truth-dup-{uuid.uuid4().hex}"
    id_a = _doc(truth_session, wid, content_hash=h)
    id_b = _doc(truth_session, wid, content_hash=h)
    truth_session.commit()

    findings = DuplicateDetector(truth_session, wid).detect()
    found_ids = {f["document_id"] for f in findings if f["finding_type"] == "DUPLICATE_DOCUMENT"}
    assert id_a in found_ids
    assert id_b in found_ids


def test_detector_ignores_archived_documents(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    wid = truth_seed["workspace_id"]
    h = f"arch-{uuid.uuid4().hex}"
    id_active = _doc(truth_session, wid, content_hash=h, lifecycle_status="active")
    _doc(truth_session, wid, content_hash=h, lifecycle_status="archived")
    truth_session.commit()

    findings = DuplicateDetector(truth_session, wid).detect()
    found_ids = {f["document_id"] for f in findings}
    assert id_active not in found_ids


def test_detector_does_not_mutate_documents(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    wid = truth_seed["workspace_id"]
    h = f"nomut-{uuid.uuid4().hex}"
    id_a = _doc(truth_session, wid, content_hash=h)
    id_b = _doc(truth_session, wid, content_hash=h)
    truth_session.commit()

    snap_before = truth_session.execute(
        text("SELECT id, lifecycle_status, updated_at FROM documents WHERE id IN (:a, :b)"),
        {"a": id_a, "b": id_b},
    ).fetchall()

    DuplicateDetector(truth_session, wid).detect()
    truth_session.commit()

    snap_after = truth_session.execute(
        text("SELECT id, lifecycle_status, updated_at FROM documents WHERE id IN (:a, :b)"),
        {"a": id_a, "b": id_b},
    ).fetchall()

    assert snap_before == snap_after


def test_detector_finding_shape_on_postgres(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    wid = truth_seed["workspace_id"]
    h = f"shape-{uuid.uuid4().hex}"
    _doc(truth_session, wid, content_hash=h)
    _doc(truth_session, wid, content_hash=h)
    truth_session.commit()

    findings = [
        f for f in DuplicateDetector(truth_session, wid).detect()
        if f.get("finding_type") == "DUPLICATE_DOCUMENT"
    ]
    assert findings, "Expected at least one finding"
    required = {
        "finding_type", "severity", "document_id",
        "version_id", "chunk_id", "title", "description", "remediation",
    }
    for f in findings:
        missing = required - set(f.keys())
        assert not missing
        assert f["severity"] == "warning"
        assert f["remediation"] == "Dokumente prüfen und ggf. zusammenführen"


def test_detector_severity_passes_db_check_constraint(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    """Findings from detector must be insertable without violating severity check."""
    from app.models.data_quality import DataQualityRun, DataQualityFinding

    wid = truth_seed["workspace_id"]
    h = f"constraint-{uuid.uuid4().hex}"
    _doc(truth_session, wid, content_hash=h)
    _doc(truth_session, wid, content_hash=h)
    truth_session.commit()

    run_id = str(uuid.uuid4())
    truth_session.add(DataQualityRun(
        id=run_id,
        workspace_id=wid,
        status="running",
        started_at=datetime.now(UTC),
    ))
    truth_session.flush()

    now = datetime.now(UTC)
    for f in DuplicateDetector(truth_session, wid).detect():
        truth_session.add(DataQualityFinding(
            id=str(uuid.uuid4()),
            run_id=run_id,
            workspace_id=wid,
            finding_type=f["finding_type"],
            severity=f["severity"],
            document_id=f.get("document_id"),
            version_id=f.get("version_id"),
            chunk_id=f.get("chunk_id"),
            title=f["title"],
            description=f["description"],
            remediation=f["remediation"],
            created_at=now,
        ))
    # Commit triggers all DB constraints
    truth_session.commit()
