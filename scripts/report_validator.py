from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from report_schema_registry import ReportSchema, get_schema, match_schema  # noqa: E402


@dataclass(frozen=True)
class ReportValidationIssue:
    code: str
    field: str | None
    message: str


@dataclass(frozen=True)
class ReportValidationResult:
    valid: bool
    schema_name: str | None
    issues: tuple[ReportValidationIssue, ...]

    def codes(self) -> set[str]:
        return {issue.code for issue in self.issues}


def validate_payload(
    payload: dict[str, Any],
    *,
    schema_name: str | None = None,
) -> ReportValidationResult:
    schema = _resolve_schema(payload, schema_name)
    issues: list[ReportValidationIssue] = []

    if schema is None:
        issues.append(ReportValidationIssue(
            "schema_match_failed",
            None,
            "report payload does not match a registered schema",
        ))
        return ReportValidationResult(False, None, tuple(issues))

    issues.extend(_missing_field_issues(payload, schema))
    issues.extend(_unknown_field_issues(payload, schema))
    issues.extend(_type_issues(payload, schema))
    issues.extend(_status_issues(payload, schema))
    issues.extend(_timestamp_issues(payload))

    return ReportValidationResult(not issues, schema.name, tuple(issues))


def validate_report(
    path: Path,
    *,
    schema_name: str | None = None,
) -> ReportValidationResult:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ReportValidationResult(
            False,
            schema_name,
            (ReportValidationIssue("invalid_json", None, f"invalid JSON: {exc}"),),
        )

    if not isinstance(payload, dict):
        return ReportValidationResult(
            False,
            schema_name,
            (ReportValidationIssue("invalid_root", None, "report root must be a JSON object"),),
        )
    return validate_payload(payload, schema_name=schema_name)


def _resolve_schema(payload: dict[str, Any], schema_name: str | None) -> ReportSchema | None:
    if schema_name is not None:
        try:
            return get_schema(schema_name)
        except KeyError:
            return None
    return match_schema(payload)


def _missing_field_issues(
    payload: dict[str, Any],
    schema: ReportSchema,
) -> list[ReportValidationIssue]:
    return [
        ReportValidationIssue(
            "missing_field",
            field,
            f"missing required field: {field}",
        )
        for field in schema.required_fields
        if field not in payload
    ]


def _unknown_field_issues(
    payload: dict[str, Any],
    schema: ReportSchema,
) -> list[ReportValidationIssue]:
    return [
        ReportValidationIssue(
            "unknown_field",
            field,
            f"unknown field for {schema.name}: {field}",
        )
        for field in sorted(payload)
        if field not in schema.allowed_fields
    ]


def _type_issues(
    payload: dict[str, Any],
    schema: ReportSchema,
) -> list[ReportValidationIssue]:
    issues: list[ReportValidationIssue] = []
    for field, expected_types in schema.field_types.items():
        if field not in payload:
            continue
        value = payload[field]
        if _matches_type(value, expected_types):
            continue
        expected = " or ".join(schema.type_names(field))
        issues.append(ReportValidationIssue(
            "invalid_type",
            field,
            f"{field} must be {expected}",
        ))
    return issues


def _status_issues(
    payload: dict[str, Any],
    schema: ReportSchema,
) -> list[ReportValidationIssue]:
    status = payload.get("status")
    if not isinstance(status, str):
        return []
    normalized_statuses = {value.upper().replace("-", "_") for value in schema.status_values}
    if status.upper().replace("-", "_") in normalized_statuses:
        return []
    return [ReportValidationIssue(
        "invalid_status",
        "status",
        f"status must be one of {sorted(schema.status_values)}",
    )]


def _timestamp_issues(payload: dict[str, Any]) -> list[ReportValidationIssue]:
    value = payload.get("timestamp")
    if not isinstance(value, str):
        return []
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return [ReportValidationIssue(
            "invalid_timestamp",
            "timestamp",
            "timestamp must be machine-readable ISO 8601",
        )]
    return []


def _matches_type(value: Any, expected_types: tuple[type, ...]) -> bool:
    if bool not in expected_types and isinstance(value, bool):
        return False
    return isinstance(value, expected_types)


def _format_issue(issue: ReportValidationIssue) -> str:
    field = f"{issue.field}: " if issue.field else ""
    return f"{issue.code}: {field}{issue.message}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate reports against the report schema registry.")
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--schema", choices=("gate_report", "supporting_report", "diagnostic_report", "status_report"))
    args = parser.parse_args(argv)

    failed = 0
    for path in args.reports:
        result = validate_report(path, schema_name=args.schema)
        if result.valid:
            print(f"OK   {path} ({result.schema_name})")
            continue
        failed += 1
        print(f"FAIL {path} ({result.schema_name or 'no_schema'})")
        for issue in result.issues:
            print(f"  - {_format_issue(issue)}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
