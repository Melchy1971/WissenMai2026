from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisJob, AnalysisResult, AnalysisSuggestion
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, DOCUMENT_ID

pytestmark = pytest.mark.unit_fast


def test_analysis_tables_expose_final_columns(test_engine) -> None:
    inspector = inspect(test_engine)

    assert set(inspector.get_table_names()) >= {
        "analysis_jobs",
        "analysis_job_source_documents",
        "analysis_results",
        "analysis_comparisons",
        "analysis_comparison_documents",
        "analysis_suggestions",
    }
    assert {column["name"] for column in inspector.get_columns("analysis_jobs")} == {
        "id",
        "workspace_id",
        "status",
        "analysis_type",
        "prompt",
        "created_by",
        "created_at",
        "started_at",
        "finished_at",
        "error_code",
        "error_message",
    }
    assert {column["name"] for column in inspector.get_columns("analysis_results")} == {
        "id",
        "job_id",
        "summary",
        "key_points",
        "suggested_tags",
        "suggested_topics",
        "confidence",
        "created_at",
    }


def test_analysis_model_has_required_fk_constraints_and_indexes(test_engine) -> None:
    inspector = inspect(test_engine)
    job_fks = {(fk["constrained_columns"][0], fk["referred_table"]) for fk in inspector.get_foreign_keys("analysis_jobs")}
    source_fks = {
        (fk["constrained_columns"][0], fk["referred_table"])
        for fk in inspector.get_foreign_keys("analysis_job_source_documents")
    }
    suggestion_fks = {
        (fk["constrained_columns"][0], fk["referred_table"])
        for fk in inspector.get_foreign_keys("analysis_suggestions")
    }

    assert ("workspace_id", "workspaces") in job_fks
    assert ("created_by", "users") in job_fks
    assert ("job_id", "analysis_jobs") in source_fks
    assert ("document_id", "documents") in source_fks
    assert ("job_id", "analysis_jobs") in suggestion_fks
    assert ("approved_by", "users") in suggestion_fks

    job_indexes = {index["name"] for index in inspector.get_indexes("analysis_jobs")}
    assert {"ix_analysis_jobs_workspace_id", "ix_analysis_jobs_status", "ix_analysis_jobs_created_at"} <= job_indexes


def test_suggestions_are_not_marked_approved_before_approval(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    now = datetime.now(UTC)
    job = AnalysisJob(
        id="analysis-model-job",
        workspace_id=DEFAULT_WORKSPACE_ID,
        status="completed",
        analysis_type="summary",
        prompt="Summarize",
        created_by=DEFAULT_USER_ID,
        created_at=now,
        finished_at=now,
    )
    job.source_document_ids = [DOCUMENT_ID]
    job.result = AnalysisResult(
        id="analysis-model-result",
        job_id=job.id,
        summary="Done",
        key_points=["One"],
        suggested_tags=[],
        suggested_topics=[],
        confidence=0.9,
        created_at=now,
    )
    job.suggestions = [
        AnalysisSuggestion(
            id="analysis-model-suggestion",
            job_id=job.id,
            suggestion_type="tag",
            payload={"tag": "finance"},
            status="pending",
            approved_by=None,
            approved_at=None,
        )
    ]

    db_session.add(job)
    db_session.commit()

    suggestion = db_session.get(AnalysisSuggestion, "analysis-model-suggestion")
    assert suggestion is not None
    assert suggestion.status == "pending"
    assert suggestion.approved_by is None
    assert suggestion.approved_at is None


def test_approved_suggestion_requires_approval_metadata(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    now = datetime.now(UTC)
    job = AnalysisJob(
        id="analysis-model-invalid-approval-job",
        workspace_id=DEFAULT_WORKSPACE_ID,
        status="completed",
        analysis_type="summary",
        prompt="Summarize",
        created_by=DEFAULT_USER_ID,
        created_at=now,
    )
    job.source_document_ids = [DOCUMENT_ID]
    job.suggestions = [
        AnalysisSuggestion(
            id="analysis-model-invalid-approval",
            job_id=job.id,
            suggestion_type="tag",
            payload={"tag": "finance"},
            status="approved",
            approved_by=None,
            approved_at=None,
        )
    ]

    db_session.add(job)
    with pytest.raises(IntegrityError):
        db_session.commit()
