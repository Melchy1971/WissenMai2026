from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

CURRENT_DIR = REPO_ROOT / "reports" / "current"
OUTPUT_PATH = CURRENT_DIR / "m5_data_quality_report.json"
DEFAULT_WORKSPACE_ID = os.environ.get("DEFAULT_WORKSPACE_ID", "00000000-0000-0000-0000-000000000001")
SCORE_THRESHOLD = 80.0


def _write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    tmp_path.write_text(text, encoding="utf-8")

    # Validate before rename to avoid half-written invalid reports.
    parsed = json.loads(tmp_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Generated report root must be JSON object")

    tmp_path.replace(path)


def _success_payload(*, workspace_id: str, run_data: dict[str, Any], threshold: float) -> dict[str, Any]:
    score = float(run_data.get("quality_score") or 0.0)
    passed = score >= threshold
    status = "PASS" if passed else "FAIL"
    return {
        "report_schema_version": 1,
        "report_name": "m5_data_quality_report",
        "gate": "m5_data_quality_report",
        "generated_by": "m5_data_quality_report_generator",
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": "local",
        "report_type": "truth",
        "status": status,
        "result": status,
        "collected": 1,
        "passed": 1 if passed else 0,
        "failed": 0 if passed else 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if passed else 1,
        "blockers": [] if passed else [{
            "id": "quality_score_below_threshold",
            "severity": "blocking",
            "reason": f"quality_score {score} is below threshold {threshold}.",
        }],
        "source_command": "python scripts/generate_m5_data_quality_report.py",
        "workspace_id": workspace_id,
        "run_id": run_data.get("run_id"),
        "run_status": run_data.get("status"),
        "started_at": run_data.get("started_at"),
        "finished_at": run_data.get("finished_at"),
        "total_findings": run_data.get("total_findings", 0),
        "quality_score": score,
        "findings": run_data.get("findings", []),
        "decision": {
            "go_no_go": "GO" if passed else "NO_GO",
            "result": "GO" if passed else "NO_GO",
            "score_threshold": threshold,
        },
    }


def _failure_payload(*, workspace_id: str, reason: str) -> dict[str, Any]:
    return {
        "report_schema_version": 1,
        "report_name": "m5_data_quality_report",
        "gate": "m5_data_quality_report",
        "generated_by": "m5_data_quality_report_generator",
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": "local",
        "report_type": "truth",
        "status": "FAIL",
        "result": "FAIL",
        "collected": 1,
        "passed": 0,
        "failed": 0,
        "errors": 1,
        "skipped": 0,
        "exit_code": 2,
        "blockers": [{
            "id": "data_quality_run_failed",
            "severity": "blocking",
            "reason": reason,
        }],
        "source_command": "python scripts/generate_m5_data_quality_report.py",
        "workspace_id": workspace_id,
        "run_id": None,
        "run_status": "failed",
        "started_at": None,
        "finished_at": None,
        "total_findings": 0,
        "quality_score": 0.0,
        "findings": [],
        "decision": {
            "go_no_go": "NO_GO",
            "result": "NO_GO",
            "score_threshold": SCORE_THRESHOLD,
        },
    }


def _run_scan(workspace_id: str) -> dict[str, Any]:
    from sqlalchemy import select, text
    from sqlalchemy.orm import Session

    from app.db.session import get_engine
    from app.models.documents import Workspace
    from app.services.data_quality_runner import DataQualityRunner

    engine = get_engine()
    with Session(engine) as session:
        session.execute(text("SELECT 1"))

    with Session(engine) as session:
        workspace = session.scalar(select(Workspace).where(Workspace.id == workspace_id))
        if workspace is None:
            raise ValueError(f"Workspace '{workspace_id}' not found")

    with Session(engine) as session:
        runner = DataQualityRunner.from_session(session, workspace_id)
        result = runner.run()
        session.commit()
        return {
            "run_id": result.run_id,
            "status": result.status,
            "started_at": result.started_at.isoformat(),
            "finished_at": result.finished_at.isoformat(),
            "total_findings": result.total_findings,
            "quality_score": result.quality_score,
            "findings": result.findings,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate M5 Data Quality report from DataQualityRunner.")
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE_ID, help="Workspace ID to scan")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output path")
    parser.add_argument("--score-threshold", type=float, default=SCORE_THRESHOLD, help="PASS threshold for quality_score")
    args = parser.parse_args()

    output = Path(args.output)
    workspace_id = str(args.workspace)

    try:
        run_data = _run_scan(workspace_id)
        payload = _success_payload(workspace_id=workspace_id, run_data=run_data, threshold=float(args.score_threshold))
    except Exception as exc:
        payload = _failure_payload(workspace_id=workspace_id, reason=str(exc))

    _write_atomic_json(output, payload)
    print(f"m5_data_quality_report = {payload['status']}")
    print(f"Wrote: {output}")
    return int(payload.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
