"""Dataset request vs content identity for ARVP provenance.

Issue #4151 (first narrow provenance slice): keep request identity (what was
asked for) strictly separate from content identity (what was actually loaded).

Request fingerprint
-------------------
Delegates to ``DatasetSpec.fingerprint()``. Includes source, window, warmup,
and source-specific labels (``file_path`` / ``db_dataset_window``). It does
**not** depend on candle bytes.

Content fingerprint
-------------------
SHA-256 over a versioned, canonically serialized payload of the candle series
actually returned by a provider. File and DB rows are normalized to the same
semantic fields so equivalent OHLCV content hashes identically regardless of
provider, path, Decimal vs float representation, or omitted nulls.

Secrets, DSNs, and local paths never enter the content payload.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash, canonical_json_dumps
from core.replay.dataset_spec import DatasetSpec

CONTENT_IDENTITY_SCHEMA_VERSION = "cdb.dataset_content_identity.v1"

# Semantic market-data fields shared by file and DB providers.
# Key order here is documentary; canonical_json sorts keys for hashing.
CONTENT_CANDLE_KEYS: tuple[str, ...] = (
    "ts_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
)

# Keys that must never appear in content-identity evidence payloads.
_FORBIDDEN_EVIDENCE_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "api_secret",
        "connection_string",
        "database_url",
        "dsn",
        "file_path",
        "password",
        "path",
        "postgres_password",
        "redis_password",
        "secret",
        "token",
    }
)


def request_fingerprint(spec: DatasetSpec) -> str:
    """Return the deterministic request identity for ``spec``.

    Compatible alias for ``DatasetSpec.fingerprint()``.
    """
    return spec.fingerprint()


def _normalize_number(value: Any) -> Any:
    """Normalize numeric candle values for File/DB parity.

    ``Decimal`` (DB) and ``float`` (file JSON) are reduced to the same float
    sanitization path used by ``canonical_json`` (10-decimal rounding, -0.0).
    Non-finite Decimals become ``None`` (omitted from dicts).
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        try:
            if not value.is_finite():
                return None
            # String round-trip strips scientific notation / trailing zeros
            # before float conversion so File floats and DB Decimals converge.
            text = format(value.normalize(), "f")
        except (InvalidOperation, ValueError):
            return None
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        if text in {"", "-", "+"}:
            text = "0"
        try:
            return float(text)
        except ValueError:
            return None
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return _normalize_number(Decimal(stripped))
        except (InvalidOperation, ValueError):
            return stripped
    return value


def normalize_candle_for_content(candle: Mapping[str, Any]) -> dict[str, Any]:
    """Project one candle onto the semantic content schema.

    Unknown / provider-only fields (``symbol``, ``regime_id``, ``trade_count``,
    paths, secrets) are dropped. Missing or ``None`` optional OHLCV fields are
    omitted so File rows without ``open``/``volume`` stay stable.
    """
    out: dict[str, Any] = {}
    for key in CONTENT_CANDLE_KEYS:
        if key not in candle:
            continue
        value = candle[key]
        if value is None:
            continue
        if key == "ts_ms":
            out[key] = int(value)
        else:
            normalized = _normalize_number(value)
            if normalized is not None:
                out[key] = normalized
    return out


def normalize_candles_for_content(
    candles: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize and deterministically order candles by ``ts_ms``."""
    normalized = [normalize_candle_for_content(c) for c in candles]
    return sorted(normalized, key=lambda row: int(row.get("ts_ms", 0)))


def build_content_identity_payload(
    candles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the versioned payload hashed as content identity."""
    return {
        "candles": normalize_candles_for_content(candles),
        "schema_version": CONTENT_IDENTITY_SCHEMA_VERSION,
    }


def content_identity_canonical_json(candles: Sequence[Mapping[str, Any]]) -> str:
    """Return the repeatable canonical JSON for content identity."""
    return canonical_json_dumps(build_content_identity_payload(candles))


def content_fingerprint(candles: Sequence[Mapping[str, Any]]) -> str:
    """Deterministic 64-char SHA-256 hex of actually loaded candle content."""
    return canonical_hash(build_content_identity_payload(candles))


def collect_forbidden_evidence_keys(payload: Mapping[str, Any]) -> list[str]:
    """Return sorted forbidden keys found anywhere in a nested mapping/list."""
    found: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                key_str = str(key)
                if key_str in _FORBIDDEN_EVIDENCE_KEYS or key_str.lower() in {
                    k.lower() for k in _FORBIDDEN_EVIDENCE_KEYS
                }:
                    found.add(key_str)
                _walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                _walk(item)

    _walk(payload)
    return sorted(found)


def assert_content_payload_secret_safe(payload: Mapping[str, Any]) -> None:
    """Fail-closed guard: content identity must not embed secrets or paths."""
    bad = collect_forbidden_evidence_keys(payload)
    if bad:
        raise ValueError(
            "content identity payload must not include secret/path/DSN fields: "
            + ", ".join(bad)
        )
