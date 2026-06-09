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


status_engine = _load_module("status_engine_v2")
masterplan = _load_module("masterplan_status_v2")


def _parent(gate: str, status: str = "PASS", *, child: str | None = None) -> dict:
    blockers = []
    if status != "PASS":
        blockers.append({
            "id": child or gate,
            "child_gate_id": child or gate,
            "severity": "blocking",
            "reason": f"{child or gate}: report is stale",
        })
    return {
        "report_name": "parent_gate_validation",
        "parent_gate": gate,
        "status": status,
        "result": status,
        "decision": {"go_no_go": "GO" if status == "PASS" else "NO_GO"},
        "collected": 1,
        "passed": 1 if status == "PASS" else 0,
        "failed": 0 if status == "PASS" else 1,
        "blockers": blockers,
    }


def _gate_layer(*, m3a: str = "PASS", m4: str = "PASS", m5a: str = "PASS") -> dict:
    return {
        "layer": "gate",
        "source": "gate_engine",
        "timestamp": "2026-06-09T08:00:00+00:00",
        "parent_gates": {
            "m3a": _parent("m3a", m3a, child="runtime_connectivity_gate"),
            "m4": _parent("m4", m4, child="m4a_auth_truth"),
            "m5a": _parent("m5a", m5a, child="report_integrity_v2"),
        },
        "errors": {},
    }


def test_status_engine_keeps_parent_gate_boundaries() -> None:
    payload = status_engine.evaluate_status(
        timestamp="2026-06-09T08:00:00+00:00",
        gate_layer=_gate_layer(m3a="STALE", m4="PASS", m5a="PASS"),
    )

    assert payload["parent_gate_statuses"] == {"m3a": "STALE", "m4": "PASS", "m5a": "PASS"}
    assert payload["phases"]["m3a"]["decision"] == "NO_GO"
    assert payload["phases"]["m4"]["decision"] == "GO"
    assert payload["m5"]["preparation_allowed"] is True
    assert any(blocker["source"] == "gate_engine:m3a" for blocker in payload["blockers"])
    assert not any(blocker["source"] == "gate_engine:m4" for blocker in payload["blockers"])


def test_masterplan_v2_consumes_status_snapshot_without_report_files() -> None:
    status_snapshot = status_engine.evaluate_status(
        timestamp="2026-06-09T08:00:00+00:00",
        gate_layer=_gate_layer(m3a="STALE", m4="PASS", m5a="PASS"),
    )

    payload = masterplan.build_masterplan_status(
        timestamp="2026-06-09T08:00:00+00:00",
        status_snapshot=status_snapshot,
    )

    assert payload["report_name"] == "masterplan_status_v2"
    assert payload["architecture"]["direct_report_dependencies"] == []
    assert payload["inputs"]["status_engine"]["report_name"] == "status_engine_v2"
    assert payload["phases"]["m4"]["decision"] == "GO"
    assert payload["overall"]["status"] == "blocked"
    assert payload["progress_model"]["documentation_pass_counted"] is False


def test_masterplan_v2_source_has_no_direct_report_loader() -> None:
    source = (SCRIPTS_DIR / "masterplan_status_v2.py").read_text(encoding="utf-8")

    assert "_load_json" not in source
    assert "json.loads" not in source
    assert "current_dir" not in source
    assert "m3a_release_candidate.json" not in source
    assert "m5a_data_quality_gate.json" not in source
    assert "known_limitations.json" not in source


def test_masterplan_v2_uses_status_engine_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    status_snapshot = status_engine.evaluate_status(
        timestamp="2026-06-09T08:00:00+00:00",
        gate_layer=_gate_layer(m3a="PASS", m4="PASS", m5a="BLOCKED"),
    )

    def fake_evaluate_status(*, timestamp: str | None = None) -> dict:
        assert timestamp == "2026-06-09T08:00:00+00:00"
        return status_snapshot

    monkeypatch.setattr(masterplan, "evaluate_status", fake_evaluate_status)

    payload = masterplan.build_masterplan_status(timestamp="2026-06-09T08:00:00+00:00")

    assert payload["inputs"]["status_engine"]["report_name"] == "status_engine_v2"
    assert payload["inputs"]["gate_engine"]["parent_gate_statuses"]["m5a"] == "BLOCKED"
    assert payload["architecture"]["direct_report_dependencies"] == []
    assert payload["m5"]["m5a_status"] == "BLOCKED"
