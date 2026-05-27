from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
import shutil
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
ARCHIVE_DIR = REPORTS_DIR / "archive"
CURRENT_DIR = REPORTS_DIR / "current"

CANONICAL_BY_GATE = {
    "m3a": "m3a_frontend_truth.json",
    "m3a_truth": "m3a_frontend_truth.json",
    "frontend_truth": "m3a_frontend_truth.json",
    "m3a_release_candidate": "m3a_release_candidate.json",
    "m4a": "m4a_auth_truth.json",
    "m4a_auth_truth": "m4a_auth_truth.json",
    "m4b": "m4b_upload_queue_truth.json",
    "m4b_upload_queue_truth": "m4b_upload_queue_truth.json",
    "m4c": "m4c_lifecycle_retrieval_truth.json",
    "m4c_lifecycle_retrieval_truth": "m4c_lifecycle_retrieval_truth.json",
    "m4e": "m4e_backup_restore_truth.json",
    "m4e_backup_restore_truth": "m4e_backup_restore_truth.json",
    "masterplan_status": "masterplan_status.json",
}

# Helper: extract gate from report

def extract_gate(report: dict) -> str:
    return report.get("gate") or report.get("marker") or "unknown"

def extract_timestamp(report: dict) -> str:
    ts = report.get("timestamp")
    if not ts:
        return datetime.now().isoformat()
    # Normalize for filename
    return re.sub(r"[:.]+", "-", ts)

def archive_and_update(report_path: Path):
    if not report_path.exists():
        print(f"[SKIP] {report_path} does not exist")
        return
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Could not read {report_path}: {e}")
        return
    gate = extract_gate(report)
    ts = extract_timestamp(report)
    report_name = report_path.name
    # Prepare archive path
    archive_gate_dir = ARCHIVE_DIR / gate
    archive_gate_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_gate_dir / f"{ts}_{report_name}"
    # Prepare current path
    current_path = CURRENT_DIR / CANONICAL_BY_GATE.get(gate, f"{gate}.json")
    # If current exists, decide what to do
    if current_path.exists():
        with current_path.open("r", encoding="utf-8") as f:
            current = json.load(f)
        # Rule: alter PASS darf neuen FAIL nie überschreiben
        #        neuer FAIL invalidiert alten PASS
        old_result = current.get("result")
        new_result = report.get("result")
        if old_result == "FAIL" and new_result == "PASS":
            print(f"[ARCHIVE] New PASS ignored, current FAIL kept for {gate}")
            # Archive the PASS, but do not overwrite current FAIL
            shutil.move(str(report_path), str(archive_path))
            return
        # Archive old current
        old_ts = extract_timestamp(current)
        old_name = current_path.name
        old_archive_path = archive_gate_dir / f"{old_ts}_{old_name}"
        shutil.move(str(current_path), str(old_archive_path))
    # Move new report to current
    shutil.move(str(report_path), str(current_path))
    print(f"[UPDATE] {gate}: {report_path.name} → current/{gate}.json")
    print(f"[ARCHIVE] Old reports archived under archive/{gate}/")

if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        archive_and_update(Path(arg))
