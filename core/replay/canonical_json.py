"""
Canonical JSON serialization for deterministic replay hashing.

Governance: LR-021 Slice 1 Evidence (docs/live-readiness/LR-021-EVIDENCE-SLICE1.md)

Rules:
  - Keys sorted lexicographically (sort_keys=True)
  - Compact separators (",", ":") -- no whitespace variance
  - None values OMITTED from dict serialization (not serialized as null)
  - None values in lists are preserved as null (removing would change indices)
  - Floats sanitized: NaN/Inf -> None (omitted from dicts, null in lists);
    normal floats rounded to 10 decimals; -0.0 normalized to 0.0
  - UTF-8 encoding for hashing

Isolation: This module has its own _sanitize_float(), intentionally decoupled
from core.utils.uuid_gen._sanitize_float(). Changes to the risk-service hashing
cannot silently alter replay hashes.

relations:
  role: serialization_utility
  domain: replay
  upstream: []
  downstream:
    - core/replay/envelopes.py
    - scripts/replay/lr021_replay.py
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def _sanitize_float(value: Any) -> Any:
    """Sanitize float values for deterministic JSON serialization.

    - NaN, +Inf, -Inf -> None (will be omitted from dicts by _omit_none)
    - Normal floats -> rounded to 10 decimal places
    - Recurses into dicts and lists.
    """
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        rounded = round(value, 10)
        # Normalize -0.0 -> 0.0 (equal in Python but different JSON strings)
        if rounded == 0.0:
            rounded = 0.0
        return rounded
    if isinstance(value, dict):
        return {k: _sanitize_float(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_float(v) for v in value]
    return value


def _omit_none(obj: Any) -> Any:
    """Recursively remove None-valued entries from dicts.

    List items are preserved (None in lists stays as null).
    """
    if isinstance(obj, dict):
        return {k: _omit_none(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_omit_none(item) for item in obj]
    return obj


def canonical_json_dumps(obj: Any) -> str:
    """Produce canonical JSON string: sorted keys, compact, None-omitted, float-sanitized.

    Args:
        obj: Any JSON-serializable Python object.

    Returns:
        Canonical JSON string suitable for deterministic hashing.
    """
    sanitized = _sanitize_float(obj)
    cleaned = _omit_none(sanitized)
    return json.dumps(cleaned, sort_keys=True, separators=(",", ":"))


def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 hex digest of raw bytes.

    Args:
        data: Raw bytes to hash.

    Returns:
        64-character lowercase hex string.
    """
    return hashlib.sha256(data).hexdigest()


def canonical_hash(obj: Any) -> str:
    """Convenience: canonical JSON -> UTF-8 bytes -> SHA-256 hex.

    Args:
        obj: Any JSON-serializable Python object.

    Returns:
        64-character lowercase hex string.
    """
    return sha256_hex(canonical_json_dumps(obj).encode("utf-8"))
