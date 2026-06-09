from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = REPO_ROOT / "config" / "known_limitations_schema.json"
DEFAULT_REPORT = REPO_ROOT / "reports" / "current" / "known_limitations.json"


@dataclass(frozen=True)
class KnownLimitationsIssue:
    code: str
    field: str | None
    message: str


@dataclass(frozen=True)
class KnownLimitationsValidationResult:
    valid: bool
    issues: tuple[KnownLimitationsIssue, ...]

    def codes(self) -> set[str]:
        return {issue.code for issue in self.issues}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_file(
    report_path: Path = DEFAULT_REPORT,
    *,
    schema_path: Path = DEFAULT_SCHEMA,
    repo_root: Path = REPO_ROOT,
) -> KnownLimitationsValidationResult:
    try:
        payload = load_json(report_path)
    except (OSError, json.JSONDecodeError) as exc:
        return KnownLimitationsValidationResult(
            False,
            (KnownLimitationsIssue("invalid_json", None, f"invalid JSON: {exc}"),),
        )
    try:
        schema = load_json(schema_path)
    except (OSError, json.JSONDecodeError) as exc:
        return KnownLimitationsValidationResult(
            False,
            (KnownLimitationsIssue("invalid_schema", None, f"invalid schema: {exc}"),),
        )
    return validate_payload(payload, schema, repo_root=repo_root)


