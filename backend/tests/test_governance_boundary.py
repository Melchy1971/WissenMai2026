from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.m3a_truth

BOUNDARY_PATH = Path(__file__).resolve().parents[2] / "docs" / "governance-boundary.json"


def _boundary() -> dict:
    return json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))


def test_m5_and_governance_truth_do_not_block_m4() -> None:
    boundary = _boundary()
    m4 = boundary["phases"]["m4"]
    m4_mapping = boundary["gate_mapping"]["m4_overall_gate"]

    assert "m5_truth" in m4["forbidden_blockers"]
    assert "governance_truth" in m4["forbidden_blockers"]
    assert "m5_truth" in m4_mapping["must_not_be_blocked_by"]
    assert "governance_truth" in m4_mapping["must_not_be_blocked_by"]
    assert "m4_overall_gate" in boundary["test_classification"]["m5_truth"]["does_not_block"]


def test_m4_truth_can_block_m5() -> None:
    boundary = _boundary()
    m5 = boundary["phases"]["m5"]
    rule = next(item for item in boundary["boundary_rules"] if item["id"] == "GB-005")

    assert "m4_overall_gate" in m5["allowed_upstream_dependencies"]
    assert "m4_truth" in m5["blocking_markers"]
    assert "m4_truth" in rule["allowed_upstream_blockers"]
    assert "m5_start_gate" in boundary["test_classification"]["m4_truth"]["blocks"]


def test_frontend_truth_blocks_m4_only_with_gui_dependency() -> None:
    boundary = _boundary()
    m4 = boundary["phases"]["m4"]
    frontend = boundary["test_classification"]["frontend_truth"]
    rule = next(item for item in boundary["boundary_rules"] if item["id"] == "GB-006")

    assert rule["conditional_marker"] == "frontend_truth"
    assert "gui_dependency=true" in rule["condition"]
    assert m4["conditional_blockers"][0]["marker"] == "frontend_truth"
    assert "m4_overall_gate when gui_dependency=true" in frontend["conditional_blocks"]
    assert "m4_overall_gate without gui_dependency" in frontend["does_not_block"]


def test_all_gate_markers_have_boundary_classification() -> None:
    boundary = _boundary()
    expected_markers = {
        "frontend_truth",
        "m3a_truth",
        "m4_truth",
        "m4a_auth_truth",
        "m4b_upload_queue_truth",
        "m4c_lifecycle_retrieval_truth",
        "m4e_backup_restore_truth",
        "m5_truth",
        "governance_truth",
        "chaos_truth",
        "slow_truth",
    }

    assert set(boundary["test_classification"]) == expected_markers
