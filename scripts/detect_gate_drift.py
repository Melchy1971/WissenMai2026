from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import re
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
CURRENT_DIR = REPORTS_DIR / "current"
ARCHIVE_DIR = REPORTS_DIR / "archive"
DEFAULT_BASELINE = REPORTS_DIR / "gate_drift_baseline.json"
DEFAULT_OUTPUT_JSON = CURRENT_DIR / "gate_drift_report.json"
DEFAULT_OUTPUT_MD = REPORTS_DIR / "gate_drift_report.md"
DEFAULT_TAXONOMY_REPORT = CURRENT_DIR / "truth_marker_taxonomy.json"

DOCS_TO_SCAN = (
    REPO_ROOT / "masterplan.md",
    REPO_ROOT / "docs" / "status.md",
    REPO_ROOT / "docs" / "frontend.md",
    REPO_ROOT / "docs" / "api.md",
    REPO_ROOT / "docs" / "security.md",
    REPO_ROOT / "docs" / "operations.md",
    REPO_ROOT / "docs" / "changelog.md",
    REPO_ROOT / "docs" / "known_limitations.md",
)

GATE_REPORTS = (
    "m3a_frontend_truth.json",
    "m3a_release_candidate.json",
    "m4a_auth_truth.json",
    "m4b_upload_queue_truth.json",
    "m4c_lifecycle_retrieval_truth.json",
    "m4e_backup_restore_truth.json",
    "masterplan_status.json",
)

GATE_MARKERS = (
    "frontend_truth",
    "m3a_truth",
    "m4_truth",
    "m4a_auth_truth",
    "m4b_upload_queue_truth",
    "m4c_lifecycle_retrieval_truth",
    "m4e_backup_restore_truth",
    "m5_truth",
    "governance_truth",
    "chaos_truth",
    "slow_truth",
)

REPORT_REFERENCE_PATTERN = re.compile(r"reports/[A-Za-z0-9_.\-/]+")


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    rule: str
    message: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "rule": self.rule,
            "message": self.message,
            "evidence": self.evidence,
        }


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {path}: {exc}"
    if not isinstance(payload, dict):
        return None, f"JSON root must be object: {path}"
    return payload, None


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _report_dir_policy_findings(report_dir: Path) -> list[Finding]:
    resolved = report_dir.resolve()
    if _is_relative_to(resolved, ARCHIVE_DIR):
        return [
            Finding(
                id="GDD-ARCHIVE-REPORT-SOURCE",
                severity="critical",
                rule="Gate-Validatoren duerfen keine Archive-Reports lesen.",
                message="Report-Quelle liegt unter reports/archive.",
                evidence={"report_dir": _display_path(report_dir)},
            )
        ]
    if resolved == REPO_ROOT.resolve() or (_is_relative_to(resolved, REPORTS_DIR) and resolved != CURRENT_DIR.resolve()):
        return [
            Finding(
                id="GDD-NONCURRENT-REPORT-SOURCE",
                severity="critical",
                rule="Aktive Gate-Reports muessen aus reports/current gelesen werden.",
                message="Report-Quelle ist nicht reports/current.",
                evidence={"report_dir": _display_path(report_dir)},
            )
        ]
    return []


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _score(report: dict[str, Any]) -> float | None:
    collected = _as_int(report.get("collected"))
    passed = _as_int(report.get("passed"))
    if collected is None or passed is None or collected <= 0:
        return None
    return round((passed / collected) * 100, 3)


def _failure_count(report: dict[str, Any]) -> int | None:
    failed = _as_int(report.get("failed"))
    errors = _as_int(report.get("errors"))
    if failed is None or errors is None:
        return None
    return failed + errors


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _snapshot_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": report.get("timestamp") or report.get("generated_at"),
        "collected": report.get("collected"),
        "passed": report.get("passed"),
        "failed": report.get("failed"),
        "errors": report.get("errors"),
        "skipped": report.get("skipped"),
        "exit_code": report.get("exit_code"),
        "score": _score(report),
    }