def validate_payload(
    payload: Any,
    schema: dict[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> KnownLimitationsValidationResult:
    issues: list[KnownLimitationsIssue] = []
    if not isinstance(payload, dict):
        return KnownLimitationsValidationResult(
            False,
            (KnownLimitationsIssue("invalid_root", None, "known limitations root must be an object"),),
        )

    root_schema = schema.get("root", {})
    limitation_schema = schema.get("limitation", {})
    issues.extend(_object_issues(payload, root_schema, prefix=None))
    issues.extend(_root_status_issues(payload, root_schema))
    issues.extend(_timestamp_issues(payload))

    limitations = payload.get("limitations")
    if not isinstance(limitations, list):
        issues.append(KnownLimitationsIssue(
            "invalid_type",
            "limitations",
            "limitations must be an array",
        ))
        return KnownLimitationsValidationResult(False, tuple(issues))

    seen_ids: set[str] = set()
    for index, item in enumerate(limitations):
        prefix = f"limitations[{index}]"
        if not isinstance(item, dict):
            issues.append(KnownLimitationsIssue(
                "invalid_type",
                prefix,
                "limitation must be an object",
            ))
            continue
        issues.extend(_object_issues(item, limitation_schema, prefix=prefix))
        issues.extend(_limitation_value_issues(item, limitation_schema, prefix, repo_root))
        item_id = item.get("id")
        if isinstance(item_id, str):
            if item_id in seen_ids:
                issues.append(KnownLimitationsIssue(
                    "duplicate_id",
                    f"{prefix}.id",
                    f"duplicate limitation id: {item_id}",
                ))
            seen_ids.add(item_id)

    issues.extend(_counter_issues(payload))
    return KnownLimitationsValidationResult(not issues, tuple(issues))


def _object_issues(
    value: dict[str, Any],
    schema: dict[str, Any],
    *,
    prefix: str | None,
) -> list[KnownLimitationsIssue]:
    issues: list[KnownLimitationsIssue] = []
    required = tuple(schema.get("required", ()))
    allowed = set(schema.get("allowed", ()))
    types = schema.get("types", {})

    for field in required:
        if field not in value:
            issues.append(KnownLimitationsIssue(
                "missing_field",
                _field(prefix, field),
                f"missing required field: {field}",
            ))

    for field in sorted(value):
        if field not in allowed:
            issues.append(KnownLimitationsIssue(
                "unknown_field",
                _field(prefix, field),
                f"unknown field: {field}",
            ))

    for field, type_name in types.items():
        if field not in value:
            continue
        if not _matches_type(value[field], str(type_name)):
            issues.append(KnownLimitationsIssue(
                "invalid_type",
                _field(prefix, field),
                f"{field} must be {type_name}",
            ))

    return issues


def _root_status_issues(payload: dict[str, Any], schema: dict[str, Any]) -> list[KnownLimitationsIssue]:
    status = payload.get("status")
    allowed = set(schema.get("status_values", ()))
    if isinstance(status, str) and status in allowed:
        return []
    if status is None:
        return []
    return [KnownLimitationsIssue(
        "invalid_status",
        "status",
        f"status must be one of {sorted(allowed)}",
    )]


def _timestamp_issues(payload: dict[str, Any]) -> list[KnownLimitationsIssue]:
    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, str):
        return []
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return [KnownLimitationsIssue(
            "invalid_timestamp",
            "timestamp",
            "timestamp must be ISO 8601",
        )]
    return []


def _limitation_value_issues(
    item: dict[str, Any],
    schema: dict[str, Any],
    prefix: str,
    repo_root: Path,
) -> list[KnownLimitationsIssue]:
    issues: list[KnownLimitationsIssue] = []
    status = item.get("status")
    if isinstance(status, str) and status not in set(schema.get("status_values", ())):
        issues.append(KnownLimitationsIssue(
            "invalid_status",
            f"{prefix}.status",
            f"status must be one of {sorted(schema.get('status_values', ())) }",
        ))

    severity = item.get("severity")
    if isinstance(severity, str) and severity not in set(schema.get("severity_values", ())):
        issues.append(KnownLimitationsIssue(
            "invalid_severity",
            f"{prefix}.severity",
            f"severity must be one of {sorted(schema.get('severity_values', ())) }",
        ))

    for field in ("id", "title", "owner", "evidence_report", "next_action"):
        value = item.get(field)
        if isinstance(value, str) and not value.strip():
            issues.append(KnownLimitationsIssue(
                "empty_field",
                f"{prefix}.{field}",
                f"{field} must not be empty",
            ))

    evidence = item.get("evidence_report")
    if isinstance(evidence, str) and evidence.strip() and not _evidence_exists(evidence, repo_root):
        issues.append(KnownLimitationsIssue(
            "missing_evidence_report",
            f"{prefix}.evidence_report",
            f"evidence_report does not exist: {evidence}",
        ))

    return issues


def _counter_issues(payload: dict[str, Any]) -> list[KnownLimitationsIssue]:
    limitations = payload.get("limitations")
    if not isinstance(limitations, list):
        return []
    expected = {
        "collected": len(limitations),
        "open": _count_status(limitations, "open"),
        "deferred": _count_status(limitations, "deferred"),
        "blocking": sum(
            1 for item in limitations
            if isinstance(item, dict) and bool(item.get("blocks_gate"))
        ),
        "non_blocking": sum(
            1 for item in limitations
            if isinstance(item, dict) and not bool(item.get("blocks_gate"))
        ),
    }
    issues: list[KnownLimitationsIssue] = []
    for field, value in expected.items():
        if field not in payload:
            continue
        if payload.get(field) != value:
            issues.append(KnownLimitationsIssue(
                "counter_mismatch",
                field,
                f"{field} must be {value}, got {payload.get(field)!r}",
            ))
    return issues


def _count_status(limitations: list[Any], status: str) -> int:
    return sum(
        1 for item in limitations
        if isinstance(item, dict) and item.get("status") == status
    )


def _matches_type(value: Any, type_name: str) -> bool:
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "array:string":
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if type_name == "array:object":
        return isinstance(value, list) and all(isinstance(item, dict) for item in value)
    return False


def _field(prefix: str | None, field: str) -> str:
    return f"{prefix}.{field}" if prefix else field


def _evidence_exists(value: str, repo_root: Path) -> bool:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return True
    return (repo_root / value).exists()


def _format_issue(issue: KnownLimitationsIssue) -> str:
    field = f"{issue.field}: " if issue.field else ""
    return f"{issue.code}: {field}{issue.message}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate known limitations governance.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args(argv)

    result = validate_file(args.report, schema_path=args.schema)
    if result.valid:
        print(f"OK   {args.report}")
        return 0

    print(f"FAIL {args.report}")
    for issue in result.issues:
        print(f"  - {_format_issue(issue)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
