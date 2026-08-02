"""Constants and reason codes for cdb.pr_approval_context.v1 (#4257)."""

from __future__ import annotations

from tools.agent_control.errors import AgentControlError

SCHEMA_ID = "cdb.pr_approval_context.v1"
SCHEMA_VERSION = "1.0.0"

SHA40 = r"^[a-f0-9]{40}$"
DIGEST_PREFIX = "sha256:"

RECOMMENDATIONS = frozenset(
    {
        "APPROVE_RECOMMENDED",
        "REQUEST_CHANGES",
        "ABSTAIN",
        "HOLD",
        "BLOCKED",
        "UNKNOWN",
    }
)

DRIFT_STATUSES = frozenset(
    {
        "NONE",
        "POLICY",
        "PROMPT",
        "ADAPTER",
        "PROTECTION_VIEW",
        "UNKNOWN",
    }
)

CHECK_MECHANISMS = frozenset({"check_run", "commit_status", "unknown"})

AUTHORITY_LIMITS = {
    "merge": False,
    "publish_cdb_local_ci": False,
    "modify_branch_protection": False,
    "modify_rulesets": False,
    "execute_live_agent": False,
    "live_go": False,
    "real_money_go": False,
}

DEFAULT_POLICY_RELPATH = "config/agent-control/policies/approval/pr_approval.v1.yaml"
DEFAULT_PROMPT_RELPATH = "config/agent-control/prompts/approval/pr_approval.v1.md"
DEFAULT_BASELINE_RELPATH = (
    "config/agent-control/capability-baselines/"
    "approval-dashboard-export.redacted.v1.json"
)
DEFAULT_SCHEMA_RELPATH = "docs/contracts/cdb_pr_approval_context.v1.schema.json"

# Machine-readable reason / error codes (not recommendation values).
REASON_MISSING_HEAD = "MISSING_HEAD"
REASON_INVALID_HEAD = "INVALID_HEAD"
REASON_MISSING_BASE = "MISSING_BASE"
REASON_INVALID_BASE = "INVALID_BASE"
REASON_CONFLICTING_HEAD = "CONFLICTING_HEAD"
REASON_STALE_HEAD = "STALE_HEAD"
REASON_MISSING_POLICY = "MISSING_POLICY"
REASON_MISSING_PROMPT = "MISSING_PROMPT"
REASON_SECRET_DETECTED = "APPROVAL_SECRET_DETECTED"
REASON_SCHEMA_INVALID = "APPROVAL_SCHEMA_INVALID"
REASON_DIGEST_MISMATCH = "APPROVAL_DIGEST_MISMATCH"
REASON_DRAFT_PR = "DRAFT_PR"
REASON_CHANGES_REQUESTED = "CHANGES_REQUESTED"
REASON_BLOCKING_THREAD = "BLOCKING_THREAD"
REASON_UNKNOWN_REVIEW = "UNKNOWN_REVIEW_DECISION"
REASON_REQUIRED_CHECK_PENDING = "REQUIRED_CHECK_PENDING"
REASON_REQUIRED_CHECK_FAILED = "REQUIRED_CHECK_FAILED"
REASON_REQUIRED_CHECK_MISSING = "REQUIRED_CHECK_MISSING"
REASON_MECHANISM_MISMATCH = "MECHANISM_MISMATCH"
REASON_APP_ID_MISMATCH = "APP_ID_MISMATCH"
REASON_UNKNOWN_MECHANISM = "UNKNOWN_MECHANISM"
REASON_DRIFT = "DRIFT_PRESENT"
REASON_DRIFT_UNKNOWN = "DRIFT_UNKNOWN"
REASON_INCOMPLETE_SNAPSHOT = "INCOMPLETE_SNAPSHOT"
REASON_PROTECTION_INCOMPLETE = "PROTECTION_INCOMPLETE"
REASON_MISSING_DRAFT_STATE = "MISSING_DRAFT_STATE"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_BLOCKED = 2
EXIT_HOLD = 3
EXIT_UNKNOWN = 4


class ApprovalError(AgentControlError):
    """Fail-closed approval-context error with stable machine code."""
