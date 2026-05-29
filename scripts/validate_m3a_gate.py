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
CURRENT_DIR = REPORTS_DIR / "current"
DEFAULT_FRONTEND_REPORT = CURRENT_DIR / "m3a_frontend_truth.json"
DEFAULT_GUI_TRUTH_LATEST = CURRENT_DIR / "gui_truth_latest.json"
DEFAULT_GUI_CHAOS_REPORT = CURRENT_DIR / "gui_chaos_suite_report.json"
DEFAULT_CONTRACT_REPORT = CURRENT_DIR / "contract_test_report.json"
DEFAULT_POSTGRES_REPORT = CURRENT_DIR / "m4a_auth_truth.json"
DEFAULT_OUTPUT_JSON = CURRENT_DIR / "m3a_gate_result.json"
DEFAULT_OUTPUT_MD = CURRENT_DIR / "m3a_gate_result.md"

RULE_COUNT = 9


@dataclass(frozen=True)
class RuleResult:
    id: str
    passed: bool
    blocker: str | None = None


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    resolved = path.resolve()
    repo_root = REPO_ROOT.resolve()
    current_dir = CURRENT_DIR.resolve()
    archive_dir = (REPORTS_DIR / "archive").resolve()
    try:
        in_repo = resolved.relative_to(repo_root)
    except ValueError:
        in_repo = None
    if in_repo is not None:
        try:
            resolved.relative_to(archive_dir)
            return None, f"archive reports are not valid gate inputs: {path}"
        except ValueError:
            pass
        try:
            resolved.relative_to(current_dir)
        except ValueError:
            return None, f"gate inputs must come from reports/current: {path}"
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
        reason = load_error or "frontend truth report unavailable"
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


def _classify_postgres_truth_nodeid(nodeid: str, *, kind: str = "failure") -> dict[str, str]:
    lowered = nodeid.lower()
    if not nodeid or nodeid.startswith("unclassified_setup_error_"):
        group = "Setup/Error"
        domain = "Report integrity"
        m4_critical = "yes"
        m5_critical = "yes"
        reason = "Setup-/Collect-Error ohne Nodeid im historischen Report"
    elif "test_entropy_truth.py" in lowered or "test_queue_aging_truth.py" in lowered:
        group = "M5 entropy/drift"
        domain = "M5 Operational Truth"
        m4_critical = "no"
        m5_critical = "yes"
        reason = "Entropy, Queue Aging oder Drift gehoeren nicht zum M3a Gate"
    elif any(
        token in lowered
        for token in (
            "test_m5_",
            "cleanup_governance",
            "citation_longevity",
            "reindex_governance",
        )
    ):
        group = "M5 entropy/drift"
        domain = "M5 Operational Truth"
        m4_critical = "no"
        m5_critical = "yes"
        reason = "Operational-Hardening fuer M5, keine M3a-Pflicht"
    elif any(token in lowered for token in ("test_m4a_", "auth_workspace", "workspace_bootstrap")):
        group = "M4a"
        domain = "M4 Backend Truth"
        m4_critical = "yes"
        m5_critical = "no"
        reason = "Auth-/Workspace-Isolation ist M4a-gate-kritisch"
    elif any(
        token in lowered
        for token in (
            "test_m4b_",
            "upload",
            "duplicate",
            "queue",
            "replay",
            "recover_stale_import_job",
            "import_job",
        )
    ):
        group = "M4b"
        domain = "M4 Backend Truth"
        m4_critical = "yes"
        m5_critical = "no"
        reason = "Upload-/Queue-Recovery ist M4b-gate-kritisch"
    elif any(token in lowered for token in ("test_m4c_", "lifecycle", "retrieval", "search", "chat")):
        group = "M4c"
        domain = "M4 Backend Truth"
        m4_critical = "yes"
        m5_critical = "no"
        reason = "Lifecycle/Search/Chat ist M4c-gate-kritisch"
    else:
        group = "Setup/Error"
        domain = "Report integrity"
        m4_critical = "yes"
        m5_critical = "yes"
        reason = "Unbekannter postgres_truth-Scope muss vor Freigabe geklaert werden"

    return {
        "nodeid": nodeid,
        "kind": kind,
        "group": group,
        "domain": domain,
        "m4_critical": m4_critical,
        "m5_critical": m5_critical,
        "m3a_relevant": "no",
        "reason": reason,
    }


