from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.frontend_truth

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_frontend_runtime_connectivity_gate.py"
spec = importlib.util.spec_from_file_location("validate_frontend_runtime_connectivity_gate", SCRIPT_PATH)
gate = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)


def _truth_report(results: dict[str, str]) -> dict:
    return {
        "result": "PASS" if all(value == "PASS" for value in results.values()) else "FAIL",
        "frontend_base_url": "http://localhost:5173",
        "api_base_url": "http://127.0.0.1:8000",
        "failure_classification": [],
        "checks": [
            {"id": check_id, "result": result, "evidence": f"{check_id} {result}"}
            for check_id, result in results.items()
        ],
    }


def test_runtime_connectivity_gate_passes_at_100_score() -> None:
    report = gate.evaluate_gate(
        _truth_report({definition.truth_check_id: "PASS" for definition in gate.GATE_CHECKS}),
        generated_at="2026-05-20T00:00:00Z",
    )

    assert report["result"] == "PASS"
    assert report["decision"] == "CONNECTIVITY_STABLE"
    assert report["score"] == 100.0
    assert report["runtime_blockers"] == []


def test_runtime_connectivity_gate_blocks_m3a_below_90_score() -> None:
    results = {definition.truth_check_id: "FAIL" for definition in gate.GATE_CHECKS}
    results["no_cors_error"] = "PASS"
    results["no_mixed_content_error"] = "PASS"

    report = gate.evaluate_gate(_truth_report(results), generated_at="2026-05-20T00:00:00Z")

    assert report["result"] == "FAIL"
    assert report["decision"] == "M3A_BLOCKED"
    assert report["gate_effect"] == "M3a blockiert"
    assert report["score"] == 22.2
    assert {blocker["id"] for blocker in report["runtime_blockers"]} == {
        "backend_not_reachable",
        "health_not_green",
        "auth_me_not_reachable",
        "login_not_successful",
        "workspace_bootstrap_failed",
        "document_list_not_loaded",
        "api_unreachable_visible",
    }


def test_missing_truth_check_is_blocking() -> None:
    report = gate.evaluate_gate(_truth_report({}), generated_at="2026-05-20T00:00:00Z")

    assert report["result"] == "FAIL"
    assert report["score"] == 0.0
    assert report["runtime_blockers"][0]["evidence"] == "Truth check 'frontend_reaches_backend' fehlt."
