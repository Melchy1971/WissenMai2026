"""
Tests for AnalysisApprovalPolicy — all 8 rules.
Pure unit tests, no database.
"""
import pytest
from app.services.analysis.approval_policy import (
    AnalysisApprovalPolicy,
    ApprovalContext,
    ApprovalPolicyViolation,
    RULE_CONFIRM_REQUIRED,
    RULE_STATUS_MUST_REVIEW,
    RULE_NO_SELF_APPROVE,
    RULE_REASON_REQUIRED,
    RULE_WORKSPACE_SCOPED,
    RULE_NOT_ALREADY_FINAL,
    RULE_JOB_MUST_COMPLETE,
    RULE_ADMIN_ONLY,
    ALL_RULES,
)

policy = AnalysisApprovalPolicy()

# ── Fixtures ─────────────────────────────────────────────────────────────────

def approve_ctx(**overrides) -> ApprovalContext:
    defaults = dict(
        action="approve",
        actor_id="admin-user",
        actor_role="admin",
        workspace_id="ws-1",
        result_id="res-1",
        result_status="review",
        result_workspace="ws-1",
        created_by="other-user",
        job_status="completed",
        confirm=True,
        reject_reason="",
    )
    defaults.update(overrides)
    return ApprovalContext(**defaults)


def reject_ctx(**overrides) -> ApprovalContext:
    defaults = dict(
        action="reject",
        actor_id="admin-user",
        actor_role="admin",
        workspace_id="ws-1",
        result_id="res-1",
        result_status="review",
        result_workspace="ws-1",
        created_by="other-user",
        job_status="completed",
        confirm=False,
        reject_reason="Content is incorrect.",
    )
    defaults.update(overrides)
    return ApprovalContext(**defaults)


# ── ALL_RULES constant ────────────────────────────────────────────────────────

def test_all_rules_count():
    assert len(ALL_RULES) == 8


# ── RULE-08: Admin only ───────────────────────────────────────────────────────

def test_member_cannot_approve():
    violations = policy.violations(approve_ctx(actor_role="member"))
    rules = [v.rule for v in violations]
    assert RULE_ADMIN_ONLY in rules


def test_member_cannot_reject():
    violations = policy.violations(reject_ctx(actor_role="member"))
    rules = [v.rule for v in violations]
    assert RULE_ADMIN_ONLY in rules


def test_admin_passes_rule08():
    ctx = approve_ctx(actor_role="admin")
    violations = policy.violations(ctx)
    assert not any(v.rule == RULE_ADMIN_ONLY for v in violations)


# ── RULE-05: Workspace scoped ─────────────────────────────────────────────────

def test_cross_workspace_approve_blocked():
    violations = policy.violations(approve_ctx(result_workspace="ws-other"))
    assert any(v.rule == RULE_WORKSPACE_SCOPED for v in violations)


def test_same_workspace_passes_rule05():
    violations = policy.violations(approve_ctx(workspace_id="ws-1", result_workspace="ws-1"))
    assert not any(v.rule == RULE_WORKSPACE_SCOPED for v in violations)


# ── RULE-06: Not already final ────────────────────────────────────────────────

def test_already_approved_blocked():
    violations = policy.violations(approve_ctx(result_status="approved"))
    assert any(v.rule == RULE_NOT_ALREADY_FINAL for v in violations)


def test_already_rejected_blocked():
    violations = policy.violations(approve_ctx(result_status="rejected"))
    assert any(v.rule == RULE_NOT_ALREADY_FINAL for v in violations)


def test_draft_status_not_blocked_by_rule06():
    # draft triggers RULE-02 (not review) but not RULE-06
    violations = policy.violations(approve_ctx(result_status="draft"))
    assert not any(v.rule == RULE_NOT_ALREADY_FINAL for v in violations)


# ── RULE-01: Confirm required ─────────────────────────────────────────────────

def test_approve_without_confirm_blocked():
    violations = policy.violations(approve_ctx(confirm=False))
    assert any(v.rule == RULE_CONFIRM_REQUIRED for v in violations)


def test_approve_with_confirm_passes_rule01():
    violations = policy.violations(approve_ctx(confirm=True))
    assert not any(v.rule == RULE_CONFIRM_REQUIRED for v in violations)


def test_reject_does_not_require_confirm():
    # confirm is irrelevant for reject — RULE-01 should not fire
    violations = policy.violations(reject_ctx(confirm=False))
    assert not any(v.rule == RULE_CONFIRM_REQUIRED for v in violations)