def _postgres_failure_gate_matrix(report: dict[str, Any] | None) -> list[dict[str, str]]:
    if report is None:
        return []
    rows = [
        _classify_postgres_truth_nodeid(str(nodeid), kind="failure")
        for nodeid in (report.get("failed_tests") or [])
    ]
    error_tests = [str(nodeid) for nodeid in (report.get("error_tests") or [])]
    rows.extend(_classify_postgres_truth_nodeid(nodeid, kind="error") for nodeid in error_tests)
    error_count = _as_int(report.get("errors"), 0) or 0
    if error_count > len(error_tests):
        for index in range(error_count - len(error_tests)):
            rows.append(
                _classify_postgres_truth_nodeid(
                    f"unclassified_setup_error_{index + 1}",
                    kind="error",
                )
            )
    return rows


def _contract_rule(report: dict[str, Any] | None, load_error: str | None) -> RuleResult:
    if load_error or report is None:
        return RuleResult("contract_tests_green", False, load_error or "contract_test_report unavailable")
    blockers = _green_test_report_blockers(report, kind="contract_tests")
    return RuleResult(
        "contract_tests_green",
        not blockers,
        None if not blockers else "; ".join(blockers),
    )


def _has_passed_flow(report: dict[str, Any] | None, token: str) -> bool:
    if report is None:
        return False
    passed_tests = report.get("passed_tests")
    if not isinstance(passed_tests, list):
        return False
    lowered_token = token.lower()
    return any(lowered_token in str(item).lower() for item in passed_tests)


def _m3a_backend_minimum_rule(
    frontend: dict[str, Any] | None,
    frontend_error: str | None,
    contract: dict[str, Any] | None,
    contract_error: str | None,
) -> RuleResult:
    blockers: list[str] = []

    if frontend_error or frontend is None:
        blockers.append(frontend_error or "frontend truth report unavailable")
    else:
        if frontend.get("real_api") is not True:
            blockers.append("M3a backend minimum requires real_api=true")
        if frontend.get("mock_only") is not False:
            blockers.append("M3a backend minimum requires mock_only=false")
        if frontend.get("test_database_url_set") is not True:
            blockers.append("M3a backend minimum requires TEST_DATABASE_URL proof")
        api_health = frontend.get("api_database_health") or {}
        if not isinstance(api_health, dict) or api_health.get("ok") is not True:
            blockers.append("M3a backend minimum requires healthy /health/db")

        required_flow_tokens = {
            "auth": "Login flow",
            "documents": "Dokumentliste",
            "upload": "Upload flow",
            "search": "Search flow",
            "chat": "Chat flow",
            "diagnostics": "Diagnostics GUI",
        }
        missing = [
            name for name, token in required_flow_tokens.items()
            if not _has_passed_flow(frontend, token)
        ]
        if missing:
            blockers.append("M3a relevant endpoint flows missing in frontend truth: " + ", ".join(missing))

    if contract_error or contract is None:
        blockers.append(contract_error or "contract_test_report unavailable")
    else:
        blockers.extend(_green_test_report_blockers(contract, kind="contract_tests"))

    return RuleResult(
        "m3a_backend_minimum_green",
        not blockers,
        None if not blockers else "; ".join(blockers),
    )


def _frontend_full_suite_rule(
    frontend: dict[str, Any] | None,
    frontend_error: str | None,
    gui_latest: dict[str, Any] | None,
    gui_latest_error: str | None,
) -> RuleResult:
    blockers: list[str] = []
    if frontend_error or frontend is None:
        blockers.append(frontend_error or "frontend truth report unavailable")
    else:
        blockers.extend(_green_test_report_blockers(frontend, kind="frontend_truth"))
        if frontend.get("real_api") is not True:
            blockers.append("frontend_truth real_api must be true")
        if frontend.get("mock_only") is not False:
            blockers.append("frontend_truth mock_only must be false")
        if frontend.get("test_database_url_set") is not True:
            blockers.append("frontend_truth TEST_DATABASE_URL proof missing")
        api_health = frontend.get("api_database_health") or {}
        if not isinstance(api_health, dict) or api_health.get("ok") is not True:
            blockers.append("frontend_truth API database health must be ok")

    if gui_latest_error or gui_latest is None:
        blockers.append(gui_latest_error or "reports/gui_truth/latest.json unavailable")
    elif frontend is not None:
        if gui_latest.get("timestamp") != frontend.get("timestamp"):
            blockers.append("current GUI truth latest timestamp differs from frontend truth report")
        if gui_latest.get("collected") != frontend.get("collected"):
            blockers.append("current GUI truth latest collected differs from frontend truth report")

    return RuleResult(
        "full_suite_frontend_truth_green",
        not blockers,
        None if not blockers else "; ".join(blockers),
    )


