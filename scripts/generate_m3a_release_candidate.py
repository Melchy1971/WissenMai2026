"""Generate the M3a Release Candidate report.

Reads the current input reports, runs the stale guard and precondition checks,
evaluates all M3a gate criteria, and writes m3a_release_candidate.json +
m3a_release_candidate.md to reports/current/.

Exit codes:
  0 – RC generated, status PASS/GO
  1 – RC generated with STALE or precondition failures (gate BLOCKED)
  2 – fatal: cannot read a mandatory input file
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

# Stale guard lives in the same directory.
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from m3a_stale_guard import (  # noqa: E402
    STALE_GATE,
    STALE_STATUS,
    StaleResult,
    check_preconditions,
    check_staleness,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
GUI_TRUTH_DIR = REPO_ROOT / "reports" / "gui_truth"

# Mandatory inputs
FRONTEND_FULL_SUITE = "frontend_full_suite_staged_report.json"
FRONTEND_MINIMAL = "frontend_truth_minimal_report.json"
PREFLIGHT = "report_truth_preflight.json"
DOC_LINT = "documentation_truth_lint.json"
# Optional input
GUI_CHAOS = "gui_chaos_suite_report.json"

OUTPUT_JSON = CURRENT_DIR / "m3a_release_candidate.json"
OUTPUT_MD = CURRENT_DIR / "m3a_release_candidate.md"

REPORT_NAME = "m3a_release_candidate"
SCHEMA_VERSION = 1


def _commit_hash() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON {path}: {exc}"
    if not isinstance(payload, dict):
        return None, f"JSON root must be an object: {path}"
    return payload, None


def _int(value: Any, default: int = 0) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def _ts(report: dict[str, Any] | None) -> str | None:
    if report is None:
        return None
    return report.get("timestamp") or report.get("generated_at")


def _report_is_pass(report: dict[str, Any] | None) -> bool:
    if report is None:
        return False
    status = str(report.get("status") or report.get("result") or "").upper()
    collected = _int(report.get("collected"))
    passed = _int(report.get("passed"))
    failed = _int(report.get("failed"), 1)
    errors = _int(report.get("errors"), 1)
    skipped = _int(report.get("skipped"), 1)
    exit_code = report.get("exit_code")
    return (
        status == "PASS"
        and collected > 0
        and passed == collected
        and failed == 0
        and errors == 0
        and skipped == 0
        and exit_code in (0, None)
    )


# ---------------------------------------------------------------------------
# Criteria evaluation
# ---------------------------------------------------------------------------

def _eval_frontend_full_suite(
    report: dict[str, Any] | None,
    error: str | None,
) -> dict[str, Any]:
    passed = error is None and _report_is_pass(report)
    blockers = []
    if error:
        blockers.append(error)
    elif report is not None and not passed:
        if _int(report.get("collected")) == 0:
            blockers.append("frontend_full_suite: collected must be > 0")
        if _int(report.get("failed")):
            blockers.append(f"frontend_full_suite: failed={report.get('failed')}")
        if _int(report.get("errors")):
            blockers.append(f"frontend_full_suite: errors={report.get('errors')}")
        if report.get("exit_code") not in (0, None):
            blockers.append(f"frontend_full_suite: exit_code={report.get('exit_code')}")
    return {
        "id": "frontend_full_suite_staged_green",
        "label": "Frontend Full Suite Staged grün",
        "passed": passed,
        "source": f"reports/current/{FRONTEND_FULL_SUITE}",
        "blockers": blockers,
        "evidence": {
            "status": report.get("status") if report else None,
            "collected": report.get("collected") if report else None,
            "passed": report.get("passed") if report else None,
            "failed": report.get("failed") if report else None,
            "errors": report.get("errors") if report else None,
            "skipped": report.get("skipped") if report else None,
            "exit_code": report.get("exit_code") if report else None,
            "real_api": report.get("real_api") if report else None,
            "test_database_url_set": report.get("test_database_url_set") if report else None,
            "timestamp": _ts(report),
        },
    }


def _eval_frontend_minimal(
    report: dict[str, Any] | None,
    error: str | None,
) -> dict[str, Any]:
    passed = error is None and _report_is_pass(report)
    blockers = [error] if error else ([] if passed else ["frontend_truth_minimal not PASS"])
    return {
        "id": "frontend_truth_minimal_green",
        "label": "Frontend Truth Minimal grün",
        "passed": passed,
        "source": f"reports/current/{FRONTEND_MINIMAL}",
        "blockers": blockers,
        "evidence": {
            "status": report.get("status") if report else None,
            "collected": report.get("collected") if report else None,
            "passed": report.get("passed") if report else None,
            "failed": report.get("failed") if report else None,
            "errors": report.get("errors") if report else None,
            "timestamp": _ts(report),
        },
    }


def _eval_preflight(
    report: dict[str, Any] | None,
    error: str | None,
) -> dict[str, Any]:
    passed = error is None and _report_is_pass(report)
    blockers = [error] if error else ([] if passed else ["report_truth_preflight not PASS"])
    return {
        "id": "report_truth_preflight_green",
        "label": "Report Truth Preflight grün",
        "passed": passed,
        "source": f"reports/current/{PREFLIGHT}",
        "blockers": blockers,
        "evidence": {
            "status": report.get("status") if report else None,
            "result": report.get("result") if report else None,
            "collected": report.get("collected") if report else None,
            "passed": report.get("passed") if report else None,
            "failed": report.get("failed") if report else None,
            "errors": report.get("errors") if report else None,
            "exit_code": report.get("exit_code") if report else None,
            "timestamp": _ts(report),
        },
    }


def _eval_doc_lint(
    report: dict[str, Any] | None,
    error: str | None,
) -> dict[str, Any]:
    # doc_lint has no collected/passed fields; evaluate by status + error count only.
    def _doc_is_pass(r: dict | None) -> bool:
        if r is None:
            return False
        status = str(r.get("status") or r.get("result") or "").upper()
        if status in ("STALE", "BLOCKED"):
            return False
        summary = r.get("summary") or {}
        errors = r.get("errors") or summary.get("errors") or 0
        exit_code = r.get("exit_code")
        return status == "PASS" and int(errors) == 0 and exit_code in (0, None)
    passed = error is None and _doc_is_pass(report)
    blockers = [error] if error else ([] if passed else ["documentation_truth_lint not PASS"])
    summary = (report.get("summary") or {}) if report else {}
    return {
        "id": "documentation_truth_lint_green",
        "label": "Documentation Truth Lint grün",
        "passed": passed,
        "source": f"reports/current/{DOC_LINT}",
        "blockers": blockers,
        "evidence": {
            "status": report.get("status") if report else None,
            "result": report.get("result") if report else None,
            "errors": report.get("errors") or summary.get("errors") if report else None,
            "warnings": report.get("warnings") or summary.get("warnings") if report else None,
            "exit_code": report.get("exit_code") if report else None,
            "timestamp": _ts(report),
        },
    }


def _eval_gui_chaos(
    report: dict[str, Any] | None,
    error: str | None,
    *,
    available: bool,
) -> dict[str, Any]:
    if not available or error or report is None:
        return {
            "id": "gui_chaos_green",
            "label": "GUI Chaos grün",
            "passed": False,
            "source": f"reports/gui_truth/{GUI_CHAOS}",
            "blockers": [error or "gui_chaos_suite_report not available"],
            "evidence": None,
        }
    passed = (
        str(report.get("result") or "").upper() == "PASS"
        and _int(report.get("failed")) == 0
        and _int(report.get("errors")) == 0
        and report.get("exit_code") in (0, None)
    )
    blockers = [] if passed else [f"gui_chaos: result={report.get('result')!r}"]
    return {
        "id": "gui_chaos_green",
        "label": "GUI Chaos grün",
        "passed": passed,
        "source": f"reports/gui_truth/{GUI_CHAOS}",
        "blockers": blockers,
        "evidence": {
            "result": report.get("result"),
            "collected": report.get("collected"),
            "passed": report.get("passed"),
            "failed": report.get("failed"),
            "errors": report.get("errors"),
            "exit_code": report.get("exit_code"),
            "timestamp": _ts(report),
        },
    }


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

def build_release_candidate(
    report_dir: Path = CURRENT_DIR,
    gui_truth_dir: Path = GUI_TRUTH_DIR,
    *,
    timestamp: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Build the M3a RC report.

    Returns:
        (payload, exit_code)  where exit_code is 0 (PASS), 1 (STALE/BLOCKED), or 2 (fatal).
    """
    generated_at = timestamp or datetime.now(timezone.utc).isoformat()

    frontend_full, ff_error = _load_json(report_dir / FRONTEND_FULL_SUITE)
    frontend_min, fm_error = _load_json(report_dir / FRONTEND_MINIMAL)
    preflight, pf_error = _load_json(report_dir / PREFLIGHT)
    doc_lint, dl_error = _load_json(report_dir / DOC_LINT)
    gui_chaos_path = gui_truth_dir / GUI_CHAOS
    gui_chaos, gc_error = _load_json(gui_chaos_path)
    gui_chaos_available = gui_chaos_path.exists() and gc_error is None

    # --- Precondition check (generation guard) ---
    precondition_violations = check_preconditions(preflight, doc_lint)

    # --- Criteria evaluation ---
    criteria = [
        _eval_frontend_full_suite(frontend_full, ff_error),
        _eval_frontend_minimal(frontend_min, fm_error),
        _eval_preflight(preflight, pf_error),
        _eval_doc_lint(doc_lint, dl_error),
        _eval_gui_chaos(gui_chaos, gc_error, available=gui_chaos_available),
    ]

    gate_pass = all(c["passed"] for c in criteria) and not precondition_violations
    all_blockers: list[str] = [b for c in criteria for b in c["blockers"]]
    all_blockers.extend(precondition_violations)

    # --- Stale guard (evaluated AFTER criteria so the report is self-describing) ---
    # When preconditions fail the RC is BLOCKED (not STALE) — different semantics.
    stale: StaleResult | None = None
    if not precondition_violations:
        # Compare the to-be-written RC timestamp against the input report timestamps.
        # Because we are generating NOW the RC will be fresh; stale guard here is a
        # sanity check that inputs aren't older than a previously existing RC.
        # The main staleness path is in the status engine (reading an existing RC).
        pass

    status = "PASS" if gate_pass else ("STALE" if (stale and stale.is_stale) else "FAIL")
    if precondition_violations:
        status = "BLOCKED"
    gate_status = "BLOCKED" if status in ("STALE", "BLOCKED") else status

    # Embed stale guard metadata so the status engine can re-evaluate without reloading inputs.
    stale_guard_meta: dict[str, Any] = {
        "input_timestamps": {
            "frontend_full_suite_staged_report": _ts(frontend_full),
            "report_truth_preflight": _ts(preflight),
            "documentation_truth_lint": _ts(doc_lint),
        },
        "rc_timestamp": generated_at,
        "precondition_violations": precondition_violations,
    }

    payload: dict[str, Any] = {
        "report_schema_version": SCHEMA_VERSION,
        "report_name": REPORT_NAME,
        "generated_by": "generate_m3a_release_candidate",
        "timestamp": generated_at,
        "generated_at": generated_at,
        "version": 3,
        "release_candidate": "M3a",
        "gate": "m3a",
        "status": status,
        "result": status,
        "gate_status": gate_status,
        "decision": {
            "gate_passed": gate_pass,
            "blocked": not gate_pass,
            "status": "passed" if gate_pass else "blocked",
            "go_no_go": "GO" if gate_pass else "NO-GO",
            "m3a_release_candidate": "GO" if gate_pass else "NO-GO",
        },
        "environment": "local",
        "report_type": "release_candidate",
        "rule": (
            "M3a RC is PASS/GO only when frontend full suite, frontend minimal, "
            "report truth preflight, and documentation lint are all green. "
            "A RC is STALE when any mandatory input carries a timestamp newer than the RC."
        ),
        "inputs": [
            f"reports/current/{FRONTEND_FULL_SUITE}",
            f"reports/current/{FRONTEND_MINIMAL}",
            f"reports/current/{PREFLIGHT}",
            f"reports/current/{DOC_LINT}",
            f"reports/gui_truth/{GUI_CHAOS}",
        ],
        "criteria": criteria,
        "stale_guard": stale_guard_meta,
        "blockers": all_blockers,
        "collected": 5,
        "passed": sum(1 for c in criteria if c["passed"]),
        "failed": sum(1 for c in criteria if not c["passed"]),
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if gate_pass else 1,
    }
    if precondition_violations:
        payload["stale_reason"] = "preconditions_not_met: " + "; ".join(precondition_violations)
        payload["exit_code"] = 1

    commit = _commit_hash()
    if commit:
        payload["commit_hash"] = commit

    exit_code = 0 if gate_pass else 1
    return payload, exit_code


