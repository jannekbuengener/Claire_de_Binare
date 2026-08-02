"""SHA-256 integrity helpers for cdb.agent_execution.v1."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from tools.agent_execution_contract.errors import ContractValidationError
from tools.agent_execution_contract.jcs import canonicalize_bytes

DIGEST_PREFIX = "sha256:"
DIGEST_FIELD_PATH = ("integrity", "digest")


def _strip_digest(contract: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy with integrity.digest removed for hash input."""
    payload = copy.deepcopy(contract)
    integrity = payload.get("integrity")
    if isinstance(integrity, dict) and "digest" in integrity:
        integrity = dict(integrity)
        integrity.pop("digest", None)
        if integrity:
            payload["integrity"] = integrity
        else:
            payload.pop("integrity", None)
    return payload


def compute_digest(contract: dict[str, Any]) -> str:
    """Compute sha256:<hex> over JCS bytes of contract excluding integrity.digest."""
    if not isinstance(contract, dict):
        raise ContractValidationError(
            "CONTRACT_TYPE_INVALID",
            "contract must be a JSON object",
        )
    material = canonicalize_bytes(_strip_digest(contract))
    digest = hashlib.sha256(material).hexdigest()
    return f"{DIGEST_PREFIX}{digest}"


def attach_digest(contract: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with integrity metadata and computed digest attached."""
    payload = copy.deepcopy(contract)
    integrity = dict(payload.get("integrity") or {})
    integrity["canonicalization"] = "RFC8785"
    integrity["digest_algorithm"] = "sha256"
    integrity["digest_encoding"] = "sha256:<lowercase-hex>"
    payload["integrity"] = integrity
    # Ensure digest is absent before computation, then set.
    integrity.pop("digest", None)
    payload["integrity"]["digest"] = compute_digest(payload)
    return payload


def verify_digest(contract: dict[str, Any]) -> str:
    """Verify digest matches canonical bytes; return digest on success."""
    integrity = contract.get("integrity")
    if not isinstance(integrity, dict):
        raise ContractValidationError(
            "CONTRACT_HASH_MISSING",
            "integrity object is required",
        )
    claimed = integrity.get("digest")
    if not isinstance(claimed, str) or not claimed.startswith(DIGEST_PREFIX):
        raise ContractValidationError(
            "CONTRACT_HASH_INVALID",
            "integrity.digest must use encoding sha256:<lowercase-hex>",
        )
    expected = compute_digest(contract)
    if claimed != expected:
        raise ContractValidationError(
            "CONTRACT_HASH_MISMATCH",
            "integrity.digest does not match RFC8785/SHA-256 material",
        )
    return expected
