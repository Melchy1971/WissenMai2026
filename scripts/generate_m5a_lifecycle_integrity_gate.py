from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"

OUTPUT_GATE = "m5a_lifecycle_integrity_gate.json"
TRUTH_REPORT = "m5a_lifecycle_integrity_truth.json"

DUPLICATE_GATE = "m5a_duplicate_detector_gate.json"
METADATA_GATE = "m5a_metadata_detector_gate.json"
DATA_QUALITY_REPORT = "data_quality_report.json"

DETECTOR_FILE = REPO_ROOT / "backend" / "app" / "services" / "lifecycle_integrity_detector.py"
RUNNER_FILE = REPO_ROOT / "backend" / "app" / "services" / "data_quality_runner.py"
UNIT_TEST_FILE = REPO_ROOT / "backend" / "tests" / "test_lifecycle_integrity_detector.py"
PG_TRUTH_TEST_FILE = REPO_ROOT / "backend" / "tests" / "postgres_truth" / "test_m5a_lifecycle_integrity_truth.py"


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root must be object"
    return payload, None


def _int_value(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def _is_pass_gate(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    status = str(report.get("status") or report.get("result") or "").upper()
    return (
        status == "PASS"
        and _int_value(report.get("collected"), 0) > 0
        and _int_value(report.get("failed"), 0) == 0
        and _int_value(report.get("errors"), 0) == 0
        and _int_value(report.get("skipped"), 0) == 0
        and _int_value(report.get("exit_code"), 1) == 0
    )


def _data_quality_completed(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    return str(report.get("status") or "").lower() == "completed"


def _file_contains(path: Path, tokens: list[str]) -> bool:
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return all(token in text for token in tokens)


def _truth_report_pass(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    status = str(report.get("status") or report.get("result") or "").upper()
    return (
        status == "PASS"
        and _int_value(report.get("failed"), 0) == 0
        and _int_value(report.get("errors"), 0) == 0
        and _int_value(report.get("exit_code"), 1) == 0
    )


def build_gate_report(current_dir: Path = CURRENT_DIR, *, timestamp: str | None = None) -> dict[str, Any]:
    now = timestamp or datetime.now(UTC).isoformat()

    duplicate_gate, duplicate_error = _load_json(current_dir / DUPLICATE_GATE)
    metadata_gate, metadata_error = _load_json(current_dir / METADATA_GATE)
    dq_report, dq_error = _load_json(current_dir / DATA_QUALITY_REPORT)
    truth_report, truth_error = _load_json(current_dir / TRUTH_REPORT)

    duplicate_pass = duplicate_error is None and _is_pass_gate(duplicate_gate)
    metadata_pass = metadata_error is None and _is_pass_gate(metadata_gate)
    dq_completed = dq_error is None and _data_quality_completed(dq_report)

    detector_exists = DETECTOR_FILE.exists()
    runner_integrated = _file_contains(RUNNER_FILE, ["LifecycleIntegrityDetector", "LifecycleIntegrityDetector("])
    unit_tests_present = UNIT_TEST_FILE.exists()
    pg_truth_tests_present = PG_TRUTH_TEST_FILE.exists()

    checks_1_4_implemented = _file_contains(
        DETECTOR_FILE,
        [
            "_detect_non_active_searchable_chunks",
            "lifecycle_status.in_((\"archived\", \"deleted\"))",
            "_detect_active_not_retrievable_documents",
        ],
    )
    check_5_implemented = _file_contains(
        DETECTOR_FILE,
        ["_detect_source_status_drift", "ChatCitation.source_status != Document.lifecycle_status"],
    )

    truth_executed_pass = truth_error is None and _truth_report_pass(truth_report)

    criteria: list[dict[str, Any]] = [
        {
            "id": "c1",
            "label": "Duplicate Detector PASS (Voraussetzung)",
            "passed": duplicate_pass,
            "source": f"reports/current/{DUPLICATE_GATE}",
            "evidence": str((duplicate_gate or {}).get("status") or duplicate_error or "missing"),
        },
        {
            "id": "c2",
            "label": "Metadata Detector PASS (Voraussetzung)",
            "passed": metadata_pass,
            "source": f"reports/current/{METADATA_GATE}",
            "evidence": str((metadata_gate or {}).get("status") or metadata_error or "missing"),
        },
        {
            "id": "c3",
            "label": "Data Quality Run ausfuehrbar (completed)",
            "passed": dq_completed,
            "source": f"reports/current/{DATA_QUALITY_REPORT}",
            "evidence": str((dq_report or {}).get("status") or dq_error or "missing"),
        },
        {
            "id": "c4",
            "label": "LifecycleIntegrityDetector implementiert",
            "passed": detector_exists,
            "source": "backend/app/services/lifecycle_integrity_detector.py",
            "evidence": "exists" if detector_exists else "missing",
        },
        {
            "id": "c5",
            "label": "Runner integriert LifecycleIntegrityDetector",
            "passed": runner_integrated,
            "source": "backend/app/services/data_quality_runner.py",
            "evidence": "integration_found" if runner_integrated else "integration_missing",
        },
        {
            "id": "c6",
            "label": "Unit-Tests fuer LifecycleIntegrityDetector vorhanden",
            "passed": unit_tests_present,
            "source": "backend/tests/test_lifecycle_integrity_detector.py",
            "evidence": "present" if unit_tests_present else "missing",
        },
        {
            "id": "c7",
            "label": "PostgreSQL Truth-Tests fuer Lifecycle Slice vorhanden",
            "passed": pg_truth_tests_present,
            "source": "backend/tests/postgres_truth/test_m5a_lifecycle_integrity_truth.py",
            "evidence": "present" if pg_truth_tests_present else "missing",
        },
        {
            "id": "c8",
            "label": "Checks 1-4 (Search/Retrieval Lifecycle) implementiert",
            "passed": checks_1_4_implemented,
            "source": "backend/app/services/lifecycle_integrity_detector.py",
            "evidence": "implemented" if checks_1_4_implemented else "missing_tokens",
        },
        {
            "id": "c9",
            "label": "Check 5 (source_status Konsistenz) implementiert",
            "passed": check_5_implemented,
            "source": "backend/app/services/lifecycle_integrity_detector.py",
            "evidence": "implemented" if check_5_implemented else "missing_tokens",
        },
        {
            "id": "c10",
            "label": "PostgreSQL Truth-Lauf fuer Lifecycle Slice PASS",
            "passed": truth_executed_pass,
            "source": f"reports/current/{TRUTH_REPORT}",
            "evidence": str((truth_report or {}).get("status") or truth_error or "missing"),
        },
    ]

    passed = sum(1 for c in criteria if c["passed"])
    failed = len(criteria) - passed
    score = round((passed / len(criteria)) * 100.0, 2) if criteria else 0.0
    go = score >= 90.0 and failed == 0

    blockers = [
        {
            "id": f"lifecycle_{item['id']}_failed",
            "severity": "blocking",
            "reason": f"{item['label']} is not satisfied.",
        }
        for item in criteria
        if not item["passed"]
    ]

    return {
        "report_schema_version": 1,
        "report_name": "m5a_lifecycle_integrity_gate",
        "gate": "m5a_lifecycle_integrity_gate",
        "generated_by": "gate_validator",
        "timestamp": now,
        "environment": "local",
        "report_type": "gate",
        "status": "PASS" if go else "BLOCKED",
        "result": "PASS" if go else "BLOCKED",
        "collected": len(criteria),
        "passed": passed,
        "failed": failed,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if go else 1,
        "score": score,
        "score_threshold": 90.0,
        "blockers": blockers,
        "source_command": "python scripts/generate_m5a_lifecycle_integrity_gate.py",
        "decision": {
            "go_no_go": "GO" if go else "NO_GO",
            "result": "GO" if go else "NO_GO",
            "m5a_lifecycle_integrity_allowed": go,
        },
        "inputs": {
            "duplicate_gate": f"reports/current/{DUPLICATE_GATE}",
            "metadata_gate": f"reports/current/{METADATA_GATE}",
            "data_quality_report": f"reports/current/{DATA_QUALITY_REPORT}",
            "truth_report": f"reports/current/{TRUTH_REPORT}",
            "detector_file": "backend/app/services/lifecycle_integrity_detector.py",
            "runner_file": "backend/app/services/data_quality_runner.py",
            "unit_tests": "backend/tests/test_lifecycle_integrity_detector.py",
            "postgres_truth_tests": "backend/tests/postgres_truth/test_m5a_lifecycle_integrity_truth.py",
        },
        "criteria": criteria,
        "summary": {
            "rule": "PASS requires all prerequisites PASS, lifecycle detector and tests implemented, and PostgreSQL truth execution PASS.",
            "overall_m5a_lifecycle_integrity_pass": go,
        },
    }


def write_gate_report(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    parsed = json.loads(tmp_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Generated gate payload must be a JSON object")
    tmp_path.replace(output_path)


def main() -> int:
    payload = build_gate_report()
    output = CURRENT_DIR / OUTPUT_GATE
    write_gate_report(payload, output)
    print(f"m5a_lifecycle_integrity_gate = {payload['decision']['go_no_go']} (status={payload['status']})")
    print(f"Wrote: {output}")
    return int(payload.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
