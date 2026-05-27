from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
CURRENT_DIR = REPORTS_DIR / "current"
DEFAULT_BASELINE = REPORTS_DIR / "regression_lock_baseline.json"
DEFAULT_SCOPE_CHANGE_LOG = REPORTS_DIR / "scope_change_log.json"
DEFAULT_OUTPUT = CURRENT_DIR / "regression_lock_result.json"

REGRESSION_THRESHOLD = 0.20


def load_baseline(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, int)}


def load_scope_change_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def check_report_regression(
    report_name: str,
    report: dict[str, Any],
    baseline_collected: int,
) -> str | None:
    """Returns a blocker string if collected dropped >20% without justification, else None."""
    current = report.get("collected")
    if isinstance(current, bool) or not isinstance(current, int):
        return None
    if baseline_collected <= 0:
        return None
    drop = baseline_collected - current
    if drop <= 0:
        return None
    drop_fraction = drop / baseline_collected
    if drop_fraction <= REGRESSION_THRESHOLD:
        return None
    if report.get("scope_change_reason") and report.get("approval"):
        return None
    return (
        f"{report_name}: collected regression — dropped from {baseline_collected} to {current} "
        f"({drop_fraction:.0%} > {int(REGRESSION_THRESHOLD * 100)}% threshold); "
        "add scope_change_reason and approval fields to override"
    )


def evaluate_regression_lock(
    report_dir: Path = CURRENT_DIR,
    baseline_path: Path = DEFAULT_BASELINE,
    scope_change_log_path: Path = DEFAULT_SCOPE_CHANGE_LOG,
    *,
    timestamp: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, int]]:
    timestamp = timestamp or datetime.now(UTC).isoformat()
    baseline = load_baseline(baseline_path)
    scope_change_log = load_scope_change_log(scope_change_log_path)

    checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    new_baseline = dict(baseline)

    for report_name, baseline_collected in baseline.items():
        report_path = report_dir / report_name
        if not report_path.exists():
            checks.append({"report": report_name, "status": "SKIP", "reason": "report not found"})
            continue
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            checks.append({"report": report_name, "status": "SKIP", "reason": "unreadable report"})
            continue
        if not isinstance(report, dict):
            checks.append({"report": report_name, "status": "SKIP", "reason": "invalid report format"})
            continue

        blocker = check_report_regression(report_name, report, baseline_collected)
        current = report.get("collected")

        if blocker:
            blockers.append(blocker)
            checks.append({"report": report_name, "status": "BLOCKED", "reason": blocker})
        else:
            if (
                isinstance(current, int)
                and not isinstance(current, bool)
                and current < baseline_collected
                and report.get("scope_change_reason")
                and report.get("approval")
            ):
                scope_change_log.append({
                    "timestamp": timestamp,
                    "report": report_name,
                    "baseline_collected": baseline_collected,
                    "new_collected": current,
                    "scope_change_reason": report.get("scope_change_reason"),
                    "approval": report.get("approval"),
                })
            if isinstance(current, int) and not isinstance(current, bool):
                new_baseline[report_name] = current
            checks.append({"report": report_name, "status": "PASS", "reason": None})

    overall = "BLOCKED" if blockers else "PASS"
    result: dict[str, Any] = {
        "report_schema_version": 1,
        "report_name": "regression_lock_result",
        "generated_by": "gate_regression_lock",
        "timestamp": timestamp,
        "result": overall,
        "status": overall,
        "checks": checks,
        "blockers": [{"reason": b} for b in blockers],
        "baseline_source": str(baseline_path),
    }
    return result, scope_change_log, new_baseline


def write_results(
    result: dict[str, Any],
    scope_change_log: list[dict[str, Any]],
    new_baseline: dict[str, int],
    output_path: Path,
    baseline_path: Path,
    scope_change_log_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    scope_change_log_path.parent.mkdir(parents=True, exist_ok=True)
    scope_change_log_path.write_text(json.dumps(scope_change_log, indent=2) + "\n", encoding="utf-8")
    if result["result"] != "BLOCKED":
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(new_baseline, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gate Regression Lock: blocks gates when collected drops >20% without justification."
    )
    parser.add_argument("--report-dir", type=Path, default=CURRENT_DIR)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--scope-change-log", type=Path, default=DEFAULT_SCOPE_CHANGE_LOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    result, scope_change_log, new_baseline = evaluate_regression_lock(
        args.report_dir, args.baseline, args.scope_change_log
    )
    write_results(result, scope_change_log, new_baseline, args.output, args.baseline, args.scope_change_log)

    print(f"Regression Lock = {result['result']}")
    for check in result["checks"]:
        reason_str = f" — {check['reason']}" if check.get("reason") else ""
        print(f"  [{check['status']}] {check['report']}{reason_str}")
    if result["result"] != "BLOCKED":
        print(f"Baseline updated: {args.baseline}")
    print(f"Wrote: {args.output}")
    return 0 if result["result"] != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