def build_baseline(report_dir: Path = CURRENT_DIR, taxonomy_path: Path = DEFAULT_TAXONOMY_REPORT) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for report_name in GATE_REPORTS:
        payload, error = _load_json(report_dir / report_name)
        reports[report_name] = {"available": False, "error": error} if error else _snapshot_report(payload or {})

    taxonomy, taxonomy_error = _load_json(taxonomy_path)
    taxonomy_snapshot: dict[str, Any]
    if taxonomy_error:
        taxonomy_snapshot = {"available": False, "error": taxonomy_error}
    else:
        taxonomy_snapshot = {
            "available": True,
            "generated_at": taxonomy.get("generated_at"),
            "collected": taxonomy.get("collected"),
            "marker_counts": taxonomy.get("marker_counts", {}),
            "tests_by_marker": taxonomy.get("tests_by_marker", {}),
        }

    return {
        "version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "reports": reports,
        "taxonomy": taxonomy_snapshot,
    }


def _report_findings(
    *,
    current_reports: dict[str, dict[str, Any] | None],
    report_errors: dict[str, str | None],
    baseline: dict[str, Any] | None,
    now: datetime,
    max_report_age_hours: int,
) -> list[Finding]:
    findings: list[Finding] = []
    baseline_reports = baseline.get("reports", {}) if baseline else {}
    max_age = timedelta(hours=max_report_age_hours)

    for report_name in GATE_REPORTS:
        report = current_reports.get(report_name)
        load_error = report_errors.get(report_name)
        if load_error or report is None:
            findings.append(
                Finding(
                    id="GDD-REPORT-MISSING",
                    severity="critical",
                    rule="Gate nutzt keinen fehlenden oder unlesbaren Report.",
                    message=f"{report_name} ist nicht verfuegbar.",
                    evidence={"report": report_name, "error": load_error},
                )
            )
            continue

        timestamp = _parse_timestamp(report.get("timestamp") or report.get("generated_at"))
        if timestamp is None:
            findings.append(
                Finding(
                    id="GDD-REPORT-TIMESTAMP-MISSING",
                    severity="critical",
                    rule="Gate-Reports brauchen einen maschinenlesbaren Timestamp.",
                    message=f"{report_name} hat keinen gueltigen Timestamp.",
                    evidence={"report": report_name, "timestamp": report.get("timestamp")},
                )
            )
        elif now - timestamp > max_age:
            findings.append(
                Finding(
                    id="GDD-REPORT-STALE",
                    severity="critical",
                    rule="Gate darf keinen veralteten Report nutzen.",
                    message=f"{report_name} ist aelter als {max_report_age_hours} Stunden.",
                    evidence={"report": report_name, "timestamp": timestamp.isoformat(), "now": now.isoformat()},
                )
            )

        baseline_report = baseline_reports.get(report_name)
        if isinstance(baseline_report, dict) and baseline_report.get("available") is not False:
            current_collected = _as_int(report.get("collected"))
            baseline_collected = _as_int(baseline_report.get("collected"))
            if current_collected is not None and baseline_collected is not None and current_collected < baseline_collected:
                findings.append(
                    Finding(
                        id="GDD-REPORT-COLLECTED-REGRESSION",
                        severity="critical",
                        rule="Report darf weniger Tests als die Baseline enthalten.",
                        message=f"{report_name} enthaelt weniger Tests als vorher.",
                        evidence={
                            "report": report_name,
                            "current_collected": current_collected,
                            "baseline_collected": baseline_collected,
                        },
                    )
                )

            current_score = _score(report)
            baseline_score = baseline_report.get("score")
            current_failures = _failure_count(report)
            baseline_failures = _as_int(baseline_report.get("failed"))
            baseline_errors = _as_int(baseline_report.get("errors"))
            if baseline_failures is not None and baseline_errors is not None:
                baseline_failure_total = baseline_failures + baseline_errors
            else:
                baseline_failure_total = None
            if (
                current_score is not None
                and isinstance(baseline_score, (int, float))
                and current_failures is not None
                and baseline_failure_total is not None
                and current_score > float(baseline_score)
                and current_failures > baseline_failure_total
            ):
                findings.append(
                    Finding(
                        id="GDD-SCORE-RISES-WITH-FAILURES",
                        severity="critical",
                        rule="Gate-Score darf nicht steigen, wenn neue Failures/Errors dazukommen.",
                        message=f"{report_name} Score steigt trotz mehr Failures/Errors.",
                        evidence={
                            "report": report_name,
                            "current_score": current_score,
                            "baseline_score": baseline_score,
                            "current_failures_errors": current_failures,
                            "baseline_failures_errors": baseline_failure_total,
                        },
                    )
                )

    return findings


