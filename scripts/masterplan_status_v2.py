from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from progress_calculator import calculate_masterplan_progress  # noqa: E402
from status_engine_v2 import evaluate_status  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
OUTPUT_REPORT = "masterplan_status_v2.json"


def build_masterplan_status(
    *,
    timestamp: str | None = None,
    status_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(UTC).isoformat()
    status_layer = status_snapshot or evaluate_status(timestamp=generated_at)
    parent_statuses = _parent_statuses(status_layer)
    phases = status_layer.get("phases") if isinstance(status_layer.get("phases"), dict) else {}
    m5 = status_layer.get("m5") if isinstance(status_layer.get("m5"), dict) else {}

    m3a_pass = parent_statuses.get("m3a") == "PASS"
    m4_pass = parent_statuses.get("m4") == "PASS"
    m5a_pass = parent_statuses.get("m5a") == "PASS"
    release_allowed = bool(status_layer.get("release_allowed"))
    progress_model = calculate_masterplan_progress(
        m3a_parent_status=parent_statuses.get("m3a", "BLOCKED"),
        m4_parent_status=parent_statuses.get("m4", "BLOCKED"),
        m5a_parent_status=parent_statuses.get("m5a", "BLOCKED"),
        m3a_pass=m3a_pass,
        m4_pass=m4_pass,
        m5_preparation_allowed=bool(m5.get("preparation_allowed")),
        m5a_slice_passes={},
        m5a_effective_status=parent_statuses.get("m5a", "BLOCKED"),
        m5b_prepared=bool(m5.get("m5b_prepared")),
        m5b_implementation_allowed=bool(m5.get("m5b_implementation_allowed")),
        release_allowed=release_allowed,
        documentation_pass=None,
    )
    blockers = [
        blocker for blocker in status_layer.get("blockers", [])
        if isinstance(blocker, dict)
    ]
    overall_status = "pass" if release_allowed else "blocked"
    return {
        "report_schema_version": 2,
        "report_name": "masterplan_status_v2",
        "report_type": "status",
        "generated_by": "masterplan_status_v2",
        "timestamp": generated_at,
        "status": overall_status,
        "result": overall_status,
        "architecture": {
            "gate_layer": "gate_engine",
            "status_layer": "status_engine_v2",
            "masterplan_layer": "masterplan_status_v2",
            "direct_report_dependencies": [],
            "rule": (
                "Masterplan v2 consumes only Status Layer output. "
                "The Status Layer is the boundary to Gate Engine aggregates."
            ),
        },
        "inputs": {
            "gate_engine": {
                "parent_gate_statuses": parent_statuses,
            },
            "status_engine": {
                "report_name": status_layer.get("report_name"),
                "timestamp": status_layer.get("timestamp"),
                "status": status_layer.get("status"),
            },
        },
        "overall": {
            "status": overall_status,
            "progress_percent": progress_model["progress_percent"],
            "release_allowed": release_allowed,
            "blocker_count": len(blockers),
        },
        "progress_model": progress_model,
        "phases": phases,
        "m5": {
            "preparation_allowed": bool(m5.get("preparation_allowed")),
            "slice_work_allowed": bool(m5.get("slice_work_allowed")),
            "m5a_status": parent_statuses.get("m5a", "BLOCKED"),
            "m5b_prepared": bool(m5.get("m5b_prepared")),
            "m5b_implementation_allowed": bool(m5.get("m5b_implementation_allowed")),
        },
        "blockers": blockers,
        "status_layer": status_layer,
    }


def write_report(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _parent_statuses(status_layer: dict[str, Any]) -> dict[str, str]:
    raw = status_layer.get("parent_gate_statuses")
    if not isinstance(raw, dict):
        return {"m3a": "BLOCKED", "m4": "BLOCKED", "m5a": "BLOCKED"}
    return {
        gate: str(raw.get(gate) or "BLOCKED").upper()
        for gate in ("m3a", "m4", "m5a")
    }


def main() -> int:
    payload = build_masterplan_status()
    output = CURRENT_DIR / OUTPUT_REPORT
    write_report(payload, output)
    print(f"masterplan_status_v2 = {payload['overall']['status']}")
    print(f"progress: {payload['overall']['progress_percent']}%")
    print(f"Wrote: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
