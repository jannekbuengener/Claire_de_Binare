"""JCS/SHA-256 digest helpers for cdb.agent_run_evidence.v1."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from tools.agent_control.errors import EvidenceError
from tools.agent_control.evidence.codes import REASON_DIGEST_MISMATCH
from tools.agent_execution_contract.jcs import canonicalize_bytes

DIGEST_PREFIX = "sha256:"


def _strip_bundle_digest(bundle: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(bundle)
    payload.pop("bundle_digest", None)
    integrity = payload.get("integrity")
    if isinstance(integrity, dict):
        integrity = dict(integrity)
        integrity.pop("digest", None)
        if integrity:
            payload["integrity"] = integrity
        else:
            payload.pop("integrity", None)
    return payload


def compute_bundle_digest(bundle: dict[str, Any]) -> str:
    material = canonicalize_bytes(_strip_bundle_digest(bundle))
    return f"{DIGEST_PREFIX}{hashlib.sha256(material).hexdigest()}"


def attach_bundle_digest(bundle: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(bundle)
    integrity = dict(payload.get("integrity") or {})
    integrity["canonicalization"] = "RFC8785"
    integrity["digest_algorithm"] = "sha256"
    integrity["digest_encoding"] = "sha256:<lowercase-hex>"
    payload["integrity"] = integrity
    integrity.pop("digest", None)
    digest = compute_bundle_digest(payload)
    payload["integrity"]["digest"] = digest
    payload["bundle_digest"] = digest
    return payload


def verify_bundle_digest(bundle: dict[str, Any]) -> str:
    claimed = bundle.get("bundle_digest")
    integrity = (
        bundle.get("integrity") if isinstance(bundle.get("integrity"), dict) else {}
    )
    claimed_integrity = integrity.get("digest") if isinstance(integrity, dict) else None
    if not isinstance(claimed, str) or not claimed.startswith(DIGEST_PREFIX):
        raise EvidenceError(
            REASON_DIGEST_MISMATCH,
            "bundle_digest missing or invalid encoding",
        )
    if claimed_integrity is not None and claimed_integrity != claimed:
        raise EvidenceError(
            REASON_DIGEST_MISMATCH,
            "integrity.digest disagrees with bundle_digest",
        )
    expected = compute_bundle_digest(bundle)
    if claimed != expected:
        raise EvidenceError(
            REASON_DIGEST_MISMATCH,
            "bundle_digest does not match RFC8785/SHA-256 material",
        )
    return expected


def derive_evidence_id(bindings: dict[str, Any]) -> str:
    material = canonicalize_bytes(bindings)
    digest = hashlib.sha256(material).hexdigest()
    return f"are-{digest[:24]}"
