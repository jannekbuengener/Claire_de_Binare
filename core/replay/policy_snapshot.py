"""
Policy snapshot builder for #748 Slice 2 runtime wiring.

Builds a deterministic policy_snapshot dict for attachment to
Decision/Order/Fill envelopes when toggle ON.

Toggle: CDB_POLICY_SNAPSHOT_BINDING_ENABLED=0|1 (default OFF).
Read per call, no cache (testable via monkeypatch).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from core.utils.uuid_gen import POLICY_ID, compute_policy_hash


def policy_snapshot_binding_enabled() -> bool:
    """True only when CDB_POLICY_SNAPSHOT_BINDING_ENABLED == '1'.

    Reads os.getenv on every call (no module-level cache) so tests
    can toggle via monkeypatch.setenv.
    """
    return os.getenv("CDB_POLICY_SNAPSHOT_BINDING_ENABLED", "0") == "1"


def build_policy_snapshot(
    thresholds: dict,
    effective_at_ms: int,
) -> Dict[str, Any]:
    """Build a deterministic policy_snapshot dict.

    Args:
        thresholds: The DECISION_THRESHOLDS dict (source of checksum).
            Stable serialization via compute_policy_hash (sorted keys,
            compact separators, SHA256).
        effective_at_ms: Decision creation timestamp in ms (deterministic,
            NOT wall-clock). Converted to ISO-8601 UTC.

    Returns:
        Dict with keys: policy_id, version, git_commit, checksum, effective_at.
        All string values. No secrets, no PII.
    """
    effective_dt = datetime.fromtimestamp(
        effective_at_ms / 1000.0, tz=timezone.utc
    )

    return {
        "policy_id": POLICY_ID,
        "version": os.getenv("CDB_POLICY_VERSION", "unknown"),
        "git_commit": os.getenv("CDB_GIT_COMMIT", "unknown"),
        "checksum": compute_policy_hash(thresholds),
        "effective_at": effective_dt.isoformat(),
    }
