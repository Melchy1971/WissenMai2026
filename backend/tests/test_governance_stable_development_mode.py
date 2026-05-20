from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.m3a_truth

MODE_PATH = Path(__file__).resolve().parents[2] / "docs" / "governance-stable-development-mode.json"


def _mode() -> dict:
    return json.loads(MODE_PATH.read_text(encoding="utf-8"))


def test_governance_stable_mode_contains_all_required_principles() -> None:
    mode = _mode()
    principles = {item["name"] for item in mode["principles"]}

    assert principles == {
        "Artefaktbasierte Wahrheit",
        "Gate-spezifische Reports",
        "Marker-disziplinierte Tests",
        "Release Candidate Pflicht",
        "Known Limitations Register",
        "Documentation Audit Pflicht",
        "Gate Drift Detection",
        "Masterplan Status Engine",
    }
    assert [item["id"] for item in mode["principles"]] == [
        "GSDM-001",
        "GSDM-002",
        "GSDM-003",
        "GSDM-004",
        "GSDM-005",
        "GSDM-006",
        "GSDM-007",
        "GSDM-008",
    ]


def test_manual_status_cannot_override_machine_artifacts() -> None:
    mode = _mode()

    assert mode["authority"]["source_of_truth"] == "machine_artifacts"
    assert mode["authority"]["manual_override_allowed"] is False
    assert mode["no_go_behavior"]["manual_status_conflict"].startswith("Maschinenstatus gewinnt")
    assert "reports/masterplan_status.json" in mode["principles"][7]["required_artifacts"]


def test_no_go_behavior_prevents_feature_driven_fallback() -> None:
    mode = _mode()

    assert "neue Feature-Implementierung ohne Gate-Zuordnung" in mode["forbidden_work_when_blocked"]
    assert "M5-Implementierung vor M5-Go" in mode["forbidden_work_when_blocked"]
    assert "Feature-Wunsch wird in RC/Backlog/Gate-Scope ueberfuehrt; keine Umgehung der Gate-Regeln." == mode["no_go_behavior"]["feature_pressure"]


def test_blocked_mode_allows_only_governance_safe_work() -> None:
    mode = _mode()

    assert "Gate-Blocker beheben" in mode["allowed_work_when_blocked"]
    assert "Documentation Audit Fixes" in mode["allowed_work_when_blocked"]
    assert "M5/Governance-Findings als M4-Blocker verwenden" in mode["forbidden_work_when_blocked"]
