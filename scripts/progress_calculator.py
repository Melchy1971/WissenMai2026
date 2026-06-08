from __future__ import annotations

from typing import Any


BLOCKING_PARENT_STATUSES = {"BLOCKED", "MISSING", "INVALID", "STALE"}

WEIGHTS = {
    "m3a_parent": 25.0,
    "m4_parent": 30.0,
    "m5_preparation": 10.0,
    "m5a_slices": 10.0,
    "m5a_parent": 10.0,
    "m5b_prepared": 5.0,
    "m5b_implementation": 10.0,
}


def _is_pass(status: str | None) -> bool:
    return str(status or "").upper() == "PASS"


def _slice_progress(slice_passes: dict[str, bool]) -> tuple[float, list[dict[str, Any]]]:
    if not slice_passes:
        return 0.0, []
    per_slice = WEIGHTS["m5a_slices"] / len(slice_passes)
    components: list[dict[str, Any]] = []
    total = 0.0
    for name, passed in sorted(slice_passes.items()):
        earned = per_slice if passed else 0.0
        total += earned
        components.append({
            "id": f"m5a_slice_{name}",
            "weight": round(per_slice, 2),
            "earned": round(earned, 2),
            "passed": passed,
            "rule": "Slice PASS earns slice progress only; it does not replace M5a parent PASS.",
        })
    return total, components


def calculate_masterplan_progress(
    *,
    m3a_parent_status: str,
    m4_parent_status: str,
    m5a_parent_status: str,
    m3a_pass: bool,
    m4_pass: bool,
    m5_preparation_allowed: bool,
    m5a_slice_passes: dict[str, bool],
    m5a_effective_status: str,
    m5b_prepared: bool,
    m5b_implementation_allowed: bool,
    release_allowed: bool,
    documentation_pass: bool | None = None,
) -> dict[str, Any]:
    components: list[dict[str, Any]] = []

    def add(id_: str, weight: float, earned: float, *, passed: bool, rule: str) -> None:
        components.append({
            "id": id_,
            "weight": weight,
            "earned": earned,
            "passed": passed,
            "rule": rule,
        })

    add(
        "m3a_parent",
        WEIGHTS["m3a_parent"],
        WEIGHTS["m3a_parent"] if m3a_pass and _is_pass(m3a_parent_status) else 0.0,
        passed=m3a_pass and _is_pass(m3a_parent_status),
        rule="M3a progress requires technical parent PASS.",
    )
    add(
        "m4_parent",
        WEIGHTS["m4_parent"],
        WEIGHTS["m4_parent"] if m4_pass and _is_pass(m4_parent_status) else 0.0,
        passed=m4_pass and _is_pass(m4_parent_status),
        rule="M4 progress requires technical parent PASS.",
    )
    add(
        "m5_preparation",
        WEIGHTS["m5_preparation"],
        WEIGHTS["m5_preparation"] if m5_preparation_allowed else 0.0,
        passed=m5_preparation_allowed,
        rule="M5 preparation can progress after technical Operations release, but it is not M5 completion.",
    )

    slice_total, slice_components = _slice_progress(m5a_slice_passes)
    components.extend(slice_components)

    m5a_parent_pass = _is_pass(m5a_parent_status) and _is_pass(m5a_effective_status)
    add(
        "m5a_parent",
        WEIGHTS["m5a_parent"],
        WEIGHTS["m5a_parent"] if m5a_parent_pass else 0.0,
        passed=m5a_parent_pass,
        rule="M5a parent PASS is required separately from slice PASS.",
    )
    add(
        "m5b_prepared",
        WEIGHTS["m5b_prepared"],
        WEIGHTS["m5b_prepared"] if m5b_prepared else 0.0,
        passed=m5b_prepared,
        rule="M5b PREPARED is progress, not implementation completion.",
    )
    add(
        "m5b_implementation",
        WEIGHTS["m5b_implementation"],
        WEIGHTS["m5b_implementation"] if m5b_implementation_allowed else 0.0,
        passed=m5b_implementation_allowed,
        rule="M5b implementation requires its own technical PASS gate.",
    )

    progress = round(sum(float(item["earned"]) for item in components), 1)
    m5_complete = m5a_parent_pass and m5b_implementation_allowed
    caps: list[dict[str, Any]] = []

    if not m5_complete and progress >= 100.0:
        progress = 99.0
        caps.append({
            "id": "m5_not_complete_cap",
            "rule": "Overall progress is never 100 while M5 is incomplete.",
            "applied": True,
        })

    parent_statuses = {
        "m3a": str(m3a_parent_status or "UNKNOWN").upper(),
        "m4": str(m4_parent_status or "UNKNOWN").upper(),
        "m5a": str(m5a_parent_status or "UNKNOWN").upper(),
    }
    blocking_parent_gates = [
        gate for gate, status in parent_statuses.items()
        if status in BLOCKING_PARENT_STATUSES
    ]

    return {
        "progress_percent": progress,
        "m5_complete": m5_complete,
        "release_allowed": release_allowed,
        "blocking_parent_gates": blocking_parent_gates,
        "parent_gate_statuses": parent_statuses,
        "documentation_pass_counted": False,
        "documentation_pass_observed": documentation_pass,
        "components": components,
        "caps": caps,
        "weights": WEIGHTS,
    }
