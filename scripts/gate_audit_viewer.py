from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = REPO_ROOT / "reports" / "current"
DEFAULT_OUTPUT = DEFAULT_REPORT_DIR / "gate_audit_log.json"


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "JSON root must be object"
    return payload, None


def build_audit_log(
    report_dir: Path = DEFAULT_REPORT_DIR,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    timestamp = generated_at or _utc_iso()
    entries: list[dict[str, Any]] = []
    invalid_sources: list[dict[str, str]] = []

    for path in sorted(report_dir.glob("*.json")):
        if path.name == "gate_audit_log.json":
            continue
        payload, error = load_json(path)
        source = _relative(path)
        if error or payload is None:
            invalid_sources.append({"source": source, "error": error or "invalid JSON"})
            continue
        entries.extend(_entries_from_payload(payload, source))

    entries.sort(key=lambda item: (str(item.get("timestamp") or ""), str(item.get("gate") or "")))
    status_counts: dict[str, int] = {}
    for entry in entries:
        status = str(entry["decision"].get("status") or "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "report_schema_version": 1,
        "report_name": "gate_audit_log",
        "generated_by": "gate_audit_viewer",
        "timestamp": timestamp,
        "environment": "local",
        "report_type": "diagnostic",
        "status": "PASS" if not invalid_sources else "WARN",
        "result": "PASS" if not invalid_sources else "WARN",
        "source_command": "python scripts\\gate_audit_viewer.py --write",
        "summary": {
            "gate_decisions": len(entries),
            "invalid_sources": len(invalid_sources),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "entries": entries,
        "invalid_sources": invalid_sources,
        "blockers": [],
    }


def write_audit_log(
    output_path: Path = DEFAULT_OUTPUT,
    *,
    report_dir: Path = DEFAULT_REPORT_DIR,
    generated_at: str | None = None,
) -> dict[str, Any]:
    payload = build_audit_log(report_dir, generated_at=generated_at)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def format_table(payload: dict[str, Any]) -> str:
    entries = payload.get("entries", [])
    if not isinstance(entries, list) or not entries:
        return "No gate audit entries."

    rows = ["timestamp | gate | decision | children | blockers | source"]
    rows.append("--- | --- | --- | ---: | ---: | ---")
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        decision = entry.get("decision") if isinstance(entry.get("decision"), dict) else {}
        rows.append(
            " | ".join(
                [
                    str(entry.get("timestamp") or ""),
                    str(entry.get("gate") or ""),
                    str(decision.get("go_no_go") or decision.get("status") or ""),
                    str(len(entry.get("child_gates") or [])),
                    str(len(entry.get("blockers") or [])),
                    str(entry.get("source_report") or ""),
                ]
            )
        )
    return "\n".join(rows)


def _entries_from_payload(payload: dict[str, Any], source: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if _is_gate_decision(payload):
        entries.append(_entry_from_decision(payload, source))

    parent_validation = payload.get("parent_gate_validation")
    if isinstance(parent_validation, dict) and _is_gate_decision(parent_validation):
        entries.append(_entry_from_decision(
            parent_validation,
            f"{source}#parent_gate_validation",
            fallback_sources=_report_sources(payload, source),
        ))
    return entries


def _entry_from_decision(
    payload: dict[str, Any],
    source: str,
    *,
    fallback_sources: list[str] | None = None,
) -> dict[str, Any]:
    trace = payload.get("gate_decision_trace")
    child_gates = _child_gates(payload, trace if isinstance(trace, dict) else None)
    report_sources = _report_sources(payload, source)
    if fallback_sources:
        report_sources.extend(fallback_sources)

    return {
        "timestamp": payload.get("timestamp") or payload.get("generated_at"),
        "gate": _gate_id(payload),
        "decision": _decision(payload),
        "child_gates": child_gates,
        "blockers": _blockers(payload),
        "report_sources": sorted(dict.fromkeys(report_sources)),
        "source_report": source,
    }


def _is_gate_decision(payload: dict[str, Any]) -> bool:
    report_type = str(payload.get("report_type") or "").lower()
    report_name = str(payload.get("report_name") or "")
    return (
        "decision" in payload
        or "parent_gate" in payload
        or "gate_decision_trace" in payload
        or report_type == "gate"
        or report_name.endswith("_gate")
        or report_name == "parent_gate_validation"
    )


def _gate_id(payload: dict[str, Any]) -> str:
    for key in ("gate", "parent_gate", "report_name"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return "unknown_gate"


def _decision(payload: dict[str, Any]) -> dict[str, Any]:
    decision = payload.get("decision")
    decision_payload = dict(decision) if isinstance(decision, dict) else {}
    if isinstance(decision, str):
        decision_payload["value"] = decision
    status = payload.get("status")
    result = payload.get("result")
    if isinstance(status, str):
        decision_payload["status"] = status
    if isinstance(result, str):
        decision_payload["result"] = result
    if "go_no_go" not in decision_payload and isinstance(status, str):
        decision_payload["go_no_go"] = "GO" if status.upper() == "PASS" else "NO_GO"
    return decision_payload


def _child_gates(payload: dict[str, Any], trace: dict[str, Any] | None) -> list[dict[str, Any]]:
    raw_children: Any = None
    if trace is not None:
        raw_children = trace.get("evaluated_children")
    if raw_children is None:
        raw_children = payload.get("child_results")
    if raw_children is None:
        raw_children = payload.get("child_gates")

    if isinstance(raw_children, dict):
        return [
            _normalize_child(child_id, child)
            for child_id, child in raw_children.items()
            if isinstance(child, dict)
        ]
    if isinstance(raw_children, list):
        children: list[dict[str, Any]] = []
        for index, child in enumerate(raw_children):
            if isinstance(child, dict):
                children.append(_normalize_child(str(child.get("child_gate_id") or child.get("child_gate") or index), child))
            elif isinstance(child, str):
                children.append({"child_gate": child})
        return children
    mandatory = payload.get("mandatory_children")
    if isinstance(mandatory, list):
        return [{"child_gate": str(child)} for child in mandatory]
    return []


def _normalize_child(child_id: str, child: dict[str, Any]) -> dict[str, Any]:
    return {
        "child_gate": child.get("child_gate_id") or child.get("child_gate") or child_id,
        "status": child.get("validation_status") or child.get("status") or child.get("report_status"),
        "decision": child.get("decision"),
        "effect": child.get("effect"),
        "report": child.get("report"),
        "blockers": child.get("blockers") or child.get("blocking_reasons") or [],
    }


def _blockers(payload: dict[str, Any]) -> list[Any]:
    blockers = payload.get("blockers")
    return list(blockers) if isinstance(blockers, list) else []


def _report_sources(payload: dict[str, Any], source: str) -> list[str]:
    sources = [source.split("#", 1)[0]]
    sources.extend(_sources_from_inputs(payload.get("inputs")))
    sources.extend(_sources_from_criteria(payload.get("criteria")))
    sources.extend(_sources_from_trace(payload.get("gate_decision_trace")))
    sources.extend(_sources_from_child_results(payload.get("child_results")))
    return [item for item in sources if item]


def _sources_from_inputs(inputs: Any) -> list[str]:
    sources: list[str] = []
    if isinstance(inputs, dict):
        for value in inputs.values():
            if isinstance(value, str):
                sources.append(value)
            elif isinstance(value, dict) and isinstance(value.get("source"), str):
                sources.append(value["source"])
    return sources


def _sources_from_criteria(criteria: Any) -> list[str]:
    if not isinstance(criteria, list):
        return []
    return [
        item["source"]
        for item in criteria
        if isinstance(item, dict) and isinstance(item.get("source"), str)
    ]


def _sources_from_trace(trace: Any) -> list[str]:
    if not isinstance(trace, dict):
        return []
    return _sources_from_inputs(trace.get("inputs"))


def _sources_from_child_results(child_results: Any) -> list[str]:
    if not isinstance(child_results, dict):
        return []
    return [
        child["report"]
        for child in child_results.values()
        if isinstance(child, dict) and isinstance(child.get("report"), str)
    ]


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or view the gate audit trail.")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write gate_audit_log.json before printing.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a table.")
    args = parser.parse_args(argv)

    payload = write_audit_log(args.output, report_dir=args.report_dir) if args.write else build_audit_log(args.report_dir)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(format_table(payload))
    return 0 if not payload.get("invalid_sources") else 1


if __name__ == "__main__":
    raise SystemExit(main())
