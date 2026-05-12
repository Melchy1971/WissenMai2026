"""
Retrieval Regression Detection — CLI entry point.

Runs the golden query set against a live PostgreSQL instance, computes
Precision@K, Recall@K, Citation Completeness, and Missing Context Rate,
then compares against a stored baseline.

Usage:
    TEST_DATABASE_URL=postgresql://user:pw@host/db python scripts/run_retrieval_benchmark.py
    ... --set-baseline    Save current run as the new baseline
    ... --no-cleanup      Keep seeded benchmark rows after the run
    ... --trigger REASON  Label the trigger (reindex|restore|cleanup|chunking)

Exit codes:
    0   All thresholds passed, no regression
    1   Configuration error
    2   Threshold violation (absolute metrics below floor)
    3   Regression vs. baseline (>5pp drop in any metric)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

REPORTS_DIR = REPO_ROOT / "reports"
CURRENT_REPORT = REPORTS_DIR / "retrieval_benchmark.json"
BASELINE_REPORT = REPORTS_DIR / "retrieval_benchmark_baseline.json"
MARKDOWN_REPORT = REPORTS_DIR / "retrieval_benchmark.md"

from tests.retrieval_benchmark.corpus import REGRESSION_DELTA, REGRESSION_THRESHOLDS


def _load_baseline() -> dict | None:
    if not BASELINE_REPORT.exists():
        return None
    try:
        return json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _detect_regression(current: dict, baseline: dict) -> list[str]:
    issues: list[str] = []
    for metric in ("precision_at_k", "recall_at_k", "citation_completeness"):
        cur = current.get(metric, 0.0)
        base = baseline.get(metric, 0.0)
        drop = base - cur
        if drop > REGRESSION_DELTA:
            issues.append(
                f"{metric}: {base:.1%} → {cur:.1%} "
                f"(drop {drop:.1%} > tolerance {REGRESSION_DELTA:.0%})"
            )
    cur_mcr = current.get("missing_context_rate", 0.0)
    base_mcr = baseline.get("missing_context_rate", 0.0)
    rise = cur_mcr - base_mcr
    if rise > REGRESSION_DELTA:
        issues.append(
            f"missing_context_rate: {base_mcr:.1%} → {cur_mcr:.1%} "
            f"(rise {rise:.1%} > tolerance {REGRESSION_DELTA:.0%})"
        )
    return issues


def _check_thresholds(current: dict) -> list[str]:
    violations: list[str] = []
    for metric, floor in REGRESSION_THRESHOLDS.items():
        if metric == "missing_context_rate_max":
            val = current.get("missing_context_rate", 0.0)
            if val > floor:
                violations.append(
                    f"missing_context_rate {val:.1%} > ceiling {floor:.1%}"
                )
        else:
            val = current.get(metric, 0.0)
            if val < floor:
                violations.append(f"{metric} {val:.1%} < floor {floor:.1%}")
    return violations


def _serialize(obj) -> object:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


def _render_markdown(
    report: dict,
    trigger: str,
    regressions: list[str],
    violations: list[str],
) -> str:
    thresholds = REGRESSION_THRESHOLDS
    p = report.get("precision_at_k", 0.0)
    r = report.get("recall_at_k", 0.0)
    cc = report.get("citation_completeness", 0.0)
    mcr = report.get("missing_context_rate", 0.0)

    def _status(val, floor, invert=False) -> str:
        ok = val <= floor if invert else val >= floor
        return "PASS" if ok else "FAIL"

    lines = [
        "# Retrieval Regression Detection Report",
        "",
        f"**Run:** {report.get('run_at', '?')}  ",
        f"**Trigger:** {trigger}  ",
        f"**Database:** `{report.get('database_url_host', '?')}`  ",
        f"**Baseline:** {'yes' if report.get('has_baseline') else 'no (first run)'}",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value | Threshold | Status |",
        "|--------|-------|-----------|--------|",
        f"| Precision@K | {p:.1%} | ≥{thresholds['precision_at_k']:.0%} | {_status(p, thresholds['precision_at_k'])} |",
        f"| Recall@K | {r:.1%} | ≥{thresholds['recall_at_k']:.0%} | {_status(r, thresholds['recall_at_k'])} |",
        f"| Citation Completeness | {cc:.1%} | ≥{thresholds['citation_completeness']:.0%} | {_status(cc, thresholds['citation_completeness'])} |",
        f"| Missing Context Rate | {mcr:.1%} | ≤{thresholds['missing_context_rate_max']:.0%} | {_status(mcr, thresholds['missing_context_rate_max'], invert=True)} |",
        f"| Queries Passed | {report.get('passed_queries', 0)}/{report.get('total_queries', 0)} | — | — |",
        "",
    ]

    if regressions:
        lines += ["## Regressionen vs. Baseline", ""]
        for issue in regressions:
            lines += [f"- {issue}"]
        lines.append("")
    elif report.get("has_baseline"):
        lines += ["## Keine Regression vs. Baseline", ""]

    if violations:
        lines += ["## Threshold-Verletzungen", ""]
        for v in violations:
            lines += [f"- {v}"]
        lines.append("")

    lines += [
        "## Per-Query Ergebnisse",
        "",
        "| ID | Beschreibung | P@K | R@K | Rang 1. Treffer | Fehlend |",
        "|----|-------------|-----|-----|-----------------|---------|",
    ]
    for qr in report.get("query_results", []):
        q = qr.get("query", {})
        missing = ", ".join(qr.get("missing_expected", [])) or "—"
        rank = qr.get("rank_of_first_expected") or "—"
        lines.append(
            f"| {q.get('id','?')} "
            f"| {q.get('description','?')[:45]} "
            f"| {qr.get('precision_at_k', 0):.0%} "
            f"| {qr.get('recall_at_k', 0):.0%} "
            f"| {rank} "
            f"| {missing} |"
        )

    lines += [
        "",
        "## Regression-Schwellenwerte",
        "",
        f"- Maximaler Rückgang vs. Baseline: **{REGRESSION_DELTA:.0%}**",
        f"- Precision@K Floor: **{thresholds['precision_at_k']:.0%}**",
        f"- Recall@K Floor: **{thresholds['recall_at_k']:.0%}**",
        f"- Citation Completeness Floor: **{thresholds['citation_completeness']:.0%}**",
        f"- Missing Context Rate Ceiling: **{thresholds['missing_context_rate_max']:.0%}**",
        "",
        "## Trigger-Integration",
        "",
        "Dieser Report wird automatisch erzeugt nach:",
        "- `POST /api/v1/admin/search/reindex` (Reindex)",
        "- Restore-Operation (Backup-Restore-Skript)",
        "- `scripts/run_retrieval_benchmark.py --trigger cleanup`",
        "- Chunking-Pipeline-Änderungen (CI/CD-Hook)",
        "",
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieval Regression Detection")
    parser.add_argument("--set-baseline", action="store_true",
                        help="Save this run as the new baseline")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Keep seeded benchmark rows after run")
    parser.add_argument("--trigger", default="manual",
                        choices=["manual", "reindex", "restore", "cleanup", "chunking"],
                        help="What triggered this benchmark run")
    args = parser.parse_args()

    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        print("ERROR: TEST_DATABASE_URL is not set.", file=sys.stderr)
        print("Set it to a reachable PostgreSQL URL and retry.", file=sys.stderr)
        return 1

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    from tests.retrieval_benchmark.runner import RetrievalBenchmarkRunner

    runner = RetrievalBenchmarkRunner(database_url)
    from tests.retrieval_benchmark.corpus import GOLDEN_QUERIES
    try:
        print(f"[benchmark] Seeding corpus ({len(GOLDEN_QUERIES)} golden queries)…")
        result = runner.run()
    finally:
        if not args.no_cleanup:
            print("[benchmark] Cleaning up seeded rows…")
            runner.cleanup()

    report_dict = _serialize(result)

    baseline = _load_baseline()
    report_dict["has_baseline"] = baseline is not None
    report_dict["trigger"] = args.trigger

    regressions = _detect_regression(report_dict, baseline) if baseline else []
    violations = _check_thresholds(report_dict)

    CURRENT_REPORT.write_text(
        json.dumps(report_dict, indent=2, default=str), encoding="utf-8"
    )
    MARKDOWN_REPORT.write_text(
        _render_markdown(report_dict, args.trigger, regressions, violations),
        encoding="utf-8",
    )

    if args.set_baseline or not baseline:
        BASELINE_REPORT.write_text(
            json.dumps(report_dict, indent=2, default=str), encoding="utf-8"
        )
        action = "updated" if baseline else "created"
        print(f"[benchmark] Baseline {action}: {BASELINE_REPORT}")

    print()
    print(f"  Precision@K:           {result.precision_at_k:.1%}")
    print(f"  Recall@K:              {result.recall_at_k:.1%}")
    print(f"  Citation Completeness: {result.citation_completeness:.1%}")
    print(f"  Missing Context Rate:  {result.missing_context_rate:.1%}")
    print(f"  Queries Passed:        {result.passed_queries}/{result.total_queries}")
    print(f"  Report:                {CURRENT_REPORT}")
    print(f"  Report (MD):           {MARKDOWN_REPORT}")

    if regressions:
        print("\nREGRESSIONS DETECTED:")
        for issue in regressions:
            print(f"  ! {issue}")

    if violations:
        print("\nTHRESHOLD VIOLATIONS:")
        for v in violations:
            print(f"  x {v}")
        return 2

    if regressions:
        return 3

    print("\n  All thresholds passed. No regression detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
