from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_validator():
    path = SCRIPTS_DIR / "validate_known_limitations.py"
    spec = importlib.util.spec_from_file_location("validate_known_limitations", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_known_limitations"] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()
SCHEMA = validator.load_json(REPO_ROOT / "config" / "known_limitations_schema.json")


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "report_schema_version": 1,
        "report_name": "known_limitations",
        "generated_by": "gate_validator",
        "timestamp": "2026-06-09T10:00:00+00:00",
        "status": "INFO",
        "collected": 1,
        "open": 1,
        "deferred": 0,
        "blocking": 1,
        "non_blocking": 0,
        "limitations": [
            {
                "id": "KL-TEST-001",
                "title": "Test limitation",
                "status": "open",
                "severity": "high",
                "blocks_gate": ["unit_gate"],
                "owner": "test_owner",
                "evidence_report": "masterplan.md",
                "next_action": "Fix the unit limitation.",
            }
        ],
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def _codes(payload: object) -> set[str]:
    return validator.validate_payload(payload, SCHEMA, repo_root=REPO_ROOT).codes()


def test_current_known_limitations_report_is_valid() -> None:
    result = validator.validate_file(
        REPO_ROOT / "reports" / "current" / "known_limitations.json",
        schema_path=REPO_ROOT / "config" / "known_limitations_schema.json",
        repo_root=REPO_ROOT,
    )

    assert result.valid is True
    assert result.issues == ()


def test_valid_payload_passes() -> None:
    result = validator.validate_payload(_payload(), SCHEMA, repo_root=REPO_ROOT)

    assert result.valid is True
    assert result.issues == ()


def test_free_form_root_fields_are_rejected() -> None:
    payload = _payload(version=2, categories=["free-form"])

    assert "unknown_field" in _codes(payload)


def test_missing_limitation_required_field_is_rejected() -> None:
    limitation = dict(_payload()["limitations"][0])
    limitation.pop("owner")
    payload = _payload(limitations=[limitation])

    assert "missing_field" in _codes(payload)


def test_unknown_limitation_field_is_rejected() -> None:
    limitation = dict(_payload()["limitations"][0])
    limitation["free_text_blob"] = "not governed"
    payload = _payload(limitations=[limitation])

    assert "unknown_field" in _codes(payload)


def test_blocks_gate_must_be_string_array() -> None:
    limitation = dict(_payload()["limitations"][0])
    limitation["blocks_gate"] = "unit_gate"
    payload = _payload(limitations=[limitation])

    assert "invalid_type" in _codes(payload)


def test_invalid_limitation_status_and_severity_are_rejected() -> None:
    limitation = dict(_payload()["limitations"][0])
    limitation["status"] = "maybe"
    limitation["severity"] = "urgent-ish"
    payload = _payload(limitations=[limitation])

    codes = _codes(payload)
    assert "invalid_status" in codes
    assert "invalid_severity" in codes


def test_duplicate_limitation_ids_are_rejected() -> None:
    limitation = dict(_payload()["limitations"][0])
    payload = _payload(
        collected=2,
        open=2,
        blocking=2,
        non_blocking=0,
        limitations=[limitation, dict(limitation)],
    )

    assert "duplicate_id" in _codes(payload)


def test_missing_evidence_report_is_rejected() -> None:
    limitation = dict(_payload()["limitations"][0])
    limitation["evidence_report"] = "reports/current/does-not-exist.json"
    payload = _payload(limitations=[limitation])

    assert "missing_evidence_report" in _codes(payload)


def test_counter_mismatch_is_rejected() -> None:
    payload = _payload(collected=99)

    assert "counter_mismatch" in _codes(payload)
