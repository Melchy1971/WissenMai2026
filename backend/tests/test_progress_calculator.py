from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "progress_calculator.py"
spec = importlib.util.spec_from_file_location("progress_calculator", SCRIPT_PATH)
assert spec is not None
calculator = importlib.util.module_from_spec(spec)
sys.modules["progress_calculator"] = calculator
assert spec.loader is not None
spec.loader.exec_module(calculator)


def _progress(**overrides):
    params = {
        "m3a_parent_status": "PASS",
        "m4_parent_status": "PASS",
        "m5a_parent_status": "PASS",
        "m3a_pass": True,
        "m4_pass": True,
        "m5_preparation_allowed": True,
        "m5a_slice_passes": {"duplicate": True, "metadata": True},
        "m5a_effective_status": "PASS",
        "m5b_prepared": True,
        "m5b_implementation_allowed": False,
        "release_allowed": False,
        "documentation_pass": True,
    }
    params.update(overrides)
    return calculator.calculate_masterplan_progress(**params)


def test_progress_never_reaches_100_until_m5_is_complete() -> None:
    result = _progress()

    assert result["progress_percent"] < 100
    assert result["m5_complete"] is False


def test_slice_pass_adds_progress_but_does_not_replace_m5a_parent_pass() -> None:
    blocked_parent = _progress(m5a_parent_status="BLOCKED", m5a_effective_status="BLOCKED", m5b_prepared=False)
    passed_parent = _progress(m5a_parent_status="PASS", m5a_effective_status="PASS")

    assert blocked_parent["progress_percent"] > 65
    assert blocked_parent["progress_percent"] < passed_parent["progress_percent"]
    assert "m5a" in blocked_parent["blocking_parent_gates"]


def test_blocked_parent_gate_is_reported_as_status_reducer() -> None:
    result = _progress(m4_parent_status="BLOCKED", m4_pass=False)

    assert "m4" in result["blocking_parent_gates"]
    assert result["parent_gate_statuses"]["m4"] == "BLOCKED"


def test_documentation_status_does_not_change_progress() -> None:
    doc_pass = _progress(documentation_pass=True)
    doc_fail = _progress(documentation_pass=False)

    assert doc_pass["progress_percent"] == doc_fail["progress_percent"]
    assert doc_pass["documentation_pass_counted"] is False
    assert doc_fail["documentation_pass_counted"] is False
