"""Drift Detection CLI - Read-Only.

Usage:
    python run_drift_detection.py --workspace <workspace_id> [--output <dir>]

Constraints (PROHIBIT-02, PROHIBIT-06):
    - No Cleanup actions
    - No Repair actions
    - No Auto-Reindex actions
    - Read-only: only writes drift_report.json and drift_summary.json

Exit codes:
    0 -- run completed (findings may exist)
    1 -- configuration error (missing DATABASE_URL, invalid workspace)
    2 -- runtime error (DB unreachable, detector failure)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

UTC = timezone.utc

EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_RUNTIME_ERROR = 2

DETECTOR_NAMES = [
    "DocumentDriftDetector",
    "MetadataDriftDetector",
    "LifecycleDriftDetector",
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_report(output_dir: str, filename: str, data: dict) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def _fail_report(output_dir: str, workspace_id: str, reason: str, error_code: str) -> None:
    """Write a valid FAIL drift_report.json on error."""
    run_id = str(uuid.uuid4())
    report = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "status": "failed",
        "error_code": error_code,
        "error_message": reason,
        "started_at": _now(),
        "completed_at": _now(),
        "detector_names": DETECTOR_NAMES,
        "total_findings": 0,
        "findings": [],
        "generated_at": _now(),
        "constraints": {
            "repair_actions": "PROHIBITED",
            "cleanup_actions": "PROHIBITED",
            "auto_reindex_actions": "PROHIBITED",
        },
    }
    summary = {
        "workspace_id": workspace_id,
        "run_id": run_id,
        "status": "failed",
        "total_drifts": 0,
        "total_checks": 0,
        "drift_rate": 0.0,
        "findings_by_type": {},
        "findings_by_severity": {},
        "generated_at": _now(),
    }
    _write_report(output_dir, "drift_report.json", report)
    _write_report(output_dir, "drift_summary.json", summary)


def _validate_config(workspace_id: str) -> tuple[bool, str]:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return False, "DATABASE_URL not set"
    if not workspace_id or not workspace_id.strip():
        return False, "workspace_id is empty"
    return True, ""


def _validate_workspace(workspace_id: str, session) -> tuple[bool, str]:
    try:
        result = session.execute(
            text("SELECT id FROM workspaces WHERE id = :ws_id"),
            {"ws_id": workspace_id},
        ).fetchone()
        if result is None:
            return False, f"Workspace '{workspace_id}' not found"
        return True, ""
    except Exception as exc:
        return False, f"DB query failed: {exc}"


def _run_detectors(workspace_id: str, session) -> dict:
    """Read-only -- no INSERT/UPDATE/DELETE on source tables."""
    findings = []
    total_checks = 0
    errors = []

    for detector in DETECTOR_NAMES:
        try:
            if detector == "DocumentDriftDetector":
                rows = session.execute(
                    text("SELECT d.id, d.status FROM documents d WHERE d.workspace_id = :ws_id"),
                    {"ws_id": workspace_id},
                ).fetchall()
                total_checks += len(rows)
                for row in rows:
                    if row.status in ("orphaned", "error"):
                        findings.append({
                            "finding_type": "DOCUMENT_DRIFT",
                            "severity": "error",
                            "entity_type": "document",
                            "entity_id": row.id,
                            "detail": {"status": row.status},
                        })

            elif detector == "MetadataDriftDetector":
                rows = session.execute(
                    text("SELECT d.id FROM documents d WHERE d.workspace_id = :ws_id AND (d.title IS NULL OR d.title = \'\')"),
                    {"ws_id": workspace_id},
                ).fetchall()
                total_checks += len(rows)
                for row in rows:
                    findings.append({
                        "finding_type": "METADATA_DRIFT",
                        "severity": "warning",
                        "entity_type": "document",
                        "entity_id": row.id,
                        "detail": {"missing_field": "title"},
                    })

            elif detector == "LifecycleDriftDetector":
                rows = session.execute(
                    text("SELECT d.id FROM documents d WHERE d.workspace_id = :ws_id AND d.status = \'active\'"),
                    {"ws_id": workspace_id},
                ).fetchall()
                total_checks += len(rows)

        except Exception as exc:
            errors.append({"detector": detector, "error": str(exc)})

    by_type: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for f in findings:
        by_type[f["finding_type"]] = by_type.get(f["finding_type"], 0) + 1
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1

    return {
        "findings": findings,
        "total_checks": total_checks,
        "findings_by_type": by_type,
        "findings_by_severity": by_sev,
        "detector_errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Drift Detection CLI -- read-only")
    parser.add_argument("--workspace", required=True, help="Workspace ID")
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(__file__), "..", "reports", "current"),
        help="Output directory",
    )
    args = parser.parse_args(argv)
    workspace_id = args.workspace.strip()
    output_dir = args.output

    ok, err = _validate_config(workspace_id)
    if not ok:
        print(f"[DRIFT CLI] CONFIG ERROR: {err}", file=sys.stderr)
        _fail_report(output_dir, workspace_id, err, "CONFIG_ERROR")
        return EXIT_CONFIG_ERROR

    try:
        engine = create_engine(os.environ["DATABASE_URL"])
        session = Session(engine)
    except Exception as exc:
        msg = f"DB connection failed: {exc}"
        print(f"[DRIFT CLI] RUNTIME ERROR: {msg}", file=sys.stderr)
        _fail_report(output_dir, workspace_id, msg, "DB_CONNECTION_ERROR")
        return EXIT_RUNTIME_ERROR

    try:
        ok, err = _validate_workspace(workspace_id, session)
        if not ok:
            print(f"[DRIFT CLI] CONFIG ERROR: {err}", file=sys.stderr)
            _fail_report(output_dir, workspace_id, err, "INVALID_WORKSPACE")
            return EXIT_CONFIG_ERROR

        run_id = str(uuid.uuid4())
        started_at = _now()
        result = _run_detectors(workspace_id, session)
        completed_at = _now()

        total_findings = len(result["findings"])
        status = "completed" if not result["detector_errors"] else "completed_with_errors"

        drift_report = {
            "run_id": run_id,
            "workspace_id": workspace_id,
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "detector_names": DETECTOR_NAMES,
            "total_findings": total_findings,
            "findings": result["findings"],
            "findings_by_type": result["findings_by_type"],
            "findings_by_severity": result["findings_by_severity"],
            "detector_errors": result["detector_errors"],
            "generated_at": _now(),
            "constraints": {
                "repair_actions": "PROHIBITED",
                "cleanup_actions": "PROHIBITED",
                "auto_reindex_actions": "PROHIBITED",
            },
        }
        total_checks = result["total_checks"]
        drift_rate = round(total_findings / total_checks, 4) if total_checks > 0 else 0.0
        drift_summary = {
            "workspace_id": workspace_id,
            "run_id": run_id,
            "status": status,
            "total_drifts": total_findings,
            "total_checks": total_checks,
            "drift_rate": drift_rate,
            "findings_by_type": result["findings_by_type"],
            "findings_by_severity": result["findings_by_severity"],
            "generated_at": _now(),
        }

        _write_report(output_dir, "drift_report.json", drift_report)
        _write_report(output_dir, "drift_summary.json", drift_summary)
        print(f"[DRIFT CLI] Run {run_id}: status={status}, findings={total_findings}")
        return EXIT_OK

    except Exception as exc:
        msg = f"Unexpected error: {exc}"
        print(f"[DRIFT CLI] RUNTIME ERROR: {msg}", file=sys.stderr)
        _fail_report(output_dir, workspace_id, msg, "RUNTIME_ERROR")
        return EXIT_RUNTIME_ERROR
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
