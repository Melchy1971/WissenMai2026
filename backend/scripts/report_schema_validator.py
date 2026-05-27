from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_reports.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_reports", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load validator: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_report_schema(report_path: str | Path) -> bool:
    validator = _load_validator()
    issues = validator.validate_report(Path(report_path))
    if issues:
        print(f"[FAIL] Report {report_path} ist ungueltig.")
        for issue in issues:
            print(f"- {issue.code}: {issue.message}")
        return False
    print(f"[OK] Report {report_path} ist gueltig.")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python report_schema_validator.py <report.json>")
        sys.exit(2)
    raise SystemExit(0 if validate_report_schema(sys.argv[1]) else 1)
