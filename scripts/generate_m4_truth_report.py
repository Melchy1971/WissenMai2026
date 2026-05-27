from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from datetime import UTC, datetime
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
OUTPUT_FILE = CURRENT_DIR / "m4_truth_report.json"

SUB_REPORTS = [
    "m4a_auth_truth.json",
    "m4b_upload_queue_truth.json",
    "m4c_lifecycle_retrieval_truth.json",
    "m4e_backup_restore_truth.json",
]


def _commit_hash() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        val = result.stdout.strip()
        if val:
            return val
    return None


def main() -> int:
    collected = 0
    passed = 0
    failed = 0
    errors = 0
    skipped = 0
    exit_code = 0
    failed_tests = []
    blockers = []
    
    missing_reports = []
    loaded_reports = {}
    
    for r_name in SUB_REPORTS:
        path = CURRENT_DIR / r_name
        if not path.exists():
            missing_reports.append(r_name)
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON root is not an object")
            loaded_reports[r_name] = payload
        except Exception as exc:
            print(f"Error loading {r_name}: {exc}", file=sys.stderr)
            missing_reports.append(r_name)
            
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    commit = _commit_hash()
    
    if missing_reports:
        status = "BLOCKED"
        exit_code = 1
        blocker_reason = f"Missing or invalid required sub-reports: {', '.join(missing_reports)}"
        blockers.append({
            "gate": "m4_crosscutting_gate",
            "severity": "critical",
            "reason": blocker_reason,
        })
        # Try to use whatever numbers we can collect, or default to 0
        for r_name, payload in loaded_reports.items():
            collected += payload.get("collected", 0)
            passed += payload.get("passed", 0)
            failed += payload.get("failed", 0)
            errors += payload.get("errors", 0)
            skipped += payload.get("skipped", 0)
            failed_tests.extend(payload.get("failed_tests") or [])
    else:
        # All reports loaded successfully
        all_passed = True
        for r_name, payload in loaded_reports.items():
            collected += payload.get("collected", 0)
            passed += payload.get("passed", 0)
            failed += payload.get("failed", 0)
            errors += payload.get("errors", 0)
            skipped += payload.get("skipped", 0)
            failed_tests.extend(payload.get("failed_tests") or [])
            if payload.get("status") != "PASS":
                all_passed = False
            if payload.get("exit_code", 0) != 0:
                exit_code = 1
                
        if failed > 0 or errors > 0 or skipped > 0 or not all_passed:
            status = "FAIL"
            exit_code = 1
            blockers.append({
                "gate": "m4_crosscutting_gate",
                "severity": "critical",
                "reason": f"{failed} failed, {errors} errors, {skipped} skipped",
            })
        else:
            status = "PASS"
            exit_code = 0

    report = {
        "report_schema_version": 2,
        "report_name": "m4_truth_report",
        "gate": "m4_crosscutting_gate",
        "status": status,
        "timestamp": timestamp,
        "environment": "local",
        "report_type": "truth",
        "collected": collected,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "exit_code": exit_code,
        "blockers": blockers,
        "source_command": "python scripts/generate_m4_truth_report.py",
        "generated_by": "gate_validator",
        "failed_tests": sorted(failed_tests),
    }
    
    if commit:
        report["commit_hash"] = commit
        
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    
    print(f"M4 Truth Report status: {status}")
    print(f"Collected: {collected}, Passed: {passed}, Failed: {failed}, Errors: {errors}, Skipped: {skipped}")
    print(f"Wrote {OUTPUT_FILE}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
