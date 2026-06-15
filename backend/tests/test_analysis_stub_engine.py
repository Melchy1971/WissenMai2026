from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.models.documents import Document
from app.services.analysis.analysis_stub_engine import DeterministicAnalysisStubEngine
from app.services.analysis.service import AnalysisComparisonService, AnalysisJobService, AnalysisResultService
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, DOCUMENT_ID, OLDER_DOCUMENT_ID

pytestmark = pytest.mark.unit_fast


def _create_job(db_session: Session):
    return AnalysisJobService(db_session).create_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        source_document_ids=[DOCUMENT_ID, OLDER_DOCUMENT_ID],
        analysis_type="comparison",
        prompt="Compare privacy-relevant changes",
    )


def test_stub_engine_result_is_deterministic_and_documents_input(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    job = _create_job(db_session)
    documents = [db_session.get(Document, DOCUMENT_ID)]
    assert documents[0] is not None
    engine = DeterministicAnalysisStubEngine(db_session)
    created_at = datetime(2026, 6, 12, 10, 0, tzinfo=UTC)

    first = engine.build_result(
        job=job,
        documents=documents,
        comparison=None,
        prompt=job.prompt,
        max_suggestions=3,
        created_at=created_at,
    )
    second = engine.build_result(
        job=job,
        documents=documents,
        comparison=None,
        prompt=job.prompt,
        max_suggestions=3,
        created_at=created_at,
    )

    assert first == second
    assert first["summary"] == "Deterministic analysis stub processed 1 provided document(s) for analysis type 'comparison'."
    assert first["input_documents"][0]["document_id"] == DOCUMENT_ID
    assert any(DOCUMENT_ID in item for item in first["key_points"])
    assert "external API calls" in first["key_points"][1]


def test_stub_engine_comparison_is_deterministic_and_reports_overlap_and_difference(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    job = _create_job(db_session)
    engine = DeterministicAnalysisStubEngine(db_session)
    created_at = datetime(2026, 6, 12, 10, 0, tzinfo=UTC)

    first = engine.compare(
        job=job,
        compared_document_ids=[OLDER_DOCUMENT_ID],
        created_at=created_at,
        max_differences=5,
    )
    second = engine.compare(
        job=job,
        compared_document_ids=[OLDER_DOCUMENT_ID],
        created_at=created_at,
        max_differences=5,
    )

    assert first == second
    assert first["compared_document_ids"] == [OLDER_DOCUMENT_ID]
    assert first["input_documents"][0]["document_id"] == DOCUMENT_ID
    assert first["input_documents"][1]["document_id"] == OLDER_DOCUMENT_ID
    assert first["overlaps"][0]["document_id"] == OLDER_DOCUMENT_ID
    assert first["differences"][0]["document_id"] == OLDER_DOCUMENT_ID
    assert first["suggested_merge"]["strategy"] == "manual_review"


def test_services_use_stub_engine_without_external_provider(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    job = _create_job(db_session)
    comparison = AnalysisComparisonService(db_session).compare_with_existing(
        workspace_id=DEFAULT_WORKSPACE_ID,
        job_id=job.id,
        compared_document_ids=[OLDER_DOCUMENT_ID],
    )
    job.status = "running"
    db_session.add(job)
    db_session.commit()

    result = AnalysisResultService(db_session).create_result(
        workspace_id=DEFAULT_WORKSPACE_ID,
        job_id=job.id,
        max_suggestions=2,
    )

    assert comparison.differences
    assert result.summary.startswith("Deterministic analysis stub processed")
    assert result.key_points[1] == "Engine: deterministic local stub; no external API calls."
