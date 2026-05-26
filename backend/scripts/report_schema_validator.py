import json
import sys
from pathlib import Path
from datetime import datetime

def fail(reason, report_path, details=None):
    print(f"[FAIL] {reason}")
    payload = {
        "status": "FAIL",
        "reason": reason,
        "report": str(report_path),
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    Path("validation_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    sys.exit(1)

def validate_report_schema(report_path):
    try:
        content = Path(report_path).read_text(encoding="utf-8").strip()
    except Exception as e:
        fail(f"Report nicht lesbar: {e}", report_path)
    if not content:
        fail("Leerer Report", report_path)
    try:
        data = json.loads(content)
    except Exception as e:
        fail(f"Ungültiges JSON: {e}", report_path)
    # Pflichtfelder
    required = ["collected", "passed", "failed", "errors", "skipped", "exit_code", "failed_tests", "timestamp"]
    missing = [f for f in required if f not in data]
    if missing:
        fail(f"Fehlende Pflichtfelder: {missing}", report_path)
    # PASS bei Fehlern verboten
    if data.get("failed", 0) > 0 or data.get("errors", 0) > 0 or data.get("skipped", 0) > 0:
        if data.get("exit_code", 1) == 0:
            fail("PASS bei failed/errors/skipped > 0 verboten", report_path)
    # Stale-Flag
    if data.get("stale", False):
        fail("Report ist als stale markiert", report_path)
    # Weitere Checks (RC/Gate Widerspruch etc.) können Gate-Integration prüfen
    print(f"[OK] Report {report_path} ist gültig.")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python report_schema_validator.py <report.json>")
        sys.exit(2)
    validate_report_schema(sys.argv[1])
