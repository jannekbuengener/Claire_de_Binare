"""Canonical capability export for the GitHub approval snapshot adapter (#4505)."""

from __future__ import annotations

import hashlib
from typing import Any

from tools.agent_control.approval.codes import DIGEST_PREFIX
from tools.agent_execution_contract.jcs import canonicalize_bytes

GITHUB_APPROVAL_SNAPSHOT_ADAPTER_ID = "cursor-approval-dashboard"
GITHUB_APPROVAL_SNAPSHOT_BASELINE_ID = "approval-dashboard-export.redacted.v1"

GITHUB_APPROVAL_SNAPSHOT_EXPORT: dict[str, Any] = {
    "adapter_id": GITHUB_APPROVAL_SNAPSHOT_ADAPTER_ID,
    "baseline_id": GITHUB_APPROVAL_SNAPSHOT_BASELINE_ID,
    "limitations": [
        "redacted export only",
        "no secrets",
        "MANUAL_BOOTSTRAP_ONLY dashboard fields",
        "public_crud_api false/unknown",
    ],
    "observed_capabilities": {
        "surface": "github-read-only-snapshot",
        "operations": [
            "branch_protection_required_checks",
            "check_runs_paginated",
            "commit_statuses",
            "graphql_review_threads_paginated",
            "issue_comments_paginated",
            "pull_request_metadata",
            "review_decision",
        ],
    },
    "public_crud_api": False,
}


def adapter_capability_fingerprint(export: dict[str, Any] | None = None) -> str:
    """Hash the canonical adapter capability export (independent of baseline)."""
    material = canonicalize_bytes(export or GITHUB_APPROVAL_SNAPSHOT_EXPORT)
    return f"{DIGEST_PREFIX}{hashlib.sha256(material).hexdigest()}"
