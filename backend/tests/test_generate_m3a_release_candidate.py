"""Tests for generate_m3a_release_candidate.py and m3a_stale_guard.py."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


def _load(name: str) -> object:
    """Load a script module directly from source, bypassing any stale .pyc."""
    path = SCRIPTS_DIR / f"{name}.py"
    src = path.read_text(encoding="utf-8")
    code = compile(src, str(path), "exec")
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    sys.modules[name] = mod
    exec(code, mod.__dict__)
    return mod


guard = _load("m3a_stale_guard")
generator = _load("generate_m3a_release_candidate")
engine = _load("generate_masterplan_status_v3")

pytestmark = pytest.mark.m3a_truth

T_OLD = "2026-05-28T10:00:00+00:00"
T_RC  = "2026-05-28T12:00:00+00:00"
T_NEW = "2026-05-28T14:00:00+00:00"


def _report(*, ts: str = T_OLD, status: str = "PASS", collected: int = 1) -> dict:
    return {
        "status": status, "result": status,
        "collected": collected, "passed": collected if status == "PASS" else 0,
        "failed": 0 if status == "PASS" else 1, "errors": 0, "skipped": 0,
        "exit_code": 0 if status == "PASS" else 1, "timestamp": ts,
    }


def _rc(*, ts: str = T_RC, status: str = "PASS") -> dict:
    return {
        **_report(ts=ts, status=status),
        "report_name": "m3a_release_candidate",
        "decision": {"go_no_go": "GO" if status == "PASS" else "NO-GO"},
    }


def _doc_lint(*, ts: str = T_OLD, errors: int = 0) -> dict:
    status = "PASS" if errors == 0 else "FAIL"
    return {
        "status": status, "result": status, "errors": errors,
        "summary": {"errors": errors, "warnings": 0},
        "exit_code": 0 if errors == 0 else 1, "timestamp": ts,
    }


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _ops_rc() -> dict:
    r = _report()
    r.update({"report_name": "m4e_operations_release_report", "operations_release_status": "GO"})
    return r


def _write_engine_inputs(
    report_dir: Path, *, m3a=None, m4=None, doc_errors=0,
    operations_release=None, frontend_full_suite=None, preflight=None,
) -> None:
    _write(report_dir / engine.M3A_RC, m3a or _rc())
    _write(report_dir / engine.M4_BACKEND_RC, m4 or _rc())
    _write(report_dir / engine.M4E_OPERATIONS_RELEASE, operations_release or _ops_rc())
    _write(report_dir / engine.DOC_LINT, _doc_lint(errors=doc_errors))
    _write(report_dir / engine.KNOWN_LIMITATIONS, {"limitations": []})
    _write(report_dir / engine.FRONTEND_FULL_SUITE, frontend_full_suite or _report())
    _write(report_dir / engine.PREFLIGHT, preflight or _report())


# ---------------------------------------------------------------------------
# Stale Guard unit tests
# ---------------------------------------------------------------------------

class TestCheckStaleness:
    def test_fresh_rc_is_not_stale(self):
        rc = _rc(ts=T_RC)
        result = guard.check_staleness(rc, _report(ts=T_OLD), _report(ts=T_OLD), _doc_lint(ts=T_OLD))
        assert not result.is_stale

    def test_frontend_newer_than_rc_is_stale(self):
        rc = _rc(ts=T_RC)
        result = guard.check_staleness(rc, _report(ts=T_NEW), _report(ts=T_OLD), _doc_lint(ts=T_OLD))
        assert result.is_stale
        assert any("frontend_full_suite_staged_report" in r for r in result.reasons)

    def test_preflight_newer_than_rc_is_stale(self):
        rc = _rc(ts=T_RC)
        result = guard.check_staleness(rc, _report(ts=T_OLD), _report(ts=T_NEW), _doc_lint(ts=T_OLD))
        assert result.is_stale
        assert any("report_truth_preflight" in r for r in result.reasons)

    def test_doc_lint_newer_than_rc_is_stale(self):
        rc = _rc(ts=T_RC)
        result = guard.check_staleness(rc, _report(ts=T_OLD), _report(ts=T_OLD), _doc_lint(ts=T_NEW))
        assert result.is_stale
        assert any("documentation_truth_lint" in r for r in result.reasons)

    def test_all_three_inputs_stale_three_reasons(self):
        rc = _rc(ts=T_RC)
        result = guard.check_staleness(rc, _report(ts=T_NEW), _report(ts=T_NEW), _doc_lint(ts=T_NEW))
        assert result.is_stale
        assert len(result.reasons) == 3

    def test_missing_rc_is_stale(self):
        result = guard.check_staleness(None, _report(ts=T_OLD), _report(ts=T_OLD), _doc_lint(ts=T_OLD))
        assert result.is_stale
        assert "rc_missing" in result.reasons

    def test_rc_without_timestamp_is_stale(self):
        rc = {**_rc(), "timestamp": None, "generated_at": None}
        result = guard.check_staleness(rc, _report(ts=T_OLD), _report(ts=T_OLD), _doc_lint(ts=T_OLD))
        assert result.is_stale

    def test_missing_input_report_treated_as_stale(self):
        rc = _rc(ts=T_RC)
        result = guard.check_staleness(rc, None, _report(ts=T_OLD), _doc_lint(ts=T_OLD))
        assert result.is_stale
        assert any("frontend_full_suite_staged_report_missing" in r for r in result.reasons)

    def test_stale_reason_is_readable_string(self):
        rc = _rc(ts=T_RC)
        result = guard.check_staleness(rc, _report(ts=T_NEW), _report(ts=T_OLD), _doc_lint(ts=T_OLD))
        assert result.stale_reason is not None
        assert "frontend_full_suite_staged_report" in result.stale_reason

    def test_not_stale_stale_reason_is_none(self):
        rc = _rc(ts=T_RC)
        result = guard.check_staleness(rc, _report(ts=T_OLD), _report(ts=T_OLD), _doc_lint(ts=T_OLD))
        assert result.stale_reason is None


# ---------------------------------------------------------------------------
# Precondition check tests
# ---------------------------------------------------------------------------

class TestCheckPreconditions:
    def test_both_pass_no_violations(self):
        violations = guard.check_preconditions(_report(), _doc_lint())
        assert violations == []

    def test_preflight_missing_is_violation(self):
        violations = guard.check_preconditions(None, _doc_lint())
        assert any("preflight_missing" in v for v in violations)

    def test_preflight_fail_status_is_violation(self):
        violations = guard.check_preconditions(_report(status="FAIL"), _doc_lint())
        assert any("preflight" in v for v in violations)

    def test_doc_lint_missing_is_violation(self):
        violations = guard.check_preconditions(_report(), None)
        assert any("lint_missing" in v for v in violations)

    def test_doc_lint_with_errors_is_violation(self):
        violations = guard.check_preconditions(_report(), _doc_lint(errors=2))
        assert any("lint" in v for v in violations)

    def test_both_fail_yields_two_violations(self):
        violations = guard.check_preconditions(_report(status="FAIL"), _doc_lint(errors=1))
        assert len(violations) == 2


# ---------------------------------------------------------------------------
# Generator tests
# ---------------------------------------------------------------------------

def _make_generator_inputs(report_dir, gui_truth_dir, *, frontend_ts=T_OLD,
                            frontend_status="PASS", preflight_status="PASS", doc_errors=0):
    _write(report_dir / generator.FRONTEND_FULL_SUITE, _report(ts=frontend_ts, status=frontend_status))
    _write(report_dir / generator.FRONTEND_MINIMAL, _report(ts=T_OLD))
    _write(report_dir / generator.PREFLIGHT, _report(status=preflight_status))
    _write(report_dir / generator.DOC_LINT, _doc_lint(errors=doc_errors))


class TestBuildReleaseCandidate:
    def test_pass_when_all_inputs_green_and_gui_available(self, tmp_path):
        gui_dir = tmp_path / "gui_truth"
        _make_generator_inputs(tmp_path, gui_dir)
        _write(gui_dir / generator.GUI_CHAOS, {
            "result": "PASS", "collected": 8, "passed": 8, "failed": 0,
            "errors": 0, "skipped": 0, "exit_code": 0, "timestamp": T_OLD,
        })

        payload, exit_code = generator.build_release_candidate(tmp_path, gui_dir)

        assert payload["status"] == "PASS"
        assert payload["decision"]["go_no_go"] == "GO"
        assert exit_code == 0

    def test_blocked_when_preflight_fails(self, tmp_path):
        gui_dir = tmp_path / "gui_truth"
        _make_generator_inputs(tmp_path, gui_dir, preflight_status="FAIL")

        payload, exit_code = generator.build_release_candidate(tmp_path, gui_dir)

        assert payload["status"] == "BLOCKED"
        assert payload["decision"]["go_no_go"] == "NO-GO"
        assert exit_code == 1
        assert "stale_reason" in payload

    def test_blocked_when_doc_lint_has_errors(self, tmp_path):
        gui_dir = tmp_path / "gui_truth"
        _make_generator_inputs(tmp_path, gui_dir, doc_errors=3)

        payload, exit_code = generator.build_release_candidate(tmp_path, gui_dir)

        assert payload["status"] == "BLOCKED"
        assert exit_code == 1

    def test_fail_when_frontend_full_suite_fails(self, tmp_path):
        gui_dir = tmp_path / "gui_truth"
        _make_generator_inputs(tmp_path, gui_dir, frontend_status="FAIL")

        payload, exit_code = generator.build_release_candidate(tmp_path, gui_dir)

        assert payload["status"] != "PASS"
        assert payload["decision"]["go_no_go"] == "NO-GO"
        assert exit_code == 1

    def test_stale_guard_metadata_always_present(self, tmp_path):
        gui_dir = tmp_path / "gui_truth"
        _make_generator_inputs(tmp_path, gui_dir)

        payload, _ = generator.build_release_candidate(tmp_path, gui_dir)

        sg = payload.get("stale_guard")
        assert sg is not None
        assert "input_timestamps" in sg
        assert "rc_timestamp" in sg

    def test_output_embeds_frontend_timestamp(self, tmp_path):
        gui_dir = tmp_path / "gui_truth"
        _make_generator_inputs(tmp_path, gui_dir, frontend_ts=T_OLD)

        payload, _ = generator.build_release_candidate(tmp_path, gui_dir)

        ts = payload["stale_guard"]["input_timestamps"]["frontend_full_suite_staged_report"]
        assert ts == T_OLD

    def test_precondition_violations_in_stale_reason(self, tmp_path):
        gui_dir = tmp_path / "gui_truth"
        _make_generator_inputs(tmp_path, gui_dir, preflight_status="FAIL")

        payload, _ = generator.build_release_candidate(tmp_path, gui_dir)

        assert payload.get("stale_reason") is not None
        assert "preconditions_not_met" in payload["stale_reason"]

    def test_write_outputs_creates_json_and_md(self, tmp_path):
        gui_dir = tmp_path / "gui_truth"
        _make_generator_inputs(tmp_path, gui_dir)
        out_json = tmp_path / "rc.json"
        out_md = tmp_path / "rc.md"

        generator.write_outputs(tmp_path, gui_dir, out_json, out_md)

        assert out_json.exists()
        assert out_md.exists()
        data = json.loads(out_json.read_text())
        assert data["report_name"] == "m3a_release_candidate"


# ---------------------------------------------------------------------------
# Status engine stale guard integration tests
# ---------------------------------------------------------------------------

class TestStatusEngineStaleGuard:
    def test_fresh_rc_passes_normally(self, tmp_path):
        _write_engine_inputs(tmp_path, m3a=_rc(ts=T_RC),
                             frontend_full_suite=_report(ts=T_OLD), preflight=_report(ts=T_OLD))

        result = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

        assert result["phases"]["m3a"]["decision"] == "GO"
        assert result["overall"]["release_allowed"] is True

    def test_stale_rc_blocks_m3a_gate(self, tmp_path):
        _write_engine_inputs(tmp_path, m3a=_rc(ts=T_OLD),
                             frontend_full_suite=_report(ts=T_NEW), preflight=_report(ts=T_OLD))

        result = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

        assert result["phases"]["m3a"]["decision"] == "NO_GO"
        assert result["overall"]["release_allowed"] is False

    def test_stale_rc_adds_m3a_rc_stale_blocker(self, tmp_path):
        _write_engine_inputs(tmp_path, m3a=_rc(ts=T_OLD),
                             frontend_full_suite=_report(ts=T_NEW), preflight=_report(ts=T_OLD))

        result = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

        blocker_ids = [b["id"] for b in result["phases"]["m3a"]["blockers"]]
        assert "m3a_rc_stale" in blocker_ids

    def test_pass_status_rc_still_stale_when_inputs_newer(self, tmp_path):
        rc = {**_rc(ts=T_OLD, status="PASS")}
        _write_engine_inputs(tmp_path, m3a=rc,
                             frontend_full_suite=_report(ts=T_NEW), preflight=_report(ts=T_OLD))

        result = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

        assert result["phases"]["m3a"]["gate_status"] == "FAIL"

    def test_rc_with_stale_status_field_not_pass(self, tmp_path):
        rc = {**_rc(ts=T_RC), "status": "STALE", "result": "STALE"}
        _write_engine_inputs(tmp_path, m3a=rc,
                             frontend_full_suite=_report(ts=T_OLD), preflight=_report(ts=T_OLD))

        result = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

        assert result["phases"]["m3a"]["decision"] == "NO_GO"

    def test_rc_with_blocked_status_field_not_pass(self, tmp_path):
        rc = {**_rc(ts=T_RC), "status": "BLOCKED", "result": "BLOCKED"}
        _write_engine_inputs(tmp_path, m3a=rc,
                             frontend_full_suite=_report(ts=T_OLD), preflight=_report(ts=T_OLD))

        result = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

        assert result["phases"]["m3a"]["decision"] == "NO_GO"

    def test_preflight_newer_than_rc_is_stale(self, tmp_path):
        _write_engine_inputs(tmp_path, m3a=_rc(ts=T_OLD),
                             frontend_full_suite=_report(ts=T_OLD), preflight=_report(ts=T_NEW))

        result = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

        assert result["phases"]["m3a"]["decision"] == "NO_GO"
        blocker_ids = [b["id"] for b in result["phases"]["m3a"]["blockers"]]
        assert "m3a_rc_stale" in blocker_ids

    def test_m4_gate_unaffected_by_m3a_stale(self, tmp_path):
        _write_engine_inputs(tmp_path, m3a=_rc(ts=T_OLD),
                             frontend_full_suite=_report(ts=T_NEW), preflight=_report(ts=T_OLD))

        result = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

        assert result["phases"]["m4"]["decision"] == "GO"

    def test_regenerated_rc_clears_stale(self, tmp_path):
        _write_engine_inputs(tmp_path, m3a=_rc(ts=T_NEW),
                             frontend_full_suite=_report(ts=T_OLD), preflight=_report(ts=T_OLD))

        result = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

        assert result["phases"]["m3a"]["decision"] == "GO"
        assert result["overall"]["release_allowed"] is True