def _taxonomy_findings(taxonomy: dict[str, Any] | None, taxonomy_error: str | None, baseline: dict[str, Any] | None) -> list[Finding]:
    findings: list[Finding] = []
    if taxonomy_error or taxonomy is None:
        return [
            Finding(
                id="GDD-TAXONOMY-MISSING",
                severity="critical",
                rule="Marker-Taxonomie muss vorhanden und lesbar sein.",
                message="Truth Marker Taxonomie ist nicht verfuegbar.",
                evidence={"error": taxonomy_error},
            )
        ]

    taxonomy_markers = set(taxonomy.get("taxonomy", {}).get("gate_markers", []))
    marker_counts = taxonomy.get("marker_counts", {})
    for marker in GATE_MARKERS:
        if marker not in taxonomy_markers or marker not in marker_counts:
            findings.append(
                Finding(
                    id="GDD-MARKER-MISSING",
                    severity="critical",
                    rule="Alle Gate-Marker muessen in der Taxonomie und in marker_counts vorkommen.",
                    message=f"Gate-Marker fehlt in der aktuellen Taxonomie: {marker}",
                    evidence={"marker": marker},
                )
            )

    unclassified = taxonomy.get("unclassified_tests", [])
    ambiguous = taxonomy.get("ambiguous_tests", [])
    if unclassified:
        findings.append(
            Finding(
                id="GDD-UNCLASSIFIED-TESTS",
                severity="critical",
                rule="Neue Tests duerfen nicht unklassifiziert bleiben.",
                message=f"{len(unclassified)} Tests sind unklassifiziert.",
                evidence={"tests": unclassified},
            )
        )
    if ambiguous:
        findings.append(
            Finding(
                id="GDD-AMBIGUOUS-TESTS",
                severity="critical",
                rule="Tests duerfen nicht mehreren Gate-Markern zugeordnet sein.",
                message=f"{len(ambiguous)} Tests sind mehrfach klassifiziert.",
                evidence={"tests": ambiguous},
            )
        )

    baseline_taxonomy = baseline.get("taxonomy", {}) if baseline else {}
    baseline_marker_counts = baseline_taxonomy.get("marker_counts", {}) if isinstance(baseline_taxonomy, dict) else {}
    if isinstance(marker_counts, dict) and isinstance(baseline_marker_counts, dict):
        for marker in GATE_MARKERS:
            current_count = _as_int(marker_counts.get(marker))
            baseline_count = _as_int(baseline_marker_counts.get(marker))
            if current_count is not None and baseline_count is not None and current_count < baseline_count:
                findings.append(
                    Finding(
                        id="GDD-MARKER-COUNT-REGRESSION",
                        severity="critical",
                        rule="Marker darf nicht weniger klassifizierte Tests als die Baseline enthalten.",
                        message=f"{marker} enthaelt weniger klassifizierte Tests als vorher.",
                        evidence={
                            "marker": marker,
                            "current_count": current_count,
                            "baseline_count": baseline_count,
                        },
                    )
                )

    return findings


