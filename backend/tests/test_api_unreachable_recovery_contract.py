from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.frontend_truth

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "docs" / "frontend-api-unreachable-recovery.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_api_unreachable_recovery_defines_required_topics() -> None:
    contract = _contract()
    rule_names = {rule["name"] for rule in contract["recovery_rules"]}

    assert {
        "Retry Verhalten",
        "Reconnect Interval",
        "Manual Retry",
        "Stale Session Handling",
        "Reconnect waehrend Login",
        "Reconnect waehrend Workspace Bootstrap",
        "Kein Retry Storm",
        "Kein Spinner Loop",
        "Keine State Corruption",
    } <= rule_names


def test_retry_strategy_is_bounded_and_does_not_retry_non_retryable_errors() -> None:
    strategy = _contract()["retry_strategy"]

    assert strategy["automatic_reconnect"]["max_attempts_per_outage"] == 5
    assert strategy["automatic_reconnect"]["max_in_flight"] == 1
    assert strategy["automatic_reconnect"]["intervals_ms"] == [2000, 5000, 10000, 20000, 30000]
    assert "API_UNREACHABLE" in strategy["retryable_codes"]
    assert "TIMEOUT" in strategy["retryable_codes"]
    for code in ("AUTH_REQUIRED", "FORBIDDEN", "WORKSPACE_NOT_CONFIGURED", "VALIDATION_ERROR"):
        assert code in strategy["non_retryable_codes"]


def test_runtime_state_machine_forbids_corrupt_recovery_paths() -> None:
    machine = _contract()["runtime_recovery_state_machine"]
    forbidden = {(item["from"], item["to"]) for item in machine["forbidden_transitions"]}
    transitions = {(item["from"], item["event"], item["to"]) for item in machine["transitions"]}

    assert ("api_unreachable", "workspace_ready") in forbidden
    assert ("api_unreachable", "empty_state") in forbidden
    assert ("authenticating", "login_network_failure", "api_unreachable") in transitions
    assert ("workspace_loading", "auth_me_network_failure", "api_unreachable") in transitions
    assert ("reconnecting", "max_attempts_exhausted", "api_unreachable") in transitions


def test_current_implementation_gaps_are_explicit_not_green_claims() -> None:
    gaps = _contract()["implementation_gap_current"]

    assert gaps["manual_retry_for_bootstrap"] == "present"
    assert gaps["automatic_bounded_reconnect"] == "not_verified"
    assert gaps["request_generation_guard"] == "not_verified"
    assert gaps["truth_status"] == "defined_not_fully_truth_validated"
