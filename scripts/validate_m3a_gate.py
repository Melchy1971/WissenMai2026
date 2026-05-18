from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_FRONTEND_REPORT = REPORTS_DIR / "frontend_truth_report.json"
DEFAULT_CONTRACT_REPORT = REPORTS_DIR / "contract_test_report.json"
DEFAULT_POSTGRES_REPORT = REPORTS_DIR / "postgres_truth_report.json"
DEFAULT_OUTPUT_JSON = REPORTS_DIR / "m3a_gate_result.json"
DEFAULT_OUTPUT_MD = REPORTS_DIR / "m3a_gate_result.md"

RULE_COUNT = 7


@dataclass(frozen=True)
class RuleResult:
    id: str
    passed: bool
    blocker: str | None = None


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing report: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON report {path}: {exc}"
    if not isinstance(payload, dict):
        return None, f"report root must be a JSON object: {path}"
    return payload, None


def _as_int(value: Any, default: int | None = None) -> int | None:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def _frontend_rules(report: dict[str, Any] | None, load_error: str | None) -> list[RuleResult]:
    if load_error or report is None:
        reason = load_error or "frontend_truth_report.json unavailable"
        return [
            RuleResult("frontend_truth_passed_equals_collected", False, reason),
            RuleResult("frontend_truth_failed_zero", False, reason),
            RuleResult("frontend_truth_skipped_zero", False, reason),
            RuleResult("no_api_unreachable_in_normalflow", False, reason),
            RuleResult("no_workspace_not_configured_after_valid_login", False, reason),
        ]

    collected = _as_int(report.get("collected"))
    passed = _as_int(report.get("passed"))
    failed = _as_int(report.get("failed"))
    skipped = _as_int(report.get("skipped"))

    results = [
        RuleResult(
            "frontend_truth_passed_equals_collected",
            isinstance(collected, int) and collected > 0 and passed == collected,
            None
            if isinstance(collected, int) and collected > 0 and passed == collected
            else f"frontend_truth passed ({passed!r}) must equal collected ({collected!r})",
        ),
        RuleResult(
            "frontend_truth_failed_zero",
            failed == 0,
            None if failed == 0 else f"frontend_truth failed must be 0, got {failed!r}",
        ),
        RuleResult(
            "frontend_truth_skipped_zero",
            skipped == 0,
            None if skipped == 0 else f"frontend_truth skipped must be 0, got {skipped!r}",
        ),
    ]

    api_unreachable_hits = _find_api_unreachable_in_normalflow(report)
    results.append(
        RuleResult(
            "no_api_unreachable_in_normalflow",
            not api_unreachable_hits,
            None
            if not api_unreachable_hits
            else "API_UNREACHABLE appeared in normal flow: " + "; ".join(api_unreachable_hits[:5]),
        )
    )

    workspace_hits = _find_workspace_missing_after_valid_login(report)
    results.append(
        RuleResult(
            "no_workspace_not_configured_after_valid_login",
            not workspace_hits,
            None
            if not workspace_hits
            else "WORKSPACE_NOT_CONFIGURED after valid membership login: "
            + "; ".join(workspace_hits[:5]),
        )
    )

    return results


def _iter_flow_strings(report: dict[str, Any]) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for key in ("failed_flows", "failed_tests", "passed_tests", "skipped_tests"):
        value = report.get(key) or []
        if not isinstance(value, list):
            continue
        for entry in value:
            if isinstance(entry, dict):
                name = str(entry.get("name") or entry.get("nodeid") or "unknown")
                text = f"{name} {entry.get('error') or entry.get('message') or ''}"
            else:
                name = str(entry)
                text = name
            items.append((name, text))
    return items


def _is_intentional_unreachable_flow(name: str) -> bool:
    lowered = name.lower()
    return any(
        token in lowered
        for token in (
            "backend unreachable",
            "api_unreachable",
            "network error",
            "cors",
            "timeout",
            "nicht erreichbar",
        )
    )


