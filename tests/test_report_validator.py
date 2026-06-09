from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str):
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


registry = _load_module("report_schema_registry")
validator = _load_module("report_validator")


def _gate_report(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "report_schema_version": 1,
        "report_name": "unit_gate",
        "report_type": "gate",
        "gate": "unit",
        "generated_by": "gate_validator",
        "timestamp": "2026-06-08T10:00:00+00:00",
        "status": "PASS",
        "collected": 1,
        "passed": 1,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0,
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def _codes(payload: dict[str, object], *, schema_name: str | None = None) -> set[str]:
    return validator.validate_payload(payload, schema_name=schema_name).codes()


def test_registry_contains_required_report_kinds() -> None:
    assert set(registry.schema_names()) == {
        "gate_report",
        "supporting_report",
        "diagnostic_report",
        "status_report",
    }


def test_every_registered_schema_contains_common_required_fields() -> None:
    for schema_name in registry.schema_names():
        schema = registry.get_schema(schema_name)
        assert set(registry.COMMON_REQUIRED_FIELDS).issubset(schema.required_fields)


def test_schema_match_uses_report_type_and_shape() -> None:
    assert registry.match_schema(_gate_report()).name == "gate_report"
    assert registry.match_schema({
        "report_schema_version": 1,
        "report_name": "support",
        "report_type": "supporting",
        "generated_by": "runner",
        "timestamp": "2026-06-08T10:00:00+00:00",
        "status": "completed",
    }).name == "supporting_report"
    assert registry.match_schema({
        "report_schema_version": 1,
        "report_name": "runtime_diagnostics",
        "generated_by": "runner",
        "timestamp": "2026-06-08T10:00:00+00:00",
        "status": "INFO",
        "diagnostics": {},
    }).name == "diagnostic_report"
    assert registry.match_schema({
        "report_schema_version": 1,
        "report_name": "masterplan_status",
        "generated_by": "runner",
        "timestamp": "2026-06-08T10:00:00+00:00",
        "status": "BLOCKED",
    }).name == "status_report"


def test_valid_gate_report_passes() -> None:
    result = validator.validate_payload(_gate_report())

    assert result.valid is True
    assert result.schema_name == "gate_report"
    assert result.issues == ()


def test_missing_fields_are_reported() -> None:
    payload = _gate_report()
    payload.pop("generated_by")
    payload.pop("timestamp")

    result = validator.validate_payload(payload)

    assert result.valid is False
    assert result.schema_name == "gate_report"
    assert result.codes() == {"missing_field"}
    assert {issue.field for issue in result.issues} == {"generated_by", "timestamp"}


def test_unknown_fields_are_reported() -> None:
    payload = _gate_report(unexpected_field=True)

    result = validator.validate_payload(payload)

    assert result.valid is False
    assert result.codes() == {"unknown_field"}
    assert result.issues[0].field == "unexpected_field"


def test_type_validation_rejects_wrong_types_and_bool_for_int() -> None:
    payload = _gate_report(report_schema_version=True, blockers={})

    result = validator.validate_payload(payload)

    assert result.valid is False
    assert result.codes() == {"invalid_type"}
    assert {issue.field for issue in result.issues} == {"report_schema_version", "blockers"}


def test_schema_match_failure_is_reported() -> None:
    result = validator.validate_payload({
        "report_schema_version": 1,
        "report_name": "unknown",
        "generated_by": "runner",
        "timestamp": "2026-06-08T10:00:00+00:00",
        "status": "PASS",
    })

    assert result.valid is False
    assert result.schema_name is None
    assert result.codes() == {"schema_match_failed"}


def test_explicit_schema_validation() -> None:
    payload = {
        "report_schema_version": 1,
        "report_name": "support",
        "generated_by": "runner",
        "timestamp": "2026-06-08T10:00:00+00:00",
        "status": "completed",
        "summary": {},
    }

    result = validator.validate_payload(payload, schema_name="supporting_report")

    assert result.valid is True
    assert result.schema_name == "supporting_report"


def test_invalid_timestamp_is_reported() -> None:
    payload = _gate_report(timestamp="not-a-date")

    assert "invalid_timestamp" in _codes(payload)
