"""Reason codes and authority-limit constants for cdb.agent_run_evidence.v1."""

from __future__ import annotations

SCHEMA_ID = "cdb.agent_run_evidence.v1"
SCHEMA_VERSION = "1.0.0"
EVIDENCE_CLASS = "agent_run_evidence_bundle_v1"
SNAPSHOT_SCHEMA_ID = "cdb.agent_dispatch_evidence_snapshot.v1"
SNAPSHOT_OUTPUT_TYPE = "dispatcher_lifecycle_snapshot"

DEFAULT_STORE_RELPATH = "artifacts/agent-control/evidence/agent_run_evidence.v1.jsonl"
ALLOWED_ARTIFACT_ROOTS = ("artifacts/",)

PROVENANCE_CLASSES = frozenset(
    {
        "control_plane_observed",
        "provider_reported",
        "agent_reported",
        "derived",
    }
)

COST_STATUS = frozenset(
    {
        "CONFIRMED",
        "UNAVAILABLE",
        "NOT_APPLICABLE",
    }
)

VERDICTS = frozenset({"PASS", "HOLD", "BLOCKED", "FAILED", "CANCELLED"})

FORBIDDEN_AUTHORITY_CLAIMS = frozenset(
    {
        "final_ci_success",
        "cdb_local_ci_success",
        "completeness_review_done",
        "approval_granted",
        "merge_authorized",
        "merge_readiness",
        "live_go",
        "productive_ops_go",
    }
)

AUTHORITY_LIMITS = {
    "not_final_ci": True,
    "not_cdb_local_ci": True,
    "not_completeness_review": True,
    "not_approval": True,
    "not_merge_authority": True,
    "not_merge_readiness": True,
    "not_live_go": True,
}

REASON_EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
REASON_SECRET_DETECTED = "EVIDENCE_SECRET_DETECTED"
REASON_DIGEST_MISMATCH = "EVIDENCE_DIGEST_MISMATCH"
REASON_DIGEST_COLLISION = "EVIDENCE_DIGEST_COLLISION"
REASON_ID_COLLISION = "EVIDENCE_ID_DIGEST_COLLISION"
REASON_LOCK_CONFLICT = "EVIDENCE_STORE_LOCK_CONFLICT"
REASON_PATH_INVALID = "EVIDENCE_PATH_INVALID"
REASON_SCHEMA_INVALID = "EVIDENCE_SCHEMA_INVALID"
REASON_AUTHORITY_CLAIM = "EVIDENCE_AUTHORITY_CLAIM_FORBIDDEN"
REASON_NO_DELIVERY_RECEIPT = "EVIDENCE_DELIVERY_RECEIPT_MISSING"
REASON_NON_TERMINAL = "EVIDENCE_RUN_NON_TERMINAL"
REASON_BINDING_MISMATCH = "EVIDENCE_BINDING_MISMATCH"
REASON_MALFORMED_STORE = "EVIDENCE_STORE_MALFORMED"
REASON_TRUNCATED_LINE = "EVIDENCE_STORE_TRUNCATED_LINE"
REASON_USAGE_INVALID = "EVIDENCE_USAGE_INVALID"
REASON_LIFECYCLE_NON_MONOTONE = "EVIDENCE_LIFECYCLE_NON_MONOTONE"
REASON_DUPLICATE_RUN_ATTEMPT = "EVIDENCE_DUPLICATE_RUN_ATTEMPT"