def _find_api_unreachable_in_normalflow(report: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for name, text in _iter_flow_strings(report):
        if "API_UNREACHABLE" in text and not _is_intentional_unreachable_flow(name):
            hits.append(name)
    return hits


def _is_intentional_workspace_missing_flow(name: str) -> bool:
    lowered = name.lower()
    return any(
        token in lowered
        for token in (
            "no workspace",
            "no-membership",
            "without a validated workspace",
            "workspace missing",
            "workspace-not-configured",
            "workspaces fehlt",
            "keine workspace",
            "zero workspace",
        )
    )


def _looks_like_valid_login_flow(name: str) -> bool:
    lowered = name.lower()
    return any(
        token in lowered
        for token in (
            "successful login",
            "valid membership",
            "membership workspace",
            "bootstrap resolves",
            "workspace from membership",
            "login with truth credentials",
        )
    )


def _find_workspace_missing_after_valid_login(report: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for name, text in _iter_flow_strings(report):
        if "WORKSPACE_NOT_CONFIGURED" not in text:
            continue
        if _is_intentional_workspace_missing_flow(name):
            continue
        if _looks_like_valid_login_flow(name) or "valid" in name.lower() or "membership" in name.lower():
            hits.append(name)
    return hits


def _green_test_report_blockers(report: dict[str, Any], *, kind: str) -> list[str]:
    blockers: list[str] = []
    collected = _as_int(report.get("collected"))
    passed = _as_int(report.get("passed"))
    failed = _as_int(report.get("failed"), 0)
    skipped = _as_int(report.get("skipped"), 0)
    errors = _as_int(report.get("errors"), 0)

    if not isinstance(collected, int) or collected <= 0:
        blockers.append(f"{kind} collected must be > 0, got {collected!r}")
    if passed != collected:
        blockers.append(f"{kind} passed ({passed!r}) must equal collected ({collected!r})")
    if failed != 0:
        blockers.append(f"{kind} failed must be 0, got {failed!r}")
    if skipped != 0:
        blockers.append(f"{kind} skipped must be 0, got {skipped!r}")
    if errors != 0:
        blockers.append(f"{kind} errors must be 0, got {errors!r}")

    exit_code = (
        report.get("pytest_exit_code")
        if "pytest_exit_code" in report
        else report.get("exit_code", report.get("playwright_exit_code"))
    )
    if exit_code not in (0, None):
        blockers.append(f"{kind} exit code must be 0, got {exit_code!r}")
    return blockers


def _postgres_rule(report: dict[str, Any] | None, load_error: str | None) -> RuleResult:
    if load_error or report is None:
        return RuleResult("postgres_truth_green", False, load_error or "postgres_truth_report unavailable")
    blockers = _green_test_report_blockers(report, kind="postgres_truth")
    if report.get("test_database_url_set") is not True:
        blockers.append("postgres_truth TEST_DATABASE_URL proof missing")
    return RuleResult(
        "postgres_truth_green",
        not blockers,
        None if not blockers else "; ".join(blockers),
    )


def _contract_rule(report: dict[str, Any] | None, load_error: str | None) -> RuleResult:
    if load_error or report is None:
        return RuleResult("contract_tests_green", False, load_error or "contract_test_report unavailable")
    blockers = _green_test_report_blockers(report, kind="contract_tests")
    return RuleResult(
        "contract_tests_green",
        not blockers,
        None if not blockers else "; ".join(blockers),
    )


def _build_gate_payload(
    frontend: dict[str, Any] | None,
    contract: dict[str, Any] | None,
    postgres: dict[str, Any] | None,
    rules: list[RuleResult],
    paths: dict[str, Path],
) -> dict[str, Any]:
    blockers = [r.blocker for r in rules if not r.passed and r.blocker]
    passed_rules = sum(1 for r in rules if r.passed)
    score = round(passed_rules / RULE_COUNT * 100, 1)
    gate_passed = passed_rules == RULE_COUNT
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "gate": "M3a",
        "gate_result": "PASS" if gate_passed else "FAIL",
        "score": score,
        "rules_passed": passed_rules,
        "rules_total": RULE_COUNT,
        "blockers": blockers,
        "rule_results": [
            {"id": r.id, "passed": r.passed, "blocker": r.blocker} for r in rules
        ],
        "inputs": {key: str(path) for key, path in paths.items()},
        "input_summaries": {
            "frontend_truth": _summary(frontend),
            "contract_tests": _summary(contract),
            "postgres_truth": _summary(postgres),
        },
    }


def _summary(report: dict[str, Any] | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "collected": report.get("collected"),
        "passed": report.get("passed"),
        "failed": report.get("failed"),
        "skipped": report.get("skipped"),
        "errors": report.get("errors"),
        "exit_code": report.get("pytest_exit_code", report.get("exit_code", report.get("playwright_exit_code"))),
        "timestamp": report.get("timestamp") or report.get("generated_at"),
    }


def _write_outputs(payload: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(payload), encoding="utf-8")


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# M3a Gate Result",
        "",
        "| Feld | Wert |",
        "|---|---|",
        f"| Gate Result | {payload['gate_result']} |",
        f"| Score | {payload['score']} |",
        f"| Regeln | {payload['rules_passed']} / {payload['rules_total']} |",
        f"| Timestamp | `{payload['timestamp']}` |",
        "",
        "## Regeln",
        "",
        "| Regel | Status | Blocker |",
        "|---|---|---|",
    ]
    for rule in payload["rule_results"]:
        status = "PASS" if rule["passed"] else "FAIL"
        blocker = rule.get("blocker") or ""
        lines.append(f"| `{rule['id']}` | {status} | {blocker} |")

    lines.extend(["", "## Blocker", ""])
    blockers = payload.get("blockers") or []
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- keine")
    return "\n".join(lines) + "\n"


