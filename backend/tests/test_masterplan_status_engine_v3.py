from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate_masterplan_status_v3.py"
spec = importlib.util.spec_from_file_location("generate_masterplan_status_v3", SCRIPT_PATH)
assert spec is not None
engine = importlib.util.module_from_spec(spec)
sys.modules["generate_masterplan_status_v3"] = engine
assert spec.loader is not None
spec.loader.exec_module(engine)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _rc(status: str = "PASS", decision: str = "GO") -> dict:
    passed = status == "PASS"
    return {
        "report_schema_version": 1,
        "report_name": "rc",
        "status": status,
        "result": status,
        "decision": {"go_no_go": decision},
        "collected": 1,
        "passed": 1 if passed else 0,
        "failed": 0 if passed else 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if passed else 1,
    }


def _doc_lint(errors: int = 0) -> dict:
    status = "FAIL" if errors else "PASS"
    return {
        "status": status,
        "result": status,
        "summary": {"errors": errors, "warnings": 0},
    }


def _known_limitations(operations_open: bool = True) -> dict:
    limitations = []
    if operations_open:
        limitations.append({
            "id": "KL-NB-OPS",
            "bereich": "M4e Operations",
            "zielphase": "M5 Operations",
            "blockiert_gate": [],
        })
    return {"limitations": limitations}


def _write_inputs(report_dir: Path, *, m3a: dict | None = None, m4: dict | None = None, doc_errors: int = 0, operations_open: bool = True) -> None:
    _write(report_dir / engine.M3A_RC, m3a or _rc())
    _write(report_dir / engine.M4_BACKEND_RC, m4 or _rc())
    _write(report_dir / engine.DOC_LINT, _doc_lint(doc_errors))
    _write(report_dir / engine.KNOWN_LIMITATIONS, _known_limitations(operations_open))


def test_v3_blocks_release_when_m3a_rc_is_not_pass(tmp_path: Path) -> None:
    _write_inputs(tmp_path, m3a=_rc("FAIL", "NO-GO"), operations_open=False)

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["phases"]["m3a"]["decision"] == "NO_GO"
    assert payload["phases"]["m4"]["decision"] == "GO"
    assert payload["m5"]["preparation_allowed"] is True
    assert payload["overall"]["release_allowed"] is False


def test_v3_allows_m5_preparation_only_when_m4_rc_passes(tmp_path: Path) -> None:
    _write_inputs(tmp_path, m4=_rc("FAIL", "NO-GO"), operations_open=False)

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["phases"]["m4"]["decision"] == "NO_GO"
    assert payload["m5"]["preparation_allowed"] is False


def test_v3_keeps_m5_implementation_no_go_until_operations_release(tmp_path: Path) -> None:
    _write_inputs(tmp_path, operations_open=True)

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["phases"]["m3a"]["decision"] == "GO"
    assert payload["phases"]["m4"]["decision"] == "GO"
    assert payload["m5"]["preparation_allowed"] is True
    assert payload["m5"]["implementation_allowed"] is False
    assert payload["m5"]["implementation_decision"] == "NO_GO"
    assert payload["overall"]["release_allowed"] is True


def test_v3_doc_lint_errors_block_release(tmp_path: Path) -> None:
    _write_inputs(tmp_path, doc_errors=2, operations_open=False)

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["documentation_lint"]["errors"] == 2
    assert payload["overall"]["release_allowed"] is False
    assert any(blocker["id"] == "documentation_truth_lint_errors" for blocker in payload["blockers"])


def test_v3_status_section_uses_v3_markers(tmp_path: Path) -> None:
    _write_inputs(tmp_path, operations_open=True)
    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    section = engine.render_status_section(payload)

    assert "<!-- BEGIN GENERATED MASTERPLAN STATUS v3 -->" in section
    assert "M5 Implementierung" in section
    assert "NO_GO" in section
    assert "<!-- END GENERATED MASTERPLAN STATUS v3 -->" in section
