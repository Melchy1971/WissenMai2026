from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = REPO_ROOT / "reports" / "current" / "m3a_frontend_truth.json"
DEFAULT_TEST_RESULTS = REPO_ROOT / "frontend" / "test-results"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "current" / "frontend_failure_clusters.json"

CLUSTERS = (
    "Setup Failure",
    "Selector Failure",
    "Auth Failure",
    "Workspace Failure",
    "API Failure",
    "Routing Failure",
    "Timeout Failure",
    "Test Data Missing",
)

KEYWORDS: dict[str, tuple[str, ...]] = {
    "Setup Failure": (
        "webserver",
        "playwright output not parseable",
        "cannot find module",
        "syntaxerror",
        "npm err",
        "process exited during startup",
        "fixture",
        "beforeall",
        "global timeout",
    ),
    "Selector Failure": (
        "locator",
        "getbyrole",
        "getbytestid",
        "tobevisible",
        "element(s) not found",
        "strict mode violation",
        "waiting for selector",
        "not attached",
    ),
    "Auth Failure": (
        "auth",
        "/auth/me",
        "/auth/login",
        "login",
        "token",
        "session",
        "forbidden",
        "unauthenticated",
        "anmeldung",
        "401",
        "403",
    ),
    "Workspace Failure": (
        "workspace",
        "membership",
        "active_workspace",
        "active workspace",
        "workspace_not_configured",
        "workspace switch",
        "shell",
    ),
    "API Failure": (
        "api_unreachable",
        "network_error",
        "net::",
        "econnrefused",
        "failed to fetch",
        "fetch",
        "http 500",
        "status 500",
        "status_code",
        "/api/",
        "/health/db",
    ),
    "Routing Failure": (
        "redirect",
        "route",
        "routing",
        "page.goto",
        "/documents",
        "/login",
        "/chat",
        "root path",
    ),
    "Timeout Failure": (
        "timeouterror",
        "timeout",
        "timedout",
        "waitforselector",
        "waitforfunction",
        "waitforloadstate",
    ),
    "Test Data Missing": (
        "seed",
        "seeded",
        "truth_",
        "test_database_url_set\": false",
        "missing",
        "no documents",
        "active document",
        "not found",
    ),
}

PRIORITY = {
    "Setup Failure": 0,
    "API Failure": 1,
    "Auth Failure": 2,
    "Workspace Failure": 3,
    "Routing Failure": 4,
    "Test Data Missing": 5,
    "Selector Failure": 6,
    "Timeout Failure": 7,
}


