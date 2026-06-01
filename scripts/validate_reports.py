from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
CURRENT_DIR = REPORTS_DIR / "current"
ARCHIVE_DIR = REPORTS_DIR / "archive"
SUPPORTED_SCHEMA_VERSION = 1
DEFAULT_MAX_REPORT_AGE_HOURS = 168

REQUIRED_FIELDS = (
    "report_schema_version",
    "report_name",
    "gate",
    "status",
    "timestamp",
    "environment",
    "collected",
    "passed",
    "failed",
    "errors",
    "skipped",
    "exit_code",
    "blockers",
    "source_command",
    "generated_by",
)

CANONICAL_REPORTS = (
    CURRENT_DIR / "m3a_frontend_truth.json",
    CURRENT_DIR / "m3a_release_candidate.json",
    CURRENT_DIR / "m4a_auth_truth.json",
    CURRENT_DIR / "m4b_upload_queue_truth.json",
    CURRENT_DIR / "m4c_lifecycle_retrieval_truth.json",
    CURRENT_DIR / "m4e_backup_restore_truth.json",
    CURRENT_DIR / "m4e_operations_release_report.json",
    CURRENT_DIR / "masterplan_status.json",
)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("report root must be a JSON object")
    return payload


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


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


def _source_policy_issues(
    path: Path,
    report: dict[str, Any],
    *,
    max_report_age_hours: int | None = DEFAULT_MAX_REPORT_AGE_HOURS,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    resolved = path.resolve()
    repo_root = REPO_ROOT.resolve()
    current_dir = CURRENT_DIR.resolve()
    archive_dir = ARCHIVE_DIR.resolve()

    if _is_relative_to(resolved, archive_dir):
        issues.append(ValidationIssue("archive_report_source", "active reports must not be read from reports/archive"))
    elif _is_relative_to(resolved, repo_root) and not _is_relative_to(resolved, current_dir):
        issues.append(ValidationIssue("non_current_report_source", "active reports must be read from reports/current"))

    if max_report_age_hours is not None:
        timestamp = _parse_timestamp(report.get("timestamp") or report.get("generated_at"))
        if timestamp is None:
            issues.append(ValidationIssue("missing_report_timestamp", "report timestamp must be machine-readable"))
        else:
            max_age = timedelta(hours=max_report_age_hours)
            if datetime.now(UTC) - timestamp > max_age:
                issues.append(
                    ValidationIssue(
                        "stale_report_source",
                        f"report timestamp is older than {max_report_age_hours} hours",
                    )
                )

    return issues


def _status_from_counts(failed: int, errors: int, skipped: int, exit_code: int) -> str:
    if failed == 0 and errors == 0 and skipped == 0 and exit_code == 0:
        return "PASS"
    return "FAIL"


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
    value = result.stdout.strip()
    return value or None


def _coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def _report_defaults(path: Path, report: dict[str, Any]) -> dict[str, Any]:
    stem = path.stem
    timestamp = (
        report.get("timestamp")
        or report.get("generated_at")
        or report.get("created_at")
        or "1970-01-01T00:00:00Z"
    )

    if stem == "masterplan_status":
        status = "INFO"
        report_type = "informational"
        gate = "masterplan"
        collected = _coerce_int(report.get("collected"), 1)
        passed = _coerce_int(report.get("passed"), collected)
        failed = _coerce_int(report.get("failed"), 0)
        errors = _coerce_int(report.get("errors"), 0)
        skipped = _coerce_int(report.get("skipped"), 0)
        if passed + failed + errors + skipped != collected:
            collected = passed + failed + errors + skipped
        if collected == 0:
            collected = 1
            passed = 1
        exit_code = _coerce_int(report.get("exit_code"), 0)
    elif stem == "m3a_release_candidate":
        criteria = report.get("criteria") if isinstance(report.get("criteria"), list) else []
        collected = _coerce_int(report.get("collected"), len(criteria))
        passed = _coerce_int(report.get("passed"), sum(1 for item in criteria if isinstance(item, dict) and item.get("passed") is True))
        failed = _coerce_int(report.get("failed"), max(collected - passed, 0))
        errors = _coerce_int(report.get("errors"), 0)
        skipped = _coerce_int(report.get("skipped"), 0)
        collected = passed + failed + errors + skipped
        exit_code = _coerce_int(report.get("exit_code"), 0 if failed == 0 and errors == 0 and skipped == 0 else 1)
        status = _status_from_counts(failed, errors, skipped, exit_code)
        report_type = "release_candidate"
        gate = "m3a"
    else:
        collected = _coerce_int(report.get("collected"), 0)
        passed = _coerce_int(report.get("passed"), 0)
        failed = _coerce_int(report.get("failed"), 0)
        errors = _coerce_int(report.get("errors"), 0)
        skipped = _coerce_int(report.get("skipped"), 0)
        if passed + failed + errors + skipped != collected:
            collected = passed + failed + errors + skipped
        exit_code = _coerce_int(report.get("exit_code"), 0 if failed == 0 and errors == 0 and skipped == 0 else 1)
        status = _status_from_counts(failed, errors, skipped, exit_code)
        report_type = "truth"
        gate = {
            "m3a_frontend_truth": "m3a",
            "m4a_auth_truth": "m4a",
            "m4b_upload_queue_truth": "m4b",
            "m4c_lifecycle_retrieval_truth": "m4c",
            "m4e_backup_restore_truth": "m4e",
        }.get(stem, report.get("gate") or report.get("marker") or stem)

    blockers = report.get("blockers")
    if not isinstance(blockers, list):
        blockers = []
    if status in {"FAIL", "BLOCKED"} and not blockers:
        blockers = [{
            "gate": gate,
            "severity": "critical",
            "reason": f"{failed} failed, {errors} errors, {skipped} skipped",
        }]

    normalized = dict(report)
    normalized.update({
        "report_schema_version": SUPPORTED_SCHEMA_VERSION,
        "report_name": stem,
        "gate": str(gate),
        "status": status,
        "timestamp": str(timestamp),
        "environment": str(report.get("environment") or "local"),
        "report_type": report_type,
        "collected": collected,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "exit_code": exit_code,
        "blockers": blockers,
        "source_command": str(report.get("source_command") or f"reports/current/{path.name}"),
        "generated_by": "gate_validator",
    })
    commit = report.get("commit_hash") or _commit_hash()
    if commit:
        normalized["commit_hash"] = str(commit)
    return normalized


def normalize_report(path: Path) -> dict[str, Any]:
    return _report_defaults(path, _load_json(path))


def validate_payload(report: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    missing = [field for field in REQUIRED_FIELDS if field not in report]
    for field in missing:
        issues.append(ValidationIssue("missing_required_field", f"missing required field: {field}"))

    version = report.get("report_schema_version")
    if version is None:
        issues.append(ValidationIssue("missing_schema_version", "report_schema_version is required"))
    elif version != SUPPORTED_SCHEMA_VERSION:
        issues.append(ValidationIssue("unknown_schema_version", f"unsupported report_schema_version: {version!r}"))

    for field in ("report_name", "gate", "status", "timestamp", "environment", "source_command"):
        if field in report and (not isinstance(report[field], str) or not report[field].strip()):
            issues.append(ValidationIssue("invalid_type", f"{field} must be a non-empty string"))

    if report.get("status") not in {"PASS", "FAIL", "BLOCKED", "INFO"}:
        issues.append(ValidationIssue("invalid_status", f"invalid status: {report.get('status')!r}"))

    generated_by = report.get("generated_by")
    if generated_by is None:
        issues.append(ValidationIssue("missing_generated_by", "generated_by is required"))
    elif generated_by != "gate_validator":
        issues.append(ValidationIssue("invalid_generated_by", "generated_by must be 'gate_validator'"))

    numeric: dict[str, int] = {}
    for field in ("collected", "passed", "failed", "errors", "skipped", "exit_code"):
        value = report.get(field)
        if isinstance(value, bool) or not isinstance(value, int):
            issues.append(ValidationIssue("invalid_number", f"{field} must be an integer"))
            continue
        if field != "exit_code" and value < 0:
            issues.append(ValidationIssue("invalid_number", f"{field} must be >= 0"))
        numeric[field] = value

    if not isinstance(report.get("blockers"), list):
        issues.append(ValidationIssue("invalid_type", "blockers must be a list"))

    report_type = report.get("report_type")
    if report_type is not None and report_type not in {"gate", "truth", "release_candidate", "informational"}:
        issues.append(ValidationIssue("invalid_report_type", f"invalid report_type: {report_type!r}"))

    if {"collected", "passed", "failed", "errors", "skipped"}.issubset(numeric):
        collected = numeric["collected"]
        total = numeric["passed"] + numeric["failed"] + numeric["errors"] + numeric["skipped"]
        blocked_pre_collection = report.get("status") == "BLOCKED" and collected == 0 and numeric["errors"] > 0
        if report_type != "informational" and collected <= 0 and not blocked_pre_collection:
            issues.append(ValidationIssue("empty_collected", "collected must be > 0 unless report_type=informational"))
        if collected != total and not blocked_pre_collection:
            issues.append(ValidationIssue("inconsistent_counts", f"collected ({collected}) must equal passed+failed+errors+skipped ({total})"))
        if report.get("status") == "PASS" and (numeric["failed"] > 0 or numeric["errors"] > 0 or numeric["skipped"] > 0):
            issues.append(ValidationIssue("invalid_pass_status", "status PASS requires failed=0, errors=0, skipped=0"))

    report_name = report.get("report_name")
    if isinstance(report_name, str) and report_name.endswith("final_release") and report.get("generated_by") != "gate_validator":
        issues.append(ValidationIssue("invalid_final_release_source", "final release reports must be generated by gate_validator"))

    return issues


def validate_report(
    path: Path,
    *,
    max_report_age_hours: int | None = DEFAULT_MAX_REPORT_AGE_HOURS,
) -> list[ValidationIssue]:
    payload = _load_json(path)
    return [
        *validate_payload(payload),
        *_source_policy_issues(path, payload, max_report_age_hours=max_report_age_hours),
    ]


def _paths_from_args(values: list[str] | None) -> list[Path]:
    if values:
        return [Path(value) for value in values]
    return list(CANONICAL_REPORTS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate versioned report schema v1.")
    parser.add_argument("--normalize", action="store_true", help="Write schema-v1 required fields into reports before validation.")
    parser.add_argument("--report", nargs="*", help="Report path(s). Defaults to reports/current canonical reports.")
    parser.add_argument(
        "--max-report-age-hours",
        type=int,
        default=DEFAULT_MAX_REPORT_AGE_HOURS,
        help="Reject active reports older than this many hours. Use -1 to disable age validation.",
    )
    args = parser.parse_args(argv)
    max_report_age_hours = None if args.max_report_age_hours < 0 else args.max_report_age_hours

    failed = 0
    for path in _paths_from_args(args.report):
        if not path.exists():
            print(f"FAIL {path}: missing file")
            failed += 1
            continue
        try:
            if args.normalize:
                payload = normalize_report(path)
                path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            issues = validate_report(path, max_report_age_hours=max_report_age_hours)
        except Exception as exc:
            print(f"FAIL {path}: {exc}")
            failed += 1
            continue
        if issues:
            failed += 1
            print(f"FAIL {path}")
            for issue in issues:
                print(f"  - {issue.code}: {issue.message}")
        else:
            print(f"OK   {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
