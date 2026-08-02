"""JCS/SHA-256 digest helpers for cdb.pr_approval_context.v1."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from tools.agent_control.approval.codes import (
    DIGEST_PREFIX,
    REASON_DIGEST_MISMATCH,
    ApprovalError,
)
from tools.agent_execution_contract.jcs import canonicalize_bytes

# Metadata keys excluded from canonical digest material (wall-clock / volatile).
_NON_DIGEST_KEYS = frozenset({"observed_at", "snapshot_observed_at", "wall_clock"})


def _strip_digest_fields(envelope: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(envelope)
    payload.pop("context_digest", None)
    integrity = payload.get("integrity")
    if isinstance(integrity, dict):
        integrity = dict(integrity)
        integrity.pop("digest", None)
        if integrity:
            payload["integrity"] = integrity
        else:
            payload.pop("integrity", None)
    for key in _NON_DIGEST_KEYS:
        payload.pop(key, None)
    meta = payload.get("metadata")
    if isinstance(meta, dict):
        meta = dict(meta)
        for key in _NON_DIGEST_KEYS:
            meta.pop(key, None)
        if meta:
            payload["metadata"] = meta
        else:
            payload.pop("metadata", None)
    return payload


def compute_context_digest(envelope: dict[str, Any]) -> str:
    material = canonicalize_bytes(_strip_digest_fields(envelope))
    return f"{DIGEST_PREFIX}{hashlib.sha256(material).hexdigest()}"


def attach_context_digest(envelope: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(envelope)
    integrity = dict(payload.get("integrity") or {})
    integrity["canonicalization"] = "RFC8785"
    integrity["digest_algorithm"] = "sha256"
    integrity["digest_encoding"] = "sha256:<lowercase-hex>"
    payload["integrity"] = integrity
    integrity.pop("digest", None)
    digest = compute_context_digest(payload)
    payload["integrity"]["digest"] = digest
    payload["context_digest"] = digest
    return payload


def verify_context_digest(envelope: dict[str, Any]) -> str:
    claimed = envelope.get("context_digest")
    integrity = (
        envelope.get("integrity") if isinstance(envelope.get("integrity"), dict) else {}
    )
    claimed_integrity = integrity.get("digest") if isinstance(integrity, dict) else None
    if not isinstance(claimed, str) or not claimed.startswith(DIGEST_PREFIX):
        raise ApprovalError(
            REASON_DIGEST_MISMATCH,
            "context_digest missing or invalid encoding",
        )
    if claimed_integrity is not None and claimed_integrity != claimed:
        raise ApprovalError(
            REASON_DIGEST_MISMATCH,
            "integrity.digest disagrees with context_digest",
        )
    expected = compute_context_digest(envelope)
    if claimed != expected:
        raise ApprovalError(
            REASON_DIGEST_MISMATCH,
            "context_digest does not match RFC8785/SHA-256 material",
        )
    return expected
