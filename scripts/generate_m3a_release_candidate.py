"""Generate the M3a Release Candidate report."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from m3a_stale_guard import check_preconditions  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
GUI_TRUTH_DIR = REPO_ROOT / "reports" / "gui_truth"

RUNTIME_CONNECTIVITY_GATE = "runtime_connectivity_gate.json"
FRONTEND_FULL_SUITE = "frontend_full_suite_staged_report.json"
FRONTEND_FULL_SUITE_ARCHIVE = (
    REPO_ROOT / "reports" / "archive" / "legacy" / "20260605T100000Z" / FRONTEND_FULL_SUITE
)
PREFLIGHT = "report_truth_preflight.json"
DOC_LINT = "documentation_truth_lint.json"

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


def _load_frontend_completion(report_dir: Path) -> tuple[dict[str, Any] | None, str | None, str, str | None]:
    current_path = report_dir / FRONTEND_FULL_SUITE
    report, error = _load_json(current_path)
    if error is None:
        return report, None, f"reports/current/{FRONTEND_FULL_SUITE}", None

    archived, archive_error = _load_json(FRONTEND_FULL_SUITE_ARCHIVE)
    if archive_error is None:
        return (
            archived,
            None,
            FRONTEND_FULL_SUITE_ARCHIVE.relative_to(REPO_ROOT).as_posix(),
            "current report archived; immutable M3a completion evidence is used",
        )

    return (
        None,
        f"{error}; archive fallback invalid: {archive_error}",
        f"reports/current/{FRONTEND_FULL_SUITE}",
        None,
    )


def _int(value: Any, default: int = 0) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def _ts(report: dict[str, Any] | None) -> str | None:
    if report is None:
        return None
    return report.get("timestamp") or report.get("generated_at")


def _decision(report: dict[str, Any] | None) -> str | None:
    if not report:
        return None
    raw_decision = report.get("decision")
    if isinstance(raw_decision, dict):
        raw = raw_decision.get("go_no_go") or raw_decision.get("result")
    else:
        raw = raw_decision
    return str(raw).upper().replace("-", "_") if raw is not None else None


def _report_is_pass(report: dict[str, Any] | None, *, counters_required: bool = True) -> bool:
    if report is None:
        return False
    status = str(report.get("status") or report.get("result") or "").upper()
    if status != "PASS":
        return False
    if _decision(report) not in {None, "GO"}:
        return False
    if not counters_required:
        return _int(report.get("errors")) == 0 and report.get("exit_code") in (0, None)
    collected = _int(report.get("collected"))
    return (
        collected > 0
        and _int(report.get("passed")) == collected
        and _int(report.get("failed"), 1) == 0
        and _int(report.get("errors"), 1) == 0
        and _int(report.get("skipped"), 1) == 0
        and report.get("exit_code") in (0, None)
    )


def _runtime_criterion(report: dict[str, Any] | None, error: str | None) -> dict[str, Any]:
    passed = error is None and _report_is_pass(report)
    return {
        "id": "runtime_connectivity_gate_green",
        "label": "Runtime Connectivity Gate gruen",
        "passed": passed,
        "source": f"reports/current/{RUNTIME_CONNECTIVITY_GATE}",
        "blockers": [error] if error else ([] if passed else ["runtime_connectivity_gate not PASS/GO"]),
        "evidence": {
            "status": report.get("status") if report else None,
            "result": report.get("result") if report else None,
            "decision": _decision(report),
            "score_pct": report.get("score_pct") if report else None,
            "passed_checks": report.get("passed_checks") if report else None,
            "total_checks": report.get("total_checks") if report else None,
            "exit_code": report.get("exit_code") if report else None,
            "timestamp": _ts(report),
        },
    }


def _frontend_criterion(
    report: dict[str, Any] | None,
    error: str | None,
    source: str,
    note: str | None,
) -> dict[str, Any]:
    passed = error is None and _report_is_pass(report)
    blockers: list[str] = []
    if error:
        blockers.append(error)
    elif not passed:
        blockers.append("frontend_full_suite_staged_report not PASS")
    criterion = {
        "id": "frontend_full_suite_staged_green",
        "label": "Frontend Full Suite Staged gruen",
        "passed": passed,
        "source": source,
        "blockers": blockers,
        "evidence": {
            "status": report.get("status") if report else None,
            "collected": report.get("collected") if report else None,
            "passed": report.get("passed") if report else None,
            "failed": report.get("failed") if report else None,
            "errors": report.get("errors") if report else None,
            "skipped": report.get("skipped") if report else None,
            "exit_code": report.get("exit_code") if report else None,
            "timestamp": _ts(report),
        },
    }
    if note:
        criterion["note"] = note
    return criterion


def _preflight_criterion(report: dict[str, Any] | None, error: str | None) -> dict[str, Any]:
    passed = error is None and _report_is_pass(report)
    return {
        "id": "report_truth_preflight_green",
        "label": "Report Truth Preflight gruen",
        "passed": passed,
        "source": f"reports/current/{PREFLIGHT}",
        "blockers": [error] if error else ([] if passed else ["report_truth_preflight not PASS"]),
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


def _doc_lint_criterion(report: dict[str, Any] | None, error: str | None) -> dict[str, Any]:
    summary = report.get("summary") if report and isinstance(report.get("summary"), dict) else {}
    errors = _int(report.get("errors") if report else None, _int(summary.get("errors"), 1))
    passed = error is None and _report_is_pass(report, counters_required=False) and errors == 0
    return {
        "id": "documentation_truth_lint_green",
        "label": "Documentation Truth Lint gruen",
        "passed": passed,
        "source": f"reports/current/{DOC_LINT}",
        "blockers": [error] if error else ([] if passed else ["documentation_truth_lint not PASS"]),
        "evidence": {
            "status": report.get("status") if report else None,
            "result": report.get("result") if report else None,
            "errors": errors if report else None,
            "warnings": report.get("warnings") or summary.get("warnings") if report else None,
            "exit_code": report.get("exit_code") if report else None,
            "timestamp": _ts(report),
        },
    }


def build_release_candidate(
    report_dir: Path = CURRENT_DIR,
    gui_truth_dir: Path = GUI_TRUTH_DIR,
    *,
    timestamp: str | None = None,
) -> tuple[dict[str, Any], int]:
    del gui_truth_dir
    generated_at = timestamp or datetime.now(timezone.utc).isoformat()

    runtime_gate, rt_error = _load_json(report_dir / RUNTIME_CONNECTIVITY_GATE)
    frontend, ff_error, frontend_source, frontend_note = _load_frontend_completion(report_dir)
    preflight, pf_error = _load_json(report_dir / PREFLIGHT)
    doc_lint, dl_error = _load_json(report_dir / DOC_LINT)

    precondition_violations = check_preconditions(preflight, doc_lint)
    criteria = [
        _runtime_criterion(runtime_gate, rt_error),
        _frontend_criterion(frontend, ff_error, frontend_source, frontend_note),
        _preflight_criterion(preflight, pf_error),
        _doc_lint_criterion(doc_lint, dl_error),
    ]

    gate_pass = all(item["passed"] for item in criteria) and not precondition_violations
    blockers = [blocker for criterion in criteria for blocker in criterion["blockers"]]
    blockers.extend(precondition_violations)
    status = "PASS" if gate_pass else ("BLOCKED" if precondition_violations else "FAIL")

    payload: dict[str, Any] = {
        "report_schema_version": SCHEMA_VERSION,
        "report_name": REPORT_NAME,
        "generated_by": "gate_validator",
        "timestamp": generated_at,
        "generated_at": generated_at,
        "version": 6,
        "release_candidate": "M3a",
        "gate": "m3a",
        "status": status,
        "result": status,
        "gate_status": "PASS" if gate_pass else "BLOCKED",
        "decision": {
            "gate_passed": gate_pass,
            "blocked": not gate_pass,
            "status": "passed" if gate_pass else "blocked",
            "go_no_go": "GO" if gate_pass else "NO_GO",
            "m3a_release_candidate": "GO" if gate_pass else "NO_GO",
        },
        "environment": "local",
        "report_type": "release_candidate",
        "source_command": "python scripts/generate_m3a_release_candidate.py",
        "rule": (
            "M3a RC is PASS/GO only when runtime_connectivity_gate, frontend full-suite "
            "completion evidence, report_truth_preflight, and documentation_truth_lint are green. "
            "A RC is STALE when any mandatory current input carries a timestamp newer than the RC."
        ),
        "inputs": [
            f"reports/current/{RUNTIME_CONNECTIVITY_GATE}",
            frontend_source,
            f"reports/current/{PREFLIGHT}",
            f"reports/current/{DOC_LINT}",
        ],
        "criteria": criteria,
        "stale_guard": {
            "input_timestamps": {
                "runtime_connectivity_gate": _ts(runtime_gate),
                "frontend_full_suite_staged_report": _ts(frontend),
                "report_truth_preflight": _ts(preflight),
                "documentation_truth_lint": _ts(doc_lint),
            },
            "rc_timestamp": generated_at,
            "precondition_violations": precondition_violations,
        },
        "blockers": blockers,
        "collected": len(criteria),
        "passed": sum(1 for item in criteria if item["passed"]),
        "failed": sum(1 for item in criteria if not item["passed"]),
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if gate_pass else 1,
    }
    if precondition_violations:
        payload["stale_reason"] = "preconditions_not_met: " + "; ".join(precondition_violations)

    commit = _commit_hash()
    if commit:
        payload["commit_hash"] = commit
    return payload, 0 if gate_pass else 1


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# M3a Release Candidate",
        "",
        f"Status: `{payload['status']}` | Entscheidung: `{payload['decision']['go_no_go']}` | Zeitpunkt: `{payload['timestamp']}`",
        "",
        "## Kriterien",
        "",
        "| Kriterium | Status | Blockers |",
        "|---|---|---|",
    ]
    for criterion in payload.get("criteria", []):
        status = "PASS" if criterion["passed"] else "FAIL"
        blockers = "; ".join(criterion.get("blockers", [])) or "-"
        lines.append(f"| {criterion['label']} | `{status}` | {blockers} |")

    lines.extend(["", "## Stale Guard", ""])
    stale_guard = payload.get("stale_guard", {})
    lines.append(f"RC Timestamp: `{stale_guard.get('rc_timestamp')}`")
    lines.extend(["", "| Input | Timestamp |", "|---|---|"])
    for key, value in (stale_guard.get("input_timestamps") or {}).items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(["", "## Blocker", ""])
    blockers = payload.get("blockers") or []
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- keine")
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

    payload, exit_code = write_outputs(args.report_dir, args.gui_truth_dir, args.output_json, args.output_md)
    print(f"M3a Release Candidate = {payload['decision']['go_no_go']} (status={payload['status']})")
    if payload.get("blockers"):
        for blocker in payload["blockers"]:
            print(f"  BLOCKER: {blocker}")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
