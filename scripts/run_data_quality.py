"""CLI: Run a Data Quality scan for a workspace.

Usage:
    python scripts/run_data_quality.py --workspace <workspace_id> [options]

Options:
    --workspace   Workspace ID to scan (required)
    --output      Path for JSON report (default: reports/current/data_quality_report.json)
    --run-id      Optional explicit run ID (UUID); auto-generated if omitted
    --created-by  Optional user ID to record as run creator

Exit codes:
    0  Run completed, quality_score >= 80
    1  Run completed, quality_score < 80 (findings require attention)
    2  Run failed (detector or DB error)
    3  Configuration error (DB unreachable, workspace not found)
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Ensure backend root is on sys.path when called from repo root
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

REPORTS_DIR = _REPO_ROOT / "reports" / "current"
DEFAULT_OUTPUT = REPORTS_DIR / "data_quality_report.json"
SCORE_THRESHOLD = 80.0


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def _check_db() -> "Session":  # type: ignore[name-defined]
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    from app.db.session import get_engine
    from sqlalchemy.orm import Session

    engine = get_engine()
    try:
        with Session(engine) as session:
            session.execute(text("SELECT 1"))
        return engine
    except OperationalError as exc:
        print(f"[ERROR] DB connection failed: {exc}", file=sys.stderr)
        sys.exit(3)


def _check_workspace(engine, workspace_id: str) -> None:
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    from app.models.documents import Workspace

    with Session(engine) as session:
        ws = session.scalar(select(Workspace).where(Workspace.id == workspace_id))
        if ws is None:
            print(f"[ERROR] Workspace '{workspace_id}' not found.", file=sys.stderr)
            sys.exit(3)
        print(f"[OK]    Workspace: {ws.name} ({workspace_id})")


def _run_scan(
    engine,
    workspace_id: str,
    run_id: str,
    created_by: str | None,
) -> dict:
    from sqlalchemy.orm import Session
    from app.services.data_quality_runner import DataQualityRunner

    with Session(engine) as session:
        try:
            runner = DataQualityRunner.from_session(session, workspace_id)
            result = runner.run(run_id=run_id, created_by=created_by)
            session.commit()
            return {
                "run_id": result.run_id,
                "workspace_id": result.workspace_id,
                "status": result.status,
                "started_at": result.started_at.isoformat(),
                "finished_at": result.finished_at.isoformat(),
                "total_findings": result.total_findings,
                "quality_score": result.quality_score,
                "findings": result.findings,
            }
        except Exception as exc:
            session.commit()  # persist failed run
            print(f"[ERROR] Runner failed: {exc}", file=sys.stderr)
            sys.exit(2)


def _write_report(data: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "report_schema_version": 1,
        "report_name": "data_quality_report",
        "generated_by": "run_data_quality_cli",
        "generated_at": datetime.now(UTC).isoformat(),
        **data,
    }
    tmp_output = output.with_suffix(output.suffix + ".tmp")
    tmp_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    parsed = json.loads(tmp_output.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Generated data_quality_report payload must be a JSON object")
    tmp_output.replace(output)
    print(f"[OK]    Report written: {output}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a Data Quality scan for a workspace.",
    )
    parser.add_argument("--workspace", required=True, help="Workspace ID to scan")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument("--run-id", default=None, help="Explicit run UUID (auto-generated if omitted)")
    parser.add_argument("--created-by", default=None, help="User ID to record as run creator")
    args = parser.parse_args()

    run_id = args.run_id or str(uuid.uuid4())
    output = Path(args.output)

    print(f"[START] Data Quality Run")
    print(f"        workspace : {args.workspace}")
    print(f"        run_id    : {run_id}")
    print(f"        output    : {output}")

    # Step 1: DB connection
    print("\n[1/4]  Checking DB connection...")
    engine = _check_db()
    print("[OK]   DB reachable")

    # Step 2: Workspace
    print("\n[2/4]  Checking workspace...")
    _check_workspace(engine, args.workspace)

    # Step 3: Run
    print("\n[3/4]  Running detectors...")
    result = _run_scan(engine, args.workspace, run_id, args.created_by)
    print(f"[OK]   status        : {result['status']}")
    print(f"       total_findings: {result['total_findings']}")
    print(f"       quality_score : {result['quality_score']}")

    # Step 4: Report
    print("\n[4/4]  Writing report...")
    _write_report(result, output)

    # Exit code
    score = result.get("quality_score") or 0.0
    if score >= SCORE_THRESHOLD:
        print(f"\n[PASS] quality_score={score} >= {SCORE_THRESHOLD}")
        return 0
    else:
        print(f"\n[WARN] quality_score={score} < {SCORE_THRESHOLD} — findings require attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
