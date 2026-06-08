"""M3a Release Candidate Stale Guard.

A RC is STALE when any of its mandatory input reports carries a timestamp
that is strictly newer than the RC's own timestamp.  A STALE RC must never
be treated as PASS by the status engine.

Stale triggers (all three checked independently):
- runtime_connectivity_gate.timestamp          > rc.timestamp
- frontend_full_suite_staged_report.timestamp  > rc.timestamp
- report_truth_preflight.timestamp             > rc.timestamp
- documentation_truth_lint.timestamp           > rc.timestamp

Additionally, generation is refused when preconditions are not satisfied:
- report_truth_preflight.status != PASS
- documentation_truth_lint.status != PASS (errors > 0 counts as not PASS)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STALE_STATUS = "STALE"
STALE_GATE = "BLOCKED"
_UNSET = object()

# Inputs that trigger staleness if they are newer than the RC.
STALENESS_INPUTS: tuple[str, ...] = (
    "runtime_connectivity_gate",
    "frontend_full_suite_staged_report",
    "report_truth_preflight",
    "documentation_truth_lint",
)


@dataclass(frozen=True)
class StaleResult:
    is_stale: bool
    reasons: list[str] = field(default_factory=list)

    @property
    def stale_reason(self) -> str | None:
        return "; ".join(self.reasons) if self.reasons else None


def _ts(report: dict[str, Any] | None) -> str | None:
    """Return the best-available ISO-8601 timestamp from a report dict."""
    if report is None:
        return None
    return report.get("timestamp") or report.get("generated_at")


def check_staleness(
    rc: dict[str, Any] | None,
    frontend_full_suite: dict[str, Any] | None,
    report_truth_preflight: dict[str, Any] | None,
    documentation_truth_lint: dict[str, Any] | None,
    runtime_connectivity_gate: dict[str, Any] | None | object = _UNSET,
) -> StaleResult:
    """Evaluate whether *rc* is stale relative to the supplied current reports.

    The comparison is purely lexicographic on ISO-8601 strings, which is
    correct as long as all timestamps use the same UTC representation.
    Absent timestamps in any mandatory input are treated as a staleness signal
    (unknown freshness → must regenerate).

    Args:
        rc: Contents of the existing m3a_release_candidate.json.
        frontend_full_suite: Contents of frontend_full_suite_staged_report.json.
        report_truth_preflight: Contents of report_truth_preflight.json.
        documentation_truth_lint: Contents of documentation_truth_lint.json.
        runtime_connectivity_gate: Contents of runtime_connectivity_gate.json.

    Returns:
        StaleResult with is_stale=True and reasons when the RC is outdated.
    """
    if rc is None:
        return StaleResult(is_stale=True, reasons=["rc_missing"])

    rc_ts = _ts(rc)
    if rc_ts is None:
        return StaleResult(is_stale=True, reasons=["rc_timestamp_missing"])

    reasons: list[str] = []

    candidates = {
        "frontend_full_suite_staged_report": frontend_full_suite,
        "report_truth_preflight": report_truth_preflight,
        "documentation_truth_lint": documentation_truth_lint,
    }
    if runtime_connectivity_gate is not _UNSET:
        candidates["runtime_connectivity_gate"] = runtime_connectivity_gate

    for name, report in candidates.items():
        if report is None:
            # Cannot verify freshness → treat as stale.
            reasons.append(f"{name}_missing")
            continue
        report_ts = _ts(report)
        if report_ts is None:
            reasons.append(f"{name}_timestamp_missing")
            continue
        if report_ts > rc_ts:
            reasons.append(f"{name}_newer_than_rc ({report_ts} > {rc_ts})")

    return StaleResult(is_stale=bool(reasons), reasons=reasons)


def check_preconditions(
    report_truth_preflight: dict[str, Any] | None,
    documentation_truth_lint: dict[str, Any] | None,
) -> list[str]:
    """Return a list of precondition violations that prevent RC generation.

    Generation is refused when:
    - report_truth_preflight is absent or its status is not PASS
    - documentation_truth_lint is absent or has errors > 0 or status is not PASS

    Returns:
        Empty list when all preconditions are satisfied; otherwise one entry per
        violated precondition.
    """
    violations: list[str] = []

    if report_truth_preflight is None:
        violations.append("report_truth_preflight_missing")
    else:
        status = str(report_truth_preflight.get("status") or report_truth_preflight.get("result") or "").upper()
        exit_code = report_truth_preflight.get("exit_code")
        if status != "PASS" or exit_code not in (0, None):
            violations.append(
                f"report_truth_preflight_not_pass (status={status!r}, exit_code={exit_code!r})"
            )

    if documentation_truth_lint is None:
        violations.append("documentation_truth_lint_missing")
    else:
        status = str(documentation_truth_lint.get("status") or documentation_truth_lint.get("result") or "").upper()
        summary = documentation_truth_lint.get("summary") if isinstance(documentation_truth_lint.get("summary"), dict) else {}
        errors = documentation_truth_lint.get("errors") or summary.get("errors") or 0
        exit_code = documentation_truth_lint.get("exit_code")
        if status != "PASS" or int(errors) > 0 or exit_code not in (0, None):
            violations.append(
                f"documentation_truth_lint_not_pass (status={status!r}, errors={errors!r})"
            )

    return violations