def _documentation_findings(
    *,
    docs: tuple[Path, ...],
    current_reports: dict[str, dict[str, Any] | None],
    report_errors: dict[str, str | None],
    now: datetime,
    max_report_age_hours: int,
) -> list[Finding]:
    findings: list[Finding] = []
    max_age = timedelta(hours=max_report_age_hours)
    seen: set[tuple[str, int, str]] = set()

    for doc_path in docs:
        if not doc_path.exists():
            continue
        display_doc_path = _display_path(doc_path)
        for line_no, line in enumerate(doc_path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in REPORT_REFERENCE_PATTERN.findall(line):
                report_path = (REPO_ROOT / match).resolve()
                report_name = report_path.name
                key = (display_doc_path, line_no, match)
                if key in seen:
                    continue
                seen.add(key)

                if report_name in current_reports:
                    if match.startswith("reports/archive/"):
                        findings.append(
                            Finding(
                                id="GDD-DOC-REFERENCES-ARCHIVE-REPORT",
                                severity="critical",
                                rule="Dokumentation darf Archive-Reports nicht als aktive Evidenz referenzieren.",
                                message=f"{display_doc_path}:{line_no} referenziert Archive-Report {match}.",
                                evidence={"document": display_doc_path, "line": line_no, "reference": match},
                            )
                        )
                    elif not match.startswith("reports/current/"):
                        findings.append(
                            Finding(
                                id="GDD-DOC-REFERENCES-NONCURRENT-REPORT",
                                severity="critical",
                                rule="Aktive Reportreferenzen muessen auf reports/current zeigen.",
                                message=f"{display_doc_path}:{line_no} referenziert nicht-current Report {match}.",
                                evidence={"document": display_doc_path, "line": line_no, "reference": match},
                            )
                        )
                    report = current_reports[report_name]
                    error = report_errors[report_name]
                    if error or report is None:
                        findings.append(
                            Finding(
                                id="GDD-DOC-REFERENCES-MISSING-REPORT",
                                severity="critical",
                                rule="Dokumentation darf keinen fehlenden Gate-Report referenzieren.",
                                message=f"{display_doc_path}:{line_no} referenziert fehlenden Report {match}.",
                                evidence={"document": display_doc_path, "line": line_no, "reference": match},
                            )
                        )
                        continue
                    timestamp = _parse_timestamp(report.get("timestamp") or report.get("generated_at"))
                    if timestamp is None or now - timestamp > max_age:
                        findings.append(
                            Finding(
                                id="GDD-DOC-REFERENCES-STALE-REPORT",
                                severity="high",
                                rule="Dokumentation darf keinen alten Gate-Report als aktuelle Evidenz referenzieren.",
                                message=f"{display_doc_path}:{line_no} referenziert alten Gate-Report {match}.",
                                evidence={
                                    "document": display_doc_path,
                                    "line": line_no,
                                    "reference": match,
                                    "timestamp": None if timestamp is None else timestamp.isoformat(),
                                },
                            )
                        )

    return findings


def detect_gate_drift(
    *,
    report_dir: Path = CURRENT_DIR,
    taxonomy_path: Path = DEFAULT_TAXONOMY_REPORT,
    baseline_path: Path = DEFAULT_BASELINE,
    docs: tuple[Path, ...] = DOCS_TO_SCAN,
    timestamp: str | None = None,
    max_report_age_hours: int = 168,
) -> dict[str, Any]:
    now = _parse_timestamp(timestamp) if timestamp else datetime.now(UTC)
    if now is None:
        raise ValueError(f"invalid timestamp: {timestamp}")

    baseline, baseline_error = _load_json(baseline_path)
    current_reports: dict[str, dict[str, Any] | None] = {}
    report_errors: dict[str, str | None] = {}
    for report_name in GATE_REPORTS:
        payload, error = _load_json(report_dir / report_name)
        current_reports[report_name] = payload
        report_errors[report_name] = error

    taxonomy, taxonomy_error = _load_json(taxonomy_path)
    findings: list[Finding] = []
    findings.extend(_report_dir_policy_findings(report_dir))
    if baseline_error:
        findings.append(
            Finding(
                id="GDD-BASELINE-MISSING",
                severity="critical",
                rule="Gate Drift Detection braucht eine Baseline.",
                message="Baseline fehlt oder ist unlesbar; Regressionen gegen vorherige Testmengen koennen nicht bewertet werden.",
                evidence={"baseline": str(baseline_path), "error": baseline_error},
            )
        )

    findings.extend(
        _report_findings(
            current_reports=current_reports,
            report_errors=report_errors,
            baseline=baseline,
            now=now,
            max_report_age_hours=max_report_age_hours,
        )
    )
    findings.extend(_taxonomy_findings(taxonomy, taxonomy_error, baseline))
    findings.extend(
        _documentation_findings(
            docs=docs,
            current_reports=current_reports,
            report_errors=report_errors,
            now=now,
            max_report_age_hours=max_report_age_hours,
        )
    )

    serialized_findings = [finding.to_dict() for finding in findings]
    return {
        "version": 1,
        "generated_at": now.isoformat(),
        "result": "FAIL" if serialized_findings else "PASS",
        "fail_rules": [
            "Gate report missing, unreadable, timestamp-less or stale.",
            "Current report collected count below baseline.",
            "Required gate marker missing from taxonomy.",
            "Unclassified or ambiguous tests present.",
            "Gate score rises while failed+error count rises.",
            "Documentation references missing or stale gate report.",
            "Gate report source is outside reports/current.",
            "Baseline missing or unreadable.",
        ],
        "inputs": {
            "report_dir": str(report_dir),
            "taxonomy_report": str(taxonomy_path),
            "baseline": str(baseline_path),
            "max_report_age_hours": max_report_age_hours,
        },
        "reports": {
            report_name: {"available": current_reports[report_name] is not None, "error": report_errors[report_name]}
            for report_name in GATE_REPORTS
        },
        "taxonomy": {
            "available": taxonomy is not None,
            "error": taxonomy_error,
            "collected": None if taxonomy is None else taxonomy.get("collected"),
            "unclassified": None if taxonomy is None else len(taxonomy.get("unclassified_tests", [])),
            "ambiguous": None if taxonomy is None else len(taxonomy.get("ambiguous_tests", [])),
        },
        "findings": serialized_findings,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Gate Drift Report",
        "",
        f"- Result: `{payload['result']}`",
        f"- Generated: `{payload['generated_at']}`",
        f"- Baseline: `{payload['inputs']['baseline']}`",
        f"- Max report age hours: `{payload['inputs']['max_report_age_hours']}`",
        "",
        "## Fail-Regeln",
        "",
    ]
    lines.extend(f"- {rule}" for rule in payload["fail_rules"])
    lines.extend(["", "## Findings", ""])
    if not payload["findings"]:
        lines.append("- keine")
    else:
        lines.extend(["| ID | Severity | Rule | Message |", "|---|---|---|---|"])
        for finding in payload["findings"]:
            lines.append(
                f"| `{finding['id']}` | `{finding['severity']}` | {finding['rule']} | {finding['message']} |"
            )
    return "\n".join(lines) + "\n"


def write_report(payload: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect drift in truth gate reports, markers and documentation.")
    parser.add_argument("--report-dir", type=Path, default=CURRENT_DIR)
    parser.add_argument("--taxonomy-report", type=Path, default=DEFAULT_TAXONOMY_REPORT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--max-report-age-hours", type=int, default=168)
    parser.add_argument("--write-baseline", action="store_true", help="Write a baseline snapshot instead of evaluating drift.")
    args = parser.parse_args(argv)

    if args.write_baseline:
        baseline = build_baseline(args.report_dir, args.taxonomy_report)
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote baseline: {args.baseline}")
        return 0

    payload = detect_gate_drift(
        report_dir=args.report_dir,
        taxonomy_path=args.taxonomy_report,
        baseline_path=args.baseline,
        max_report_age_hours=args.max_report_age_hours,
    )
    write_report(payload, args.output_json, args.output_md)
    print(f"Gate Drift = {payload['result']}")
    print(f"Findings: {len(payload['findings'])}")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    return 0 if payload["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
