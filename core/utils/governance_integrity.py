"""
Integrity helpers for governance mirror tables.

Hashing uses HMAC-SHA256 over canonical JSON from core.replay.canonical_json.
The signing key is read from the external environment variable
``CDB_AUDIT_INTEGRITY_KEY`` and is never stored in the database.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Any

from core.replay.canonical_json import canonical_json_dumps

INTEGRITY_KEY_ENV = "CDB_AUDIT_INTEGRITY_KEY"
INTEGRITY_ALGO = "hmac-sha256"
INTEGRITY_VERSION = 1

STATUS_OK = "OK"
STATUS_FAIL = "FAIL"

REASON_OK = "INTEGRITY_OK"
REASON_HASH_MISMATCH = "INTEGRITY_HASH_MISMATCH"
REASON_HASH_MISSING = "INTEGRITY_HASH_MISSING"
REASON_KEY_MISSING = "INTEGRITY_KEY_MISSING"
REASON_VALIDATION_SKIPPED = "INTEGRITY_VALIDATION_SKIPPED_FORCED_FAIL"
REASON_UNSUPPORTED_ALGO = "INTEGRITY_UNSUPPORTED_ALGO"
REASON_UNSUPPORTED_VERSION = "INTEGRITY_UNSUPPORTED_VERSION"

TABLE_HASH_FIELDS = {
    "audit_trail": (
        "id",
        "service_name",
        "action_type",
        "actor_id",
        "payload",
        "created_at",
    ),
    "governance_events": (
        "id",
        "event_type",
        "evidence_ref",
        "created_at",
    ),
}


def resolve_integrity_key(key: str | None = None) -> str | None:
    """Resolve the external integrity key from the override or environment."""
    if key is not None:
        return key
    return os.getenv(INTEGRITY_KEY_ENV)


def _normalize_timestamp(value: Any) -> Any:
    """Normalize timestamps to UTC ISO-8601 with ``Z`` suffix."""
    if isinstance(value, datetime):
        dt_value = value
    elif isinstance(value, str):
        try:
            dt_value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    else:
        return value

    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_value(value: Any) -> Any:
    """Recursively normalize database row values before canonical hashing."""
    timestamp = _normalize_timestamp(value)
    if timestamp is not value:
        return timestamp
    if isinstance(value, dict):
        return {key: _normalize_value(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_normalize_value(inner) for inner in value]
    return value


def build_integrity_payload(table_name: str, row: dict[str, Any]) -> dict[str, Any]:
    """Build the canonical payload used for row-level integrity hashing."""
    fields = TABLE_HASH_FIELDS.get(table_name)
    if fields is None:
        raise ValueError(f"unsupported governance integrity table: {table_name}")

    return {
        "table": table_name,
        "version": INTEGRITY_VERSION,
        "row": {field: _normalize_value(row.get(field)) for field in fields},
    }


def compute_integrity_hash(
    table_name: str,
    row: dict[str, Any],
    key: str | None = None,
) -> str:
    """Compute the HMAC-SHA256 integrity hash for a governance row."""
    resolved_key = resolve_integrity_key(key)
    if not resolved_key:
        raise ValueError(f"{INTEGRITY_KEY_ENV} is not set")

    material = canonical_json_dumps(build_integrity_payload(table_name, row)).encode(
        "utf-8"
    )
    return hmac.new(
        resolved_key.encode("utf-8"),
        material,
        hashlib.sha256,
    ).hexdigest()


def seal_row(
    table_name: str,
    row: dict[str, Any],
    key: str | None = None,
) -> dict[str, Any]:
    """Return a copy of the row with integrity metadata populated."""
    sealed = dict(row)
    sealed["integrity_algo"] = INTEGRITY_ALGO
    sealed["integrity_version"] = INTEGRITY_VERSION
    sealed["integrity_hash"] = compute_integrity_hash(table_name, sealed, key=key)
    return sealed


def _hash_prefix(value: str | None) -> str | None:
    if not value:
        return None
    return value[:12]


def _coerce_version(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_row_integrity(
    table_name: str,
    row: dict[str, Any],
    key: str | None = None,
) -> dict[str, Any]:
    """Validate a single governance row and return an audit-friendly result."""
    stored_hash = row.get("integrity_hash")
    stored_algo = row.get("integrity_algo")
    stored_version = _coerce_version(row.get("integrity_version"))
    row_id = row.get("id")

    result = {
        "table": table_name,
        "row_id": row_id,
        "status": STATUS_FAIL,
        "reason_code": None,
        "reason": None,
        "stored_hash_prefix": _hash_prefix(stored_hash),
        "expected_hash_prefix": None,
    }

    resolved_key = resolve_integrity_key(key)
    if not resolved_key:
        result["reason_code"] = REASON_KEY_MISSING
        result["reason"] = f"{INTEGRITY_KEY_ENV} is not set"
        return result

    if not stored_hash:
        result["reason_code"] = REASON_HASH_MISSING
        result["reason"] = "integrity_hash is missing"
        return result

    if stored_algo != INTEGRITY_ALGO:
        result["reason_code"] = REASON_UNSUPPORTED_ALGO
        result["reason"] = f"unsupported integrity_algo: {stored_algo!r}"
        return result

    if stored_version != INTEGRITY_VERSION:
        result["reason_code"] = REASON_UNSUPPORTED_VERSION
        result["reason"] = (
            f"unsupported integrity_version: {row.get('integrity_version')!r}"
        )
        return result

    expected_hash = compute_integrity_hash(table_name, row, key=resolved_key)
    result["expected_hash_prefix"] = _hash_prefix(expected_hash)

    if not hmac.compare_digest(expected_hash, stored_hash):
        result["reason_code"] = REASON_HASH_MISMATCH
        result["reason"] = "stored integrity_hash does not match canonical HMAC"
        return result

    result["status"] = STATUS_OK
    result["reason_code"] = REASON_OK
    result["reason"] = "integrity_hash matches canonical HMAC"
    return result
