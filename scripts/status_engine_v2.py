from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from parent_gate_validator import CURRENT_DIR, HIERARCHY_JSON, validate_parent_gate  # noqa: E402


PARENT_GATES = ("m3a", "m4", "m5a")
BLOCKING_STATUSES = {"BLOCKED", "MISSING", "INVALID", "STALE"}


def evaluate_gate_layer(
    *,
    current_dir: Path = CURRENT_DIR,
    timestamp: str | None = None,
    max_report_age_hours: int | None = None,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(UTC).isoformat()
    parent_gates: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for gate in PARENT_GATES:
        try:
            parent_gates[gate] = validate_parent_gate(
                gate,
                report_dir=current_dir,
                hierarchy_path=HIERARCHY_JSON,
                timestamp=generated_at,
                max_report_age_hours=max_report_age_hours,
            )
        except Exception as exc:  # pragma: no cover - defensive adapter boundary
            errors[gate] = str(exc)
            parent_gates[gate] = _blocked_parent(gate, generated_at, str(exc))

    return {
        "layer": "gate",
        "generated_by": "status_engine_v2",
        "timestamp": generated_at,
        "source": "gate_engine",
        "parent_gates": parent_gates,
        "errors": errors,
    }


def evaluate_status(
    *,
    current_dir: Path = CURRENT_DIR,
    timestamp: str | None = None,
    gate_layer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(UTC).isoformat()
    gate_snapshot = gate_layer or evaluate_gate_layer(
        current_dir=current_dir,
        timestamp=generated_at,
        max_report_age_hours=None,
    )
    parent_gates = gate_snapshot.get("parent_gates") if isinstance(gate_snapshot.get("parent_gates"), dict) else {}
    parent_statuses = {
        gate: _status(parent_gates.get(gate))
        for gate in PARENT_GATES
    }
    phases = {
        "m3a": _phase_from_parent("m3a", "M3a", parent_statuses["m3a"], parent_gates.get("m3a")),
        "m4": _phase_from_parent("m4", "M4", parent_statuses["m4"], parent_gates.get("m4")),
        "m5a": _phase_from_parent("m5a", "M5a", parent_statuses["m5a"], parent_gates.get("m5a")),
    }

    m5_preparation_allowed = parent_statuses["m4"] == "PASS"
    m5_slice_work_allowed = m5_preparation_allowed and parent_statuses["m5a"] != "PASS"
    m5b_prepared = False
    m5b_implementation_allowed = False
    release_allowed = all(status == "PASS" for status in parent_statuses.values()) and m5b_implementation_allowed

    blockers = _status_blockers(parent_gates)
    if parent_statuses["m5a"] != "PASS":
        blockers.append({
            "id": "m5a_parent_not_pass",
            "type": "gate",
            "severity": "blocking",
            "detail": "M5a remains blocked until the m5a parent gate is PASS.",
            "source": "gate_engine:m5a",
        })
    blockers.append({
        "id": "m5b_implementation_gate_required",
        "type": "gate",
        "severity": "blocking",
        "detail": "M5b implementation requires a separate PASS gate in the gate layer.",
        "source": "status_engine_v2",
    })

    overall_status = "pass" if release_allowed else "blocked"
    return {
        "report_schema_version": 1,
        "report_name": "status_engine_v2",
        "report_type": "status",
        "layer": "status",
        "generated_by": "status_engine_v2",
        "timestamp": generated_at,
        "status": overall_status,
        "result": overall_status,
        "inputs": {
            "gate_layer": {
                "source": gate_snapshot.get("source", "gate_engine"),
                "timestamp": gate_snapshot.get("timestamp"),
                "parent_gates": sorted(parent_statuses),
            }
        },
        "parent_gate_statuses": parent_statuses,
        "phases": phases,
        "m5": {
            "preparation_allowed": m5_preparation_allowed,
            "slice_work_allowed": m5_slice_work_allowed,
            "m5a_status": parent_statuses["m5a"],
            "m5b_prepared": m5b_prepared,
            "m5b_implementation_allowed": m5b_implementation_allowed,
        },
        "release_allowed": release_allowed,
        "blockers": blockers,
        "architecture": {
            "gate_layer": "Gate Engine / parent gate aggregation",
            "status_layer": "status_engine_v2",
            "masterplan_layer": "masterplan_status_v2",
            "direct_report_reads_in_masterplan": False,
        },
    }


def write_status(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _blocked_parent(gate: str, timestamp: str, reason: str) -> dict[str, Any]:
    return {
        "report_schema_version": 1,
        "report_name": "parent_gate_validation",
        "generated_by": "status_engine_v2",
        "timestamp": timestamp,
        "parent_gate": gate,
        "status": "BLOCKED",
        "result": "BLOCKED",
        "decision": {"go_no_go": "NO_GO", "manual_override_allowed": False},
        "collected": 0,
        "passed": 0,
        "failed": 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 1,
        "mandatory_children": [],
        "child_results": {},
        "blockers": [{
            "id": f"{gate}_gate_layer_error",
            "child_gate_id": gate,
            "severity": "blocking",
            "reason": reason,
        }],
        "gate_decision_trace": {
            "parent_gate": gate,
            "rule": "Gate layer exception blocks this parent gate.",
            "evaluated_children": [],
            "blocking_children": [gate],
            "failing_children": [],
            "final_status": "BLOCKED",
        },
    }


def _status(parent_payload: Any) -> str:
    if not isinstance(parent_payload, dict):
        return "BLOCKED"
    return str(parent_payload.get("status") or parent_payload.get("result") or "BLOCKED").upper()


def _phase_from_parent(id_: str, label: str, status: str, parent_payload: Any) -> dict[str, Any]:
    blockers = []
    if isinstance(parent_payload, dict):
        for blocker in parent_payload.get("blockers", []):
            if isinstance(blocker, dict):
                blockers.append({
                    "id": str(blocker.get("id") or blocker.get("child_gate_id") or f"{id_}_blocker"),
                    "type": "gate",
                    "severity": str(blocker.get("severity") or "blocking"),
                    "detail": str(blocker.get("reason") or blocker.get("detail") or "parent gate blocker"),
                    "source": f"gate_engine:{id_}",
                    "child_gate_id": blocker.get("child_gate_id"),
                })
    return {
        "id": id_,
        "label": label,
        "status": "gate_passed" if status == "PASS" else "blocked",
        "decision": "GO" if status == "PASS" else "NO_GO",
        "gate_status": status,
        "source": f"gate_engine:{id_}",
        "blockers": blockers,
    }


def _status_blockers(parent_gates: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for gate in PARENT_GATES:
        payload = parent_gates.get(gate)
        status = _status(payload)
        if status == "PASS":
            continue
        if isinstance(payload, dict) and payload.get("blockers"):
            blockers.extend(_phase_from_parent(gate, gate.upper(), status, payload)["blockers"])
        else:
            blockers.append({
                "id": f"{gate}_not_pass",
                "type": "gate",
                "severity": "blocking",
                "detail": f"{gate} parent gate status is {status}.",
                "source": f"gate_engine:{gate}",
            })
    return blockers


def main() -> int:
    payload = evaluate_status()
    output = CURRENT_DIR / "status_engine_v2.json"
    write_status(payload, output)
    print(f"status_engine_v2 = {payload['status']}")
    print(f"Wrote: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