def _strip_ansi(value: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", value)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _commit_hash() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


def _display_path(path: Path) -> str:
    resolved = path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _walk_playwright_suites(suite: dict[str, Any], failures: list[dict[str, Any]], prefix: str = "") -> None:
    title = suite.get("title") or ""
    next_prefix = f"{prefix} > {title}" if prefix and title else title or prefix
    for spec in suite.get("specs", []):
        spec_title = spec.get("title") or ""
        base_name = f"{next_prefix} > {spec_title}" if next_prefix else spec_title
        for test in spec.get("tests", []):
            status = test.get("status")
            if status in {"expected", "passed", "skipped"}:
                continue
            messages: list[str] = []
            attachments: list[str] = []
            for result in test.get("results", []):
                for error in result.get("errors", []):
                    if isinstance(error, dict):
                        messages.append(str(error.get("message") or error.get("stack") or ""))
                for attachment in result.get("attachments", []):
                    if isinstance(attachment, dict) and attachment.get("path"):
                        attachments.append(str(attachment["path"]))
            failures.append({
                "name": base_name,
                "error": _strip_ansi(" ".join(messages)).strip(),
                "attachments": attachments,
                "source": "playwright_json",
            })
    for child in suite.get("suites", []):
        if isinstance(child, dict):
            _walk_playwright_suites(child, failures, next_prefix)


def extract_failures(report: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    raw_failures = report.get("failed_tests") or report.get("failed_flows")
    if isinstance(raw_failures, list):
        for item in raw_failures:
            if isinstance(item, dict):
                failures.append({
                    "name": str(item.get("name") or "unknown"),
                    "error": _strip_ansi(str(item.get("error") or "")),
                    "attachments": item.get("attachments") if isinstance(item.get("attachments"), list) else [],
                    "source": "frontend_truth_report",
                })
            elif isinstance(item, str):
                failures.append({
                    "name": item,
                    "error": "",
                    "attachments": [],
                    "source": "frontend_truth_report",
                })

    for suite in report.get("suites", []):
        if isinstance(suite, dict):
            _walk_playwright_suites(suite, failures)

    return failures


def collect_test_artifacts(test_results_dir: Path) -> dict[str, Any]:
    artifacts = {
        "root": _display_path(test_results_dir) if test_results_dir.exists() else str(test_results_dir),
        "exists": test_results_dir.exists(),
        "screenshots": [],
        "traces": [],
        "videos": [],
        "error_contexts": [],
        "other": [],
    }
    if not test_results_dir.exists():
        return artifacts

    for path in test_results_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = _display_path(path)
        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg"}:
            artifacts["screenshots"].append(rel)
        elif suffix == ".zip" and "trace" in path.name.lower():
            artifacts["traces"].append(rel)
        elif suffix in {".webm", ".mp4"}:
            artifacts["videos"].append(rel)
        elif path.name == "error-context.md":
            artifacts["error_contexts"].append({
                "path": rel,
                "text": path.read_text(encoding="utf-8", errors="replace")[:8000],
            })
        else:
            artifacts["other"].append(rel)

    return artifacts


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _context_for_failure(failure_name: str, artifacts: dict[str, Any]) -> tuple[str, str | None]:
    name_tokens = set(_norm(failure_name).split())
    best_score = 0
    best_text = ""
    best_path: str | None = None
    for item in artifacts.get("error_contexts", []):
        text = str(item.get("text") or "")
        path = str(item.get("path") or "")
        haystack = _norm(f"{path} {text}")
        score = sum(1 for token in name_tokens if len(token) > 2 and token in haystack)
        if score > best_score:
            best_score = score
            best_text = text
            best_path = path
    return best_text if best_score >= 3 else "", best_path if best_score >= 3 else None


def collect_runtime_errors(report: dict[str, Any]) -> dict[str, list[Any]]:
    result: dict[str, list[Any]] = {"console_errors": [], "network_errors": []}

    def walk(value: Any, key_path: str = "") -> None:
        if isinstance(value, dict):
            lowered_keys = " ".join(str(k).lower() for k in value)
            if "console" in lowered_keys or "level" in value:
                level = str(value.get("level") or value.get("type") or "").lower()
                text = str(value.get("text") or value.get("message") or value)
                if level in {"error", "warning"} or "error" in text.lower():
                    result["console_errors"].append(value)
            status = value.get("status") or value.get("status_code")
            if isinstance(status, int) and status >= 400:
                result["network_errors"].append(value)
            if any(token in lowered_keys for token in ("network", "request", "response")):
                text = json.dumps(value, default=str)[:2000].lower()
                if any(token in text for token in ("failed", "error", "econnrefused", "net::", "timeout")):
                    result["network_errors"].append(value)
            for key, child in value.items():
                walk(child, f"{key_path}.{key}" if key_path else str(key))
        elif isinstance(value, list):
            for child in value:
                walk(child, key_path)

    walk(report)
    return result


def classify_failure(failure: dict[str, Any], context: str = "") -> tuple[str, dict[str, int], list[str]]:
    text = _norm(f"{failure.get('name', '')} {failure.get('error', '')} {context}")
    scores: dict[str, int] = {}
    signals: list[str] = []
    for cluster, keywords in KEYWORDS.items():
        score = 0
        for keyword in keywords:
            normalized = _norm(keyword)
            if normalized and normalized in text:
                score += 2 if cluster in {"Setup Failure", "API Failure", "Auth Failure", "Workspace Failure"} else 1
                signals.append(f"{cluster}:{keyword}")
        if score:
            scores[cluster] = score

    if not scores:
        return "Setup Failure", {}, ["unclassified"]

    max_score = max(scores.values())
    candidates = [cluster for cluster, score in scores.items() if score == max_score]
    primary = sorted(candidates, key=lambda cluster: PRIORITY[cluster])[0]
    return primary, scores, sorted(set(signals))


def _root_cause_text(cluster: str) -> str:
    return {
        "Setup Failure": "Truth run setup or Playwright runner did not produce stable browser evidence.",
        "Selector Failure": "Expected UI contract is not visible; selector may be stale or the page renders a different state.",
        "Auth Failure": "Auth bootstrap, session state, login redirect, or auth error handling blocks protected screens.",
        "Workspace Failure": "Workspace membership or active workspace bootstrap prevents AppShell/documents readiness.",
        "API Failure": "Frontend observed API, health, fetch, or HTTP failure evidence.",
        "Routing Failure": "Route guard or redirect behavior does not land on the expected page.",
        "Timeout Failure": "Tests wait until timeout, usually as a cascade after an earlier state transition failure.",
        "Test Data Missing": "Seeded truth data or expected test fixture state is missing or not visible.",
    }[cluster]


def build_cluster_report(
    report: dict[str, Any],
    *,
    report_path: Path,
    test_results_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    failures = extract_failures(report)
    artifacts = collect_test_artifacts(test_results_dir)
    runtime_errors = collect_runtime_errors(report)

    clusters: dict[str, dict[str, Any]] = {
        cluster: {"count": 0, "failures": [], "signals": Counter()}
        for cluster in CLUSTERS
    }

    for failure in failures:
        context, context_path = _context_for_failure(str(failure.get("name") or ""), artifacts)
        primary, scores, signals = classify_failure(failure, context)
        entry = {
            "name": failure.get("name"),
            "error_excerpt": str(failure.get("error") or context)[:700],
            "source": failure.get("source"),
            "context_path": context_path,
            "scores": scores,
            "signals": signals[:12],
        }
        clusters[primary]["count"] += 1
        clusters[primary]["failures"].append(entry)
        clusters[primary]["signals"].update(signals)

    cluster_summary: dict[str, Any] = {}
    for cluster, payload in clusters.items():
        signal_counter: Counter = payload.pop("signals")
        cluster_summary[cluster] = {
            **payload,
            "root_cause_hint": _root_cause_text(cluster),
            "top_signals": [
                {"signal": signal, "count": count}
                for signal, count in signal_counter.most_common(8)
            ],
        }

    ranked_clusters = sorted(
        ({"cluster": cluster, **payload} for cluster, payload in cluster_summary.items()),
        key=lambda item: (-int(item["count"]), PRIORITY[str(item["cluster"])]),
    )
    top_root_causes = [
        {
            "rank": index + 1,
            "cluster": item["cluster"],
            "count": item["count"],
            "root_cause": item["root_cause_hint"],
            "evidence": item["failures"][0]["error_excerpt"] if item["failures"] else "",
        }
        for index, item in enumerate([item for item in ranked_clusters if item["count"]][:5])
    ]

    fix_order = [
        {
            "rank": index + 1,
            "cluster": item["cluster"],
            "why_first": _fix_reason(str(item["cluster"])),
            "affected_failures": item["count"],
        }
        for index, item in enumerate(sorted(
            [item for item in ranked_clusters if item["count"]],
            key=lambda item: (PRIORITY[str(item["cluster"])], -int(item["count"])),
        ))
    ]

    collected = len(failures)
    report_payload: dict[str, Any] = {
        "report_schema_version": 1,
        "report_name": output_path.stem,
        "gate": "m3a",
        "status": "INFO",
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": str(report.get("environment") or "local"),
        "report_type": "informational",
        "collected": collected,
        "passed": collected,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0,
        "blockers": [],
        "source_command": f"python scripts/cluster_frontend_failures.py --report {_display_path(report_path)}",
        "generated_by": "gate_validator",
        "commit_hash": _commit_hash(),
        "input": {
            "playwright_json_report": _display_path(report_path),
            "test_results_dir": _display_path(test_results_dir) if test_results_dir.exists() else str(test_results_dir),
            "screenshots": artifacts["screenshots"],
            "traces": artifacts["traces"],
            "videos": artifacts["videos"],
            "error_context_count": len(artifacts["error_contexts"]),
            "console_error_count": len(runtime_errors["console_errors"]),
            "network_error_count": len(runtime_errors["network_errors"]),
        },
        "cluster_order": list(CLUSTERS),
        "clusters": cluster_summary,
        "top_root_causes": top_root_causes,
        "fix_order": fix_order,
        "runtime_errors": runtime_errors,
    }
    return report_payload


def _fix_reason(cluster: str) -> str:
    return {
        "Setup Failure": "Fix runner/config first; later clusters may be false positives without stable execution.",
        "API Failure": "Restore API reachability before debugging UI state that depends on backend responses.",
        "Auth Failure": "Auth bootstrap gates every protected screen and causes broad cascades.",
        "Workspace Failure": "Workspace readiness gates AppShell, documents, upload, search, and chat flows.",
        "Routing Failure": "Route guards decide whether the expected screen can render at all.",
        "Test Data Missing": "Seed data must exist before document/search/upload expectations are meaningful.",
        "Selector Failure": "Update selectors after state and route behavior are stable.",
        "Timeout Failure": "Resolve remaining waits after primary state and selector failures are removed.",
    }[cluster]


def write_report(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cluster Frontend Truth failures from Playwright evidence.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Playwright or frontend truth JSON report.")
    parser.add_argument("--test-results", type=Path, default=DEFAULT_TEST_RESULTS, help="Playwright test-results directory.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Cluster JSON output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = args.report if args.report.is_absolute() else REPO_ROOT / args.report
    test_results_dir = args.test_results if args.test_results.is_absolute() else REPO_ROOT / args.test_results
    output_path = args.output if args.output.is_absolute() else REPO_ROOT / args.output

    report = _load_json(report_path)
    payload = build_cluster_report(
        report,
        report_path=report_path,
        test_results_dir=test_results_dir,
        output_path=output_path,
    )
    write_report(payload, output_path)

    print(f"Frontend failure clusters written: {_display_path(output_path)}")
    print("Top 5 Root Causes:")
    for item in payload["top_root_causes"]:
        print(f"{item['rank']}. {item['cluster']} ({item['count']}): {item['root_cause']}")
    print("Fix-Reihenfolge:")
    for item in payload["fix_order"]:
        print(f"{item['rank']}. {item['cluster']} ({item['affected_failures']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