def _gui_chaos_rule(report: dict[str, Any] | None, load_error: str | None) -> RuleResult:
    if load_error or report is None:
        return RuleResult("gui_chaos_tests_green", False, load_error or "GUI Chaos report unavailable")

    blockers: list[str] = []
    if report.get("result") != "PASS":
        blockers.append(f"GUI Chaos result must be PASS, got {report.get('result')!r}")
    blockers.extend(_green_test_report_blockers(report, kind="gui_chaos"))
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        blockers.append("GUI Chaos checks must be present")
    else:
        failed_checks = [
            str(check.get("id") or "unknown")
            for check in checks
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        if failed_checks:
            blockers.append("GUI Chaos failed checks: " + ", ".join(failed_checks))

    return RuleResult(
        "gui_chaos_tests_green",
        not blockers,
        None if not blockers else "; ".join(blockers),
    )


def _build_gate_payload(
    frontend: dict[str, Any] | None,
    gui_latest: dict[str, Any] | None,
    gui_chaos: dict[str, Any] | None,
    contract: dict[str, Any] | None,
    postgres: dict[str, Any] | None,
    rules: list[RuleResult],
    paths: dict[str, Path],
) -> dict[str, Any]:
    blockers = [r.blocker for r in rules if not r.passed and r.blocker]
    passed_rules = sum(1 for r in rules if r.passed)
    score = round(passed_rules / RULE_COUNT * 100, 1)
    gate_passed = passed_rules == RULE_COUNT
    postgres_matrix = _postgres_failure_gate_matrix(postgres)
    m4_backend_blockers = [row for row in postgres_matrix if row["m4_critical"] == "yes"]
    m5_operational_blockers = [row for row in postgres_matrix if row["m5_critical"] == "yes"]
    m3a_relevant_blockers = [row for row in postgres_matrix if row["m3a_relevant"] == "yes"]
    return {
        "report_schema_version": 1,
        "report_name": "m3a_gate_result",
        "generated_by": "gate_validator",
        "timestamp": datetime.now(UTC).isoformat(),
        "gate": "M3a",
        "status": "PASS" if gate_passed else "FAIL",
        "environment": "local",
        "collected": RULE_COUNT,
        "passed": passed_rules,
        "failed": RULE_COUNT - passed_rules,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if gate_passed else 1,
        "source_command": "python scripts/validate_m3a_gate.py",
        "gate_result": "PASS" if gate_passed else "FAIL",
        "score": score,
        "decision": "M3a abgeschlossen" if gate_passed else "M3a blockiert",
        "rules_passed": passed_rules,
        "rules_total": RULE_COUNT,
        "blockers": blockers,
        "scope_decision": {
            "frontend_foundation": "blocking",
            "backend_minimum": "blocking_for_m3a",
            "contract_tests": "blocking",
            "gui_chaos": "blocking",
            "postgres_truth": "not_an_m3a_gate_rule",
            "postgres_truth_m4_backend_hardening": "blocking",
            "m5_entropy_queue_drift": "not_an_m3a_gate_rule",
        },
        "truth_domains": {
            "m3a_frontend_truth": [
                "reports/current/m3a_frontend_truth.json",
            ],
            "m4_backend_truth": [
                "reports/current/m4a_auth_truth.json",
                "reports/current/m4b_upload_queue_truth.json",
                "reports/current/m4c_lifecycle_retrieval_truth.json",
                "reports/current/m4e_backup_restore_truth.json",
            ],
            "m5_operational_truth": [
                "entropy, queue aging, drift, cleanup, longevity and operational postgres_truth blocks",
            ],
        },
        "m4_m5_reference": {
            "postgres_truth_considered_for_m3a": False,
            "failure_to_gate_matrix": postgres_matrix,
            "m3a_relevant_blockers": m3a_relevant_blockers,
            "m4_backend_blockers": m4_backend_blockers,
            "m5_operational_blockers": m5_operational_blockers,
        },
        "rule_results": [
            {"id": r.id, "passed": r.passed, "blocker": r.blocker} for r in rules
        ],
        "inputs": {key: str(path) for key, path in paths.items()},
        "input_summaries": {
            "frontend_truth": _summary(frontend),
            "gui_truth_latest": _summary(gui_latest),
            "gui_chaos": _summary(gui_chaos),
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
        f"| Entscheidung | {payload['decision']} |",
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
    lines.extend(["", "## Scope-Entscheidung", ""])
    scope = payload.get("scope_decision") or {}
    lines.append("- M3a Frontend Truth: `reports/current/m3a_frontend_truth.json` ist blockierend.")
    lines.append("- M3a Backend-Minimum: echte API erreichbar, echte DB aktiv, Contract Tests gruen und relevante M3a-Endpunktflows im Frontend Truth belegt.")
    lines.append("- M4 Backend Truth: `postgres_truth_report.json` bewertet Backend-Hardening und ist keine M3a-Gate-Regel.")
    lines.append("- M5 Operational Truth: Entropy-, Queue-Aging-, Drift-, Cleanup- und Longevity-Tests sind keine M3a-Gate-Regeln.")
    lines.extend(["", "## M4/M5 Referenz", ""])
    m4_m5 = payload.get("m4_m5_reference") or {}
    lines.append(f"- `postgres_truth_considered_for_m3a`: `{str(m4_m5.get('postgres_truth_considered_for_m3a')).lower()}`")
    matrix = m4_m5.get("failure_to_gate_matrix") or []
    if matrix:
        lines.extend(
            [
                "",
                "| Failure/Error | Gruppe | M4-kritisch | M5-kritisch | M3a-relevant |",
                "|---|---|---|---|---|",
            ]
        )
        for row in matrix:
            lines.append(
                f"| `{row['nodeid']}` | {row['group']} | {row['m4_critical']} | "
                f"{row['m5_critical']} | {row['m3a_relevant']} |"
            )
    else:
        lines.append("- postgres_truth Findings: keine")
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
    parser.add_argument("--gui-latest-report", type=Path, default=DEFAULT_GUI_TRUTH_LATEST)
    parser.add_argument("--gui-chaos-report", type=Path, default=DEFAULT_GUI_CHAOS_REPORT)
    parser.add_argument("--contract-report", type=Path, default=DEFAULT_CONTRACT_REPORT)
    parser.add_argument("--postgres-report", type=Path, default=DEFAULT_POSTGRES_REPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args(argv)

    frontend, frontend_error = _load_json(args.frontend_report)
    gui_latest, gui_latest_error = _load_json(args.gui_latest_report)
    gui_chaos, gui_chaos_error = _load_json(args.gui_chaos_report)
    contract, contract_error = _load_json(args.contract_report)
    postgres, postgres_error = _load_json(args.postgres_report)

    rules: list[RuleResult] = []
    rules.append(_frontend_full_suite_rule(frontend, frontend_error, gui_latest, gui_latest_error))
    rules.append(_m3a_backend_minimum_rule(frontend, frontend_error, contract, contract_error))
    rules.append(_contract_rule(contract, contract_error))
    rules.append(_gui_chaos_rule(gui_chaos, gui_chaos_error))
    rules.extend(_frontend_rules(frontend, frontend_error))

    # Keep output order aligned with the user-facing rules.
    order = {
        "full_suite_frontend_truth_green": 1,
        "m3a_backend_minimum_green": 2,
        "contract_tests_green": 3,
        "gui_chaos_tests_green": 4,
        "frontend_truth_passed_equals_collected": 5,
        "frontend_truth_failed_zero": 6,
        "frontend_truth_skipped_zero": 7,
        "no_api_unreachable_in_normalflow": 8,
        "no_workspace_not_configured_after_valid_login": 9,
    }
    rules = sorted(rules, key=lambda r: order[r.id])

    payload = _build_gate_payload(
        frontend,
        gui_latest,
        gui_chaos,
        contract,
        postgres,
        rules,
        {
            "frontend_truth_report": args.frontend_report,
            "gui_truth_latest": args.gui_latest_report,
            "gui_chaos_suite_report": args.gui_chaos_report,
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