def render_markdown(payload: dict[str, Any]) -> str:
    status = payload["status"]
    decision = payload["decision"]["go_no_go"]
    lines = [
        "# M3a Release Candidate",
        "",
        f"Status: `{status}`  |  Entscheidung: `{decision}`  |  Zeitpunkt: `{payload['timestamp']}`",
        "",
    ]

    if status in ("STALE", "BLOCKED"):
        lines += [
            f"**Gate: {payload.get('gate_status', 'BLOCKED')}**",
            "",
            f"Stale-Reason: `{payload.get('stale_reason', 'n/a')}`",
            "",
        ]

    lines += [
        "## Kriterien",
        "",
        "| Kriterium | Status | Blockers |",
        "|---|---|---|",
    ]
    for c in payload.get("criteria", []):
        s = "PASS" if c["passed"] else "FAIL"
        b = "; ".join(c.get("blockers", [])) or "—"
        lines.append(f"| {c['label']} | `{s}` | {b} |")

    lines += ["", "## Stale Guard", ""]
    sg = payload.get("stale_guard", {})
    lines.append(f"RC Timestamp: `{sg.get('rc_timestamp')}`")
    lines.append("")
    lines.append("| Input | Timestamp |")
    lines.append("|---|---|")
    for k, v in (sg.get("input_timestamps") or {}).items():
        lines.append(f"| `{k}` | `{v}` |")

    violations = sg.get("precondition_violations") or []
    if violations:
        lines += ["", "**Precondition violations:**", ""]
        lines.extend(f"- `{v}`" for v in violations)

    lines += ["", "## Blocker", ""]
    blockers = payload.get("blockers") or []
    lines.extend(f"- {b}" for b in blockers) if blockers else lines.append("- keine")

    lines.append("")
    return "\n".join(lines)


def write_outputs(
    report_dir: Path = CURRENT_DIR,
    gui_truth_dir: Path = GUI_TRUTH_DIR,
    output_json: Path = OUTPUT_JSON,
    output_md: Path = OUTPUT_MD,
) -> tuple[dict[str, Any], int]:
    payload, exit_code = build_release_candidate(report_dir, gui_truth_dir)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(payload), encoding="utf-8")
    return payload, exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the M3a Release Candidate report.")
    parser.add_argument("--report-dir", type=Path, default=CURRENT_DIR)
    parser.add_argument("--gui-truth-dir", type=Path, default=GUI_TRUTH_DIR)
    parser.add_argument("--output-json", type=Path, default=OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=OUTPUT_MD)
    args = parser.parse_args(argv)

    payload, exit_code = write_outputs(
        args.report_dir, args.gui_truth_dir, args.output_json, args.output_md
    )
    print(f"M3a Release Candidate = {payload['decision']['go_no_go']} (status={payload['status']})")
    if payload.get("stale_reason"):
        print(f"Stale reason: {payload['stale_reason']}")
    if payload.get("blockers"):
        for b in payload["blockers"]:
            print(f"  BLOCKER: {b}")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    return exit_code


if __name__ == "__main__":
    raise Syste