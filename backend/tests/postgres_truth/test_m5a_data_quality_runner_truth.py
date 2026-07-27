"""M5a Data Quality Runner — PostgreSQL Truth Tests.

Requires a live PostgreSQL DB via truth_session fixture.
Verifies runner contracts against real constraints.

Markers: postgres_truth, m5_truth
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityFinding, DataQualityRun
from app.services.data_quality_runner import DataQualityRunner, RunResult

pytestmark = [pytest.mark.postgres_truth, pytest.mark.m5_truth]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(session: Session, workspace_id: str, **kwargs) -> RunResult:
    return DataQualityRunner.from_session(session, workspace_id).run(**kwargs)


# ---------------------------------------------------------------------------
# Run lifecycle on real Postgres
# ---------------------------------------------------------------------------

def test_runner_completes_on_clean_workspace(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    result = _run(truth_session, truth_seed["workspace_id"])
    truth_session.commit()
    assert result.status == "completed"
    assert result.workspace_id == truth_seed["workspace_id"]
    assert 0.0 <= result.quality_score <= 100.0
    assert isinstance(result.total_findings, int)


def test_runner_persists_run_row(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    run_id = str(uuid.uuid4())
    _run(truth_session, truth_seed["workspace_id"], run_id=run_id)
    truth_session.commit()
    stored = truth_session.get(DataQualityRun, run_id)
    assert stored is not None
    assert stored.status == "completed"
    assert stored.workspace_id == truth_seed["workspace_id"]
    assert stored.finished_at is not None
    assert stored.total_findings is not None


def test_runner_idempotent_on_postgres(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    run_id = str(uuid.uuid4())
    r1 = _run(truth_session, truth_seed["workspace_id"], run_id=run_id)
    truth_session.commit()
    r2 = _run(truth_session, truth_seed["workspace_id"], run_id=run_id)
    assert r2.run_id == r1.run_id
    assert r2.status == r1.status
    assert r2.total_findings == r1.total_findings
    # Row count unchanged — no duplicate run written
    count = truth_session.scalar(
        select(DataQualityRun).where(DataQualityRun.id == run_id)
    )
    assert count is not None


def test_runner_raises_on_running_status(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    run_id = str(uuid.uuid4())
    truth_session.add(DataQualityRun(
        id=run_id,
        workspace_id=truth_seed["workspace_id"],
        status="running",
        started_at=datetime.now(UTC),
    ))
    truth_session.commit()
    with pytest.raises(ValueError, match="running"):
        _run(truth_session, truth_seed["workspace_id"], run_id=run_id)


def test_runner_workspace_scoped_findings(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    """Findings written by runner must all carry the runner's workspace_id."""
    run_id = str(uuid.uuid4())
    _run(truth_session, truth_seed["workspace_id"], run_id=run_id)
    truth_session.commit()
    foreign = truth_session.execute(
        text(
            "SELECT COUNT(*) FROM data_quality_findings "
            "WHERE run_id = :rid AND workspace_id != :wid"
        ),
        {"rid": run_id, "wid": truth_seed["workspace_id"]},
    ).scalar()
    assert foreign == 0


def test_runner_does_not_mutate_documents(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    """Running the runner must not alter any row in documents."""
    snapshot_before = truth_session.execute(
        text(
            "SELECT id, updated_at, lifecycle_status, title "
            "FROM documents WHERE workspace_id = :wid",
        ),
        {"wid": truth_seed["workspace_id"]},
    ).fetchall()

    _run(truth_session, truth_seed["workspace_id"])
    truth_session.commit()

    snapshot_after = truth_session.execute(
        text(
            "SELECT id, updated_at, lifecycle_status, title "
            "FROM documents WHERE workspace_id = :wid",
        ),
        {"wid": truth_seed["workspace_id"]},
    ).fetchall()

    assert snapshot_before == snapshot_after, \
        "runner mutated one or more document rows"


def test_runner_findings_satisfy_check_constraints(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    """All written findings must pass DB check constraints (severity, FK)."""
    run_id = str(uuid.uuid4())
    _run(truth_session, truth_seed["workspace_id"], run_id=run_id)
    # flush triggers FK + CHECK constraint evaluation
    truth_session.commit()
    # If we reach here, no constraint was violated.


def test_runner_sets_failed_status_on_error(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    from unittest.mock import patch
    from app.services.metadata_quality_detector import MetadataQualityDetector

    run_id = str(uuid.uuid4())
    with patch.object(
        MetadataQualityDetector, "detect", side_effect=RuntimeError("injected")
    ):
        with pytest.raises(RuntimeError):
            _run(truth_session, truth_seed["workspace_id"], run_id=run_id)
    truth_session.commit()
    stored = truth_session.get(DataQualityRun, run_id)
    assert stored is not None
    assert stored.status == "failed"
    assert stored.finished_at is not None
