from __future__ import annotations

import json
from pathlib import Path


MODEL_PATH = Path(__file__).resolve().parents[2] / "docs" / "release-candidate-model.json"


def _model() -> dict:
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def test_release_candidate_status_order_is_complete_and_terminal_only_at_released() -> None:
    model = _model()
    statuses = model["statuses"]

    assert [status["id"] for status in statuses] == [
        "draft",
        "implemented",
        "tested",
        "truth_validated",
        "gate_passed",
        "released",
    ]
    assert [status["order"] for status in statuses] == [1, 2, 3, 4, 5, 6]
    assert [status["id"] for status in statuses if status["terminal"]] == ["released"]


def test_implemented_gate_passed_and_released_rules_are_blocking() -> None:
    rules = {rule["id"]: rule for rule in _model()["status_rules"]}

    assert rules["implemented_not_done"]["severity"] == "blocking"
    assert "implemented" in rules["implemented_not_done"]["applies_to"]
    assert rules["gate_passed_requires_machine_report"]["severity"] == "blocking"
    assert "gate_passed" in rules["gate_passed_requires_machine_report"]["applies_to"]
    assert rules["released_requires_documentation_audit"]["severity"] == "blocking"
    assert "released" in rules["released_requires_documentation_audit"]["applies_to"]


def test_m4_release_candidates_have_no_m5_or_governance_dependencies() -> None:
    scopes = _model()["rc_scopes"]

    for scope_id in ("m4a", "m4b", "m4c", "m4e", "m4_overall"):
        scope = scopes[scope_id]
        serialized = json.dumps(scope)
        assert "m5_truth" not in scope["allowed_dependencies"]
        assert "governance_truth" not in scope["allowed_dependencies"]
        assert "m5_truth" in scope["forbidden_dependencies"]
        assert "governance_truth" in scope["forbidden_dependencies"]
        assert "reports/m5_truth_report.json" not in serialized
        assert "reports/governance_truth_report.json" not in serialized


def test_masterplan_mapping_covers_every_rc_status() -> None:
    model = _model()
    status_ids = {status["id"] for status in model["statuses"]}

    assert set(model["masterplan_mapping"]) == status_ids
    assert model["completion_rule"]["completed_statuses"] == ["released"]
    assert "implemented" in model["completion_rule"]["not_completed_statuses"]
