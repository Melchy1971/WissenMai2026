#!/usr/bin/env python3
"""
Local Final Gate Validator v2

Regeln:
  1. Required FAIL/BLOCKED/INVALID → verdict BLOCKED
  2. Optional FAIL/PARTIAL_FAIL/INVALID → Warning
  3. external_only → separate Section, blockiert nicht
  4. legacy_non_blocking muss archiviert sein (archive_report PASS)
  5. Keine Skips in required local gate
  6. permission_denied blockiert nur wenn aktiver Pfad betroffen ist

Input:  local_final_gate_dependency_graph.json + reports/current/*.json
Output: reports/current/final_gate_report.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports" / "current"
GRAPH_FILE = REPO_ROOT / "local_final_gate_dependency_graph.json"
OUTPUT_FILE = REPORTS_DIR / "final_gate_report.json"


def load_json(path: Path) -> tuple:
    """Load JSON, return (data, error_string)."""
    try:
        with open(path) as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, "FILE_NOT_FOUND"
    except json.JSONDecodeError as e:
        return None, f"JSON_PARSE_ERROR: {e}"


def resolve_field(data: dict, dotpath: str):
    """Resolve dotted path like 'local_gate.status' or 'test_files_run.2.status'."""
    parts = dotpath.split(".")
    val = data
    for part in parts:
        if isinstance(val, list):
            try:
                val = val[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(val, dict):
            val = val.get(part)
        else:
            return None
    return val


def check_archive_report(archive_report_name: str) -> tuple:
    """Rule 4: legacy_non_blocking must be archived."""
    path = REPORTS_DIR / archive_report_name
    data, err = load_json(path)
    if err:
        return "MISSING", f"{archive_report_name}: {err}"
    status = data.get("status", "UNKNOWN")
    if status == "PASS":
        return "PASS", f"{archive_report_name} status=PASS — legacy tests archived"
    return "FAIL", f"{archive_report_name} status={status} — legacy tests NOT archived"


def evaluate_gate(gate: dict) -> dict:
    """Evaluate a single gate according to its type and rules."""
    gid = gate["id"]
    gtype = gate["type"]
    report_name = gate["report"]
    path = REPORTS_DIR / report_name

    data, err = load_json(path)

    result = {
        "id": gid,
        "type": gtype,
        "report": report_name,
        "description": gate.get("description", ""),
    }

    # --- Rule 3: external_only (even if file missing = NOT_RUN, still non-blocking) ---
    if gtype == "external_only":
        if err:
            result["status"] = "NOT_RUN"
            result["error"] = err
        else:
            resolve_key = gate.get("resolve", "status")
            result["status"] = str(resolve_field(data, resolve_key) or "UNKNOWN")
        result["verdict"] = "EXTERNAL_ONLY"
        result["reason"] = "external_only Gate: dokumentiert, blockiert local_final_gate nicht"
        return result

    # --- Rule 6 / Rule 4: legacy_non_blocking ---
    if gtype == "legacy_non_blocking":
        blocked_path = gate.get("blocked_path", "")
        safe_replacement = gate.get("safe_replacement_path", "")
        safe_active = gate.get("safe_replacement_active", False)
        result["blocked_path"] = blocked_path
        result["safe_replacement_path"] = safe_replacement
        result["safe_replacement_active"] = safe_active
        result["rule_applied"] = "rule_6"
        if err:
            result["status"] = "FILE_NOT_FOUND"
            result["error"] = err
        else:
            resolve_key = gate.get("resolve", "status")
            result["status"] = str(resolve_field(data, resolve_key) or "UNKNOWN")
        if safe_active:
            result["verdict"] = "NON_BLOCKING"
            result["reason"] = (
                f"Aktiver Pfad ist '{safe_replacement}' (drift_v2). "
                f"ACL-Blockierung auf '{blocked_path}' (alt) betrifft keinen aktiven Pfad. "
                "Regel 6: NON_BLOCKING."
            )
        else:
            result["verdict"] = "BLOCKED"
            result["reason"] = (
                f"Kein aktiver Ersatzpfad für '{blocked_path}'. Regel 6 nicht anwendbar. BLOCKED."
            )
        return result

    # --- File missing for required/optional ---
    if err:
        status_val = "INVALID"
        result["status"] = status_val
        result["error"] = err
        if gtype == "optional":
            result["verdict"] = "WARNING"
            result["reason"] = f"Optional gate {gid}: Report nicht lesbar ({err}) — Warning"
        else:
            result["verdict"] = "BLOCKED"
            result["reason"] = f"Regel 1: Required gate {gid}: Report nicht lesbar ({err}) — BLOCKED"
        return result

    # --- optional ---
    if gtype == "optional":
        resolve_key = gate.get("resolve", "status")
        status = resolve_field(data, resolve_key)
        warn_values = gate.get("warn_values", ["FAIL", "BLOCKED", "INVALID", "PARTIAL_FAIL"])
        note = gate.get("note", "")
        result["resolved_field"] = resolve_key
        result["resolved_value"] = status
        result["status"] = str(status)
        result["note"] = note
        if str(status) in warn_values:
            result["verdict"] = "WARNING"
            result["reason"] = f"Optional gate {gid} status={status}: Warning erzeugt, kein Blocker. {note}"
        else:
            result["verdict"] = "PASS"
            result["reason"] = f"Optional gate {gid} status={status}: OK"
        return result

    # --- required ---
    resolve_key = gate.get("resolve", "status")
    pass_values = gate.get("pass_values", ["PASS"])

    result["resolved_field"] = resolve_key

    # Special: known_limitations uses blocking_limitations count
    if gate.get("pass_when_blocking_zero"):
        lims = data.get("limitations", [])
        blocking_count = sum(1 for l in lims if l.get("severity") == "BLOCKING_CORE")
        result["blocking_limitations"] = blocking_count
        result["resolved_value"] = blocking_count
        result["status"] = "PASS" if blocking_count == 0 else "BLOCKED"
        if blocking_count == 0:
            result["verdict"] = "PASS"
            result["reason"] = f"known_limitations: {blocking_count} BLOCKING_CORE Limitations"
        else:
            result["verdict"] = "BLOCKED"
            result["reason"] = f"known_limitations: {blocking_count} BLOCKING_CORE Limitations vorhanden"
        return result

    status = resolve_field(data, resolve_key)
    result["resolved_value"] = status
    result["status"] = str(status)

    # Rule 5: skip check on backend_local_gate
    skip_field = gate.get("skip_check")
    skip_max = gate.get("skip_max", 0)
    if skip_field:
        skip_count = resolve_field(data, skip_field)
        result["skip_count"] = skip_count
        if skip_count is not None and skip_count > skip_max:
            result["verdict"] = "BLOCKED"
            result["reason"] = f"Regel 5: {skip_count} Skips in required local gate (max={skip_max})"
            return result

    # Rule 1: FAIL/BLOCKED/INVALID blocks
    blocking_states = {"FAIL", "BLOCKED", "INVALID", "BLOCKED_BY_FILESYSTEM_ACL", "BLOCKED_BY_ACL", "ERROR"}
    if str(status) in pass_values:
        result["verdict"] = "PASS"
        result["reason"] = f"status={status} in pass_values"
    elif str(status) in blocking_states:
        result["verdict"] = "BLOCKED"
        result["reason"] = f"Regel 1: status={status} blockiert required gate (pass_values={pass_values})"
    else:
        # INFO, WARNING etc. for required gates: treat as pass only if explicitly allowed
        result["verdict"] = "BLOCKED"
        result["reason"] = f"Regel 1: status={status} nicht in pass_values={pass_values} — BLOCKED"

    return result


def main():
    now = datetime.now(timezone.utc).isoformat()

    graph, err = load_json(GRAPH_FILE)
    if err:
        print(f"FATAL: Cannot load dependency graph: {err}", file=sys.stderr)
        sys.exit(2)

    gates = graph.get("gates", [])
    archive_report_name = graph.get("archive_report", "frontend_legacy_test_archive_report.json")

    # Rule 4: archive check
    archive_status, archive_reason = check_archive_report(archive_report_name)

    results = []
    blockers = []
    warnings = []
    external_gates = []
    non_blocking_gates = []

    for gate in gates:
        gtype = gate.get("type", "required")

        # Rule 4: legacy_non_blocking requires archive PASS
        if gtype == "legacy_non_blocking" and archive_status != "PASS":
            r = {
                "id": gate["id"],
                "type": gtype,
                "report": gate["report"],
                "status": "ARCHIVE_MISSING",
                "verdict": "BLOCKED",
                "reason": f"Regel 4: legacy_non_blocking Gate ohne Archive-Bestätigung. {archive_reason}",
            }
            results.append(r)
            blockers.append({"gate": gate["id"], "reason": r["reason"]})
            continue

        r = evaluate_gate(gate)
        results.append(r)

        v = r["verdict"]
        if v == "BLOCKED":
            blockers.append({"gate": r["id"], "reason": r.get("reason", r.get("status", "UNKNOWN"))})
        elif v == "WARNING":
            warnings.append({"gate": r["id"], "reason": r.get("reason", "")})
        elif v == "EXTERNAL_ONLY":
            external_gates.append({"gate": r["id"], "status": r.get("status", "UNKNOWN")})
        elif v == "NON_BLOCKING":
            non_blocking_gates.append({"gate": r["id"], "reason": r.get("reason", "")})

    verdict = "BLOCKED" if blockers else "PASS"

    report = {
        "report": "final_gate_report",
        "schema_version": 2,
        "validator": "local_final_gate_validator_v2",
        "dependency_graph": "local_final_gate_dependency_graph.json",
        "generated_at": now,
        "verdict": verdict,
        "summary": {
            "total_gates": len(gates),
            "required_pass": sum(1 for r in results if r["type"] == "required" and r["verdict"] == "PASS"),
            "required_blocked": len(blockers),
            "optional_warnings": len(warnings),
            "external_only": len(external_gates),
            "non_blocking": len(non_blocking_gates),
        },
        "blockers": blockers,
        "warnings": warnings,
        "external_only": external_gates,
        "non_blocking": non_blocking_gates,
        "archive_check": {
            "report": archive_report_name,
            "status": archive_status,
            "reason": archive_reason,
        },
        "gate_results": results,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    print(f"verdict: {verdict}")
    print(f"blockers: {len(blockers)}")
    print(f"warnings: {len(warnings)}")
    print(f"external_only: {len(external_gates)}")
    for b in blockers:
        print(f"  BLOCKED: [{b['gate']}] {b['reason'][:100]}")
    for w in warnings:
        print(f"  WARNING: [{w['gate']}] {w['reason'][:100]}")
    for e in external_gates:
        print(f"  EXTERNAL: [{e['gate']}] status={e['status']}")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
