from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "gate_engine.py"
spec = importlib.util.spec_from_file_location("gate_engine", SCRIPT_PATH)
assert spec is not None
gate_engine = importlib.util.module_from_spec(spec)
sys.modules["gate_engine"] = gate_engine
assert spec.loader is not None
spec.loader.exec_module(gate_engine)


NOW = datetime(2026, 6, 3, 8, 0, tzinfo=UTC)


def _definition(*children: object) -> object:
    return gate_engine.GateDefinition(
        parent_gate_id="parent",
        mandatory_children=tuple(children),
        hierarchy_source="docs/gate_hierarchy.json",
    )


def _child(child_id: str = "child", **kwargs: object) -> object:
    return gate_engine.ChildGateReference(
        child_gate_id=child_id,
        report=f"reports/current/{child_id}.json",
        **kwargs,
    )


def _pass_report(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "generated_by": "gate_validator",
        "timestamp": "2026-06-03T08:00:00+00:00",
        "status": "PASS",
        "result": "PASS",
        "decision": {"go_no_go": "GO"},
        "collected": 1,
        "passed": 1,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0,
        "failed_tests": [],
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def _evaluate(definition: object, child_inputs: dict[str, dict[str, object]], *, max_age: int | None = 168) -> object:
    return gate_engine.evaluate_gate(
        definition,
        child_inputs,
        now=NOW,
        max_report_age_hours=max_age,
    )


def test_gate_passes_only_when_all_mandatory_children_pass() -> None:
    definition = _definition(_child("one"), _child("two"))

    result = _evaluate(
        definition,
        {
            "one": {"report": _pass_report()},
            "two": {"report": _pass_report()},
        },
    )

    assert result.status == "PASS"
    assert result.passed == 2
    assert result.failed == 0
    assert result.decision_trace.final_status == "PASS"


def test_missing_child_blocks_parent() -> None:
    definition = _definition(_child("missing_child"))

    result = _evaluate(definition, {})

    assert result.status == "BLOCKED"
    assert result.child_results["missing_child"]["validation_status"] == "MISSING"
    assert result.decision_trace.blocking_children == ["missing_child"]


def test_invalid_child_json_blocks_parent() -> None:
    definition = _definition(_child("invalid_child"))

    result = _evaluate(
        definition,
        {"invalid_child": {"error": "invalid JSON: line 1 column 1"}},
    )

    assert result.status == "BLOCKED"
    assert result.child_results["invalid_child"]["validation_status"] == "INVALID"
    assert result.blockers[0]["child_gate_id"] == "invalid_child"


def test_stale_child_blocks_parent() -> None:
    definition = _definition(_child("stale_child"))

    result = _evaluate(
        definition,
        {"stale_child": {"report": _pass_report(timestamp="2026-06-01T08:00:00+00:00")}},
        max_age=1,
    )

    assert result.status == "BLOCKED"
    assert result.child_results["stale_child"]["validation_status"] == "STALE"


def test_failed_child_fails_parent() -> None:
    definition = _definition(_child("failed_child"))

    result = _evaluate(
        definition,
        {"failed_child": {"report": _pass_report(status="FAIL", result="FAIL")}},
    )

    assert result.status == "FAIL"
    assert result.child_results["failed_child"]["validation_status"] == "FAIL"
    assert result.decision_trace.failing_children == ["failed_child"]


def test_manual_override_does_not_unblock_child() -> None:
    definition = _definition(_child("blocked_child"))

    result = _evaluate(
        definition,
        {
            "blocked_child": {
                "report": _pass_report(
                    status="BLOCKED",
                    result="BLOCKED",
                    manual_override=True,
                )
            }
        },
    )

    assert result.status == "BLOCKED"
    assert result.manual_override_allowed is False
    assert result.child_results["blocked_child"]["validation_status"] == "BLOCKED"


def test_pass_child_requires_generated_by_timestamp_and_evidence() -> None:
    definition = _definition(_child("bad_pass"))
    missing_generated_by = _pass_report()
    missing_generated_by.pop("generated_by")

    result = _evaluate(definition, {"bad_pass": {"report": missing_generated_by}})

    assert result.status == "BLOCKED"
    assert result.child_results["bad_pass"]["validation_status"] == "INVALID"

    missing_timestamp = _pass_report()
    missing_timestamp.pop("timestamp")
    result = _evaluate(definition, {"bad_pass": {"report": missing_timestamp}})

    assert result.status == "BLOCKED"
    assert result.child_results["bad_pass"]["validation_status"] == "STALE"

    missing_evidence = _pass_report(collected=0)
    result = _evaluate(definition, {"bad_pass": {"report": missing_evidence}})

    assert result.status == "BLOCKED"
    assert result.child_results["bad_pass"]["validation_status"] == "INVALID"


def test_supporting_report_can_pass_without_collected_counter() -> None:
    definition = _definition(_child("supporting_child"))
    report = _pass_report(report_type="supporting")
    for key in ("collected", "passed", "failed", "errors", "skipped", "exit_code"):
        report.pop(key)

    result = _evaluate(definition, {"supporting_child": {"report": report}})

    assert result.status == "PASS"
