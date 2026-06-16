"""
AnalysisApprovalPolicy — 8 mandatory security rules for analysis result approval.

PROHIBIT-08: Keine automatische M5c-Ausführung ohne PO-Approval je Proposal.
All rules are enforced BEFORE any state change. Raise ApprovalPolicyViolation on failure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# ── Violation ────────────────────────────────────────────────────────────────

class ApprovalPolicyViolation(Exception):
    """Raised when an approval rule is violated. Always maps to HTTP 422."""

    def __init__(self, rule: str, detail: str) -> None:
        self.rule = rule
        self.detail = detail
        super().__init__(f"[{rule}] {detail}")


# ── Rule IDs (stable, used in audit log) ─────────────────────────────────────

RULE_CONFIRM_REQUIRED   = "RULE-01-CONFIRM-REQUIRED"
RULE_STATUS_MUST_REVIEW = "RULE-02-STATUS-MUST-BE-REVIEW"
RULE_NO_SELF_APPROVE    = "RULE-03-NO-SELF-APPROVE"
RULE_REASON_REQUIRED    = "RULE-04-REJECT-REASON-REQUIRED"
RULE_WORKSPACE_SCOPED   = "RULE-05-WORKSPACE-SCOPED"
RULE_NOT_ALREADY_FINAL  = "RULE-06-NOT-ALREADY-FINAL"
RULE_JOB_MUST_COMPLETE  = "RULE-07-JOB-MUST-BE-COMPLETED"
RULE_ADMIN_ONLY         = "RULE-08-ADMIN-ONLY"

ALL_RULES = [
    RULE_CONFIRM_REQUIRED,
    RULE_STATUS_MUST_REVIEW,
    RULE_NO_SELF_APPROVE,
    RULE_REASON_REQUIRED,
    RULE_WORKSPACE_SCOPED,
    RULE_NOT_ALREADY_FINAL,
    RULE_JOB_MUST_COMPLETE,
    RULE_ADMIN_ONLY,
]


# ── Context dataclass (pure data, no ORM) ────────────────────────────────────

@dataclass(frozen=True)
class ApprovalContext:
    """Snapshot of everything the policy needs to evaluate rules."""
    action:            Literal["approve", "reject"]
    actor_id:          str
    actor_role:        Literal["member", "admin"]
    workspace_id:      str

    result_id:         str
    result_status:     str          # draft | review | approved | rejected
    result_workspace:  str
    created_by:        str | None   # user who created the job/result

    job_status:        str          # queued | running | completed | failed | cancelled
    confirm:           bool         # must be True for approve
    reject_reason:     str          # must be non-empty for reject


# ── Policy ────────────────────────────────────────────────────────────────────

class AnalysisApprovalPolicy:
    """
    Evaluates all 8 rules against an ApprovalContext.
    Call .check() — it raises ApprovalPolicyViolation on the FIRST violation.
    Call .violations() to collect ALL violations at once (for reporting).
    """

    def check(self, ctx: ApprovalContext) -> None:
        """Raise ApprovalPolicyViolation on first failed rule."""
        for violation in self._evaluate(ctx):
            raise violation

    def violations(self, ctx: ApprovalContext) -> list[ApprovalPolicyViolation]:
        """Return all violated rules (empty list = pass)."""
        return list(self._evaluate(ctx))

    def _evaluate(self, ctx: ApprovalContext):
        # RULE-08: admin role required for both approve and reject
        if ctx.actor_role != "admin":
            yield ApprovalPolicyViolation(
                RULE_ADMIN_ONLY,
                f"Actor '{ctx.actor_id}' has role '{ctx.actor_role}'; 'admin' required.",
            )

        # RULE-05: result must belong to the actor's workspace
        if ctx.result_workspace != ctx.workspace_id:
            yield ApprovalPolicyViolation(
                RULE_WORKSPACE_SCOPED,
                f"Result '{ctx.result_id}' belongs to workspace '{ctx.result_workspace}', "
                f"not '{ctx.workspace_id}'.",
            )

        # RULE-06: result must not already be in a terminal state (approved/rejected)
        if ctx.result_status in ("approved", "rejected"):
            yield ApprovalPolicyViolation(
                RULE_NOT_ALREADY_FINAL,
                f"Result '{ctx.result_id}' is already in terminal state '{ctx.result_status}'.",
            )

        if ctx.action == "approve":
            # RULE-01: explicit confirm=True required for approve
            if not ctx.confirm:
                yield ApprovalPolicyViolation(
                    RULE_CONFIRM_REQUIRED,
                    "Field 'confirm' must be True to approve a result.",
                )

            # RULE-02: result must be in 'review' to be approved
            if ctx.result_status != "review":
                yield ApprovalPolicyViolation(
                    RULE_STATUS_MUST_REVIEW,
                    f"Result must be in 'review' to approve; current status: '{ctx.result_status}'.",
                )

            # RULE-03: no self-approval (actor must differ from creator)
            if ctx.created_by and ctx.actor_id == ctx.created_by:
                yield ApprovalPolicyViolation(
                    RULE_NO_SELF_APPROVE,
                    f"Actor '{ctx.actor_id}' created this analysis and may not approve it.",
                )

            # RULE-07: underlying job must be completed
            if ctx.job_status != "completed":
                yield ApprovalPolicyViolation(
                    RULE_JOB_MUST_COMPLETE,
                    f"Underlying job must be 'completed'; current status: '{ctx.job_status}'.",
                )

        elif ctx.action == "reject":
            # RULE-04: reject requires a non-empty reason
            if not ctx.reject_reason or not ctx.reject_reason.strip():
                yield ApprovalPolicyViolation(
                    RULE_REASON_REQUIRED,
                    "A non-empty 'reason' is required to reject a result.",
                )