# ── RULE-02: Status must be review ────────────────────────────────────────────

def test_draft_cannot_be_approved():
    violations = policy.violations(approve_ctx(result_status="draft"))
    assert any(v.rule == RULE_STATUS_MUST_REVIEW for v in violations)


def test_review_status_passes_rule02():
    violations = policy.violations(approve_ctx(result_status="review"))
    assert not any(v.rule == RULE_STATUS_MUST_REVIEW for v in violations)


# ── RULE-03: No self-approve ──────────────────────────────────────────────────

def test_creator_cannot_approve_own_result():
    violations = policy.violations(approve_ctx(actor_id="creator-1", created_by="creator-1"))
    assert any(v.rule == RULE_NO_SELF_APPROVE for v in violations)


def test_different_user_passes_rule03():
    violations = policy.violations(approve_ctx(actor_id="approver-2", created_by="creator-1"))
    assert not any(v.rule == RULE_NO_SELF_APPROVE for v in violations)


def test_no_self_approve_skipped_when_created_by_none():
    # If created_by is unknown, self-approve check is skipped (can't determine)
    violations = policy.violations(approve_ctx(actor_id="admin-user", created_by=None))
    assert not any(v.rule == RULE_NO_SELF_APPROVE for v in violations)


def test_self_approve_rule_not_checked_for_reject():
    # RULE-03 only applies to approve
    violations = policy.violations(reject_ctx(actor_id="creator-1", created_by="creator-1"))
    assert not any(v.rule == RULE_NO_SELF_APPROVE for v in violations)


# ── RULE-07: Job must be completed ───────────────────────────────────────────

def test_running_job_blocks_approve():
    violations = policy.violations(approve_ctx(job_status="running"))
    assert any(v.rule == RULE_JOB_MUST_COMPLETE for v in violations)


def test_failed_job_blocks_approve():
    violations = policy.violations(approve_ctx(job_status="failed"))
    assert any(v.rule == RULE_JOB_MUST_COMPLETE for v in violations)


def test_completed_job_passes_rule07():
    violations = policy.violations(approve_ctx(job_status="completed"))
    assert not any(v.rule == RULE_JOB_MUST_COMPLETE for v in violations)


def test_job_status_not_checked_for_reject():
    violations = policy.violations(reject_ctx(job_status="running"))
    assert not any(v.rule == RULE_JOB_MUST_COMPLETE for v in violations)


# ── RULE-04: Reject reason required ──────────────────────────────────────────

def test_reject_without_reason_blocked():
    violations = policy.violations(reject_ctx(reject_reason=""))
    assert any(v.rule == RULE_REASON_REQUIRED for v in violations)


def test_reject_with_whitespace_only_blocked():
    violations = policy.violations(reject_ctx(reject_reason="   "))
    assert any(v.rule == RULE_REASON_REQUIRED for v in violations)


def test_reject_with_reason_passes_rule04():
    violations = policy.violations(reject_ctx(reject_reason="Inhalt ist veraltet."))
    assert not any(v.rule == RULE_REASON_REQUIRED for v in violations)


def test_approve_does_not_require_reject_reason():
    violations = policy.violations(approve_ctx(reject_reason=""))
    assert not any(v.rule == RULE_REASON_REQUIRED for v in violations)


# ── Happy path: zero violations ───────────────────────────────────────────────

def test_valid_approve_has_no_violations():
    ctx = approve_ctx()
    assert policy.violations(ctx) == []


def test_valid_reject_has_no_violations():
    ctx = reject_ctx()
    assert policy.violations(ctx) == []


# ── check() raises on first violation ────────────────────────────────────────

def test_check_raises_on_member_approve():
    with pytest.raises(ApprovalPolicyViolation) as exc_info:
        policy.check(approve_ctx(actor_role="member"))
    assert exc_info.value.rule == RULE_ADMIN_ONLY


def test_check_raises_on_self_approve():
    with pytest.raises(ApprovalPolicyViolation) as exc_info:
        policy.check(approve_ctx(actor_id="creator", created_by="creator"))
    assert exc_info.value.rule == RULE_NO_SELF_APPROVE


# ── ApprovalPolicyViolation str representation ────────────────────────────────

def test_violation_str_contains_rule_and_detail():
    exc = ApprovalPolicyViolation("RULE-99-TEST", "Something went wrong.")
    assert "RULE-99-TEST" in str(exc)
    assert "Something went wrong." in str(exc)