def _print_result(payload: dict[str, Any]) -> None:
    print(f"Gate Result: {payload['gate_result']}")
    print(f"Score:       {payload['score']}")
    print("Blocker:")
    blockers = payload.get("blockers") or []
    if not blockers:
        print("  - keine")
    else:
        for blocker in blockers:
            print(f"  - {blocker}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the M3a gate from truth reports.")
    parser.add_argument("--frontend-report", type=Path, default=DEFAULT_FRONTEND_REPORT)
    parser.add_argument("--contract-report", type=Path, default=DEFAULT_CONTRACT_REPORT)
    parser.add_argument("--postgres-report", type=Path, default=DEFAULT_POSTGRES_REPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args(argv)

    frontend, frontend_error = _load_json(args.frontend_report)
    contract, contract_error = _load_json(args.contract_report)
    postgres, postgres_error = _load_json(args.postgres_report)

    rules: list[RuleResult] = []
    rules.extend(_frontend_rules(frontend, frontend_error))
    rules.append(_postgres_rule(postgres, postgres_error))
    rules.append(_contract_rule(contract, contract_error))

    # Keep output order aligned with the user-facing rules.
    order = {
        "frontend_truth_passed_equals_collected": 1,
        "frontend_truth_failed_zero": 2,
        "frontend_truth_skipped_zero": 3,
        "postgres_truth_green": 4,
        "contract_tests_green": 5,
        "no_api_unreachable_in_normalflow": 6,
        "no_workspace_not_configured_after_valid_login": 7,
    }
    rules = sorted(rules, key=lambda r: order[r.id])

    payload = _build_gate_payload(
        frontend,
        contract,
        postgres,
        rules,
        {
            "frontend_truth_report": args.frontend_report,
            "contract_test_report": args.contract_report,
            "postgres_truth_report": args.postgres_report,
        },
    )
    _write_outputs(payload, args.output_json, args.output_md)
    _print_result(payload)
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")

    return 0 if payload["gate_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
