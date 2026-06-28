"""DB-Record Evidence Response Schema validator (Issue #3421).

Read-only validation for the standardized response envelope that wraps
SurrealDB query results from MCP evidence tools. Does not access the
database, does not perform writes, and does not authorize any action.

LR remains NO-GO.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA_VERSION = "db-record-evidence-response/v1"

ALLOWED_TOOLS = frozenset(
    {
        "cdb_context_evidence_resolve",
        "cdb_context_claim_resolve",
        "cdb_context_memory_get",
        "cdb_context_trust_summary",
    }
)

ALLOWED_SOURCES = frozenset(
    {
        "surrealdb-local",
        "surrealdb-local-unavailable",
        "in_memory",
    }
)

ALLOWED_STATUSES = frozenset({"ok", "error"})

ALLOWED_TRUST_CLASSIFICATIONS = frozenset(
    {
        "valid_db_backed",
        "partial",
        "repo_only",
        "in_memory_fixture",
        "accepted_limitation",
        "invalid_fake_db",
    }
)

ALLOWED_TRUST_LEVELS = frozenset({"HIGH", "MEDIUM", "LOW", "BLOCKED"})

ALLOWED_SOURCE_PRIORITIES = frozenset(
    {
        "live_github",
        "repo_files",
        "surrealdb_context",
        "ledger_snapshots",
        "fallback",
    }
)

ALLOWED_FRESHNESS_SIGNALS = frozenset({"fresh", "aging", "stale", "unknown"})

STANDARD_LIMITATIONS = (
    "Memory is provided as context, not as authoritative truth.",
    "stale/superseded memory is flagged but not auto-removed.",
    "LR remains NO-GO; no live-go or Echtgeld-GO implied.",
)

SECRET_SUBSTRINGS = frozenset(
    {
        "SURREAL_PASS",
        "SURREAL_USER",
        "Authorization:",
        "Authorization ",
        "Basic ",
        "password=",
        "api_key=",
        "api-key=",
        "secret=",
        "token=",
        "Bearer ",
    }
)

_SECRET_RE = re.compile(
    "|".join(re.escape(s) for s in sorted(SECRET_SUBSTRINGS, key=len, reverse=True)),
    re.IGNORECASE,
)

REQUIRED_OK_FIELDS = frozenset(
    {
        "schema_version",
        "tool",
        "status",
        "source",
        "metadata",
        "record_count",
        "records",
        "filters_applied",
        "trust",
        "freshness",
        "limitations",
        "no_echtgeld_go",
    }
)

REQUIRED_ERROR_FIELDS = frozenset(
    {
        "schema_version",
        "tool",
        "status",
        "error",
        "metadata",
        "limitations",
        "no_echtgeld_go",
    }
)

REQUIRED_METADATA_FIELDS = frozenset({"source", "read_only", "query_time_ms"})

REQUIRED_TRUST_FIELDS = frozenset(
    {"level", "classification", "confidence", "source_priority"}
)

REQUIRED_FRESHNESS_FIELDS = frozenset(
    {"age_seconds", "stale_threshold_seconds", "is_stale", "freshness_signal"}
)


class DbRecordEvidenceResponseError(ValueError):
    """Raised when a response violates the evidence response schema."""


def _as_str(value: Any) -> str:
    return str(value) if value is not None else ""


def _has_secret_leak(text: str) -> bool:
    return bool(_SECRET_RE.search(text))


def _serialize_for_scan(obj: Any) -> str:
    if isinstance(obj, Mapping):
        parts = []
        for key in sorted(obj.keys()):
            parts.append(f"{key}={_serialize_for_scan(obj[key])}")
        return "{" + ",".join(parts) + "}"
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(_serialize_for_scan(v) for v in obj) + "]"
    return str(obj)


def derive_trust_level(
    source: str,
    classification: str,
    record_count: int,
) -> str:
    """Derive the trust level from source, classification, and record count.

    Rules (fail-closed):
        - BLOCKED:  invalid_fake_db or unknown classification
        - HIGH:     valid_db_backed AND surrealdb-local AND records > 0
        - MEDIUM:   valid_db_backed (any source) OR surrealdb-local with records
        - LOW:      everything else (empty results, in_memory, unavailable, etc.)
    """
    if classification not in ALLOWED_TRUST_CLASSIFICATIONS:
        return "BLOCKED"
    if classification == "invalid_fake_db":
        return "BLOCKED"

    if (
        classification == "valid_db_backed"
        and source == "surrealdb-local"
        and record_count > 0
    ):
        return "HIGH"
    if classification == "valid_db_backed":
        return "MEDIUM"
    if source == "surrealdb-local" and record_count > 0:
        return "MEDIUM"

    return "LOW"


def derive_freshness_signal(age_seconds: int, stale_threshold_seconds: int) -> str:
    """Derive a human-readable freshness label."""
    if age_seconds < 0:
        return "unknown"
    ratio = age_seconds / max(stale_threshold_seconds, 1)
    if ratio <= 0.25:
        return "fresh"
    if ratio <= 1.0:
        return "aging"
    return "stale"


def validate_db_record_evidence_response(
    response: Mapping[str, Any],
) -> list[str]:
    """Validate that *response* conforms to the DB-Record Evidence Response Schema.

    Returns a list of violation messages. An empty list means compliant.
    """
    violations: list[str] = []

    if not isinstance(response, Mapping):
        return ["response must be a mapping"]

    serialized = _serialize_for_scan(response)
    if _has_secret_leak(serialized):
        violations.append("response contains forbidden secret-like substrings")

    version = _as_str(response.get("schema_version") or "")
    if version != SCHEMA_VERSION:
        violations.append(f"schema_version must be {SCHEMA_VERSION!r}, got {version!r}")

    status = _as_str(response.get("status") or "")
    if status not in ALLOWED_STATUSES:
        violations.append(
            f"status must be one of {sorted(ALLOWED_STATUSES)}, got {status!r}"
        )
        return violations

    if status == "ok":
        violations.extend(_validate_ok_response(response))
    elif status == "error":
        violations.extend(_validate_error_response(response))

    limitations = response.get("limitations")
    if isinstance(limitations, list):
        limits_text = " ".join(str(item) for item in limitations)
        for std_lim in STANDARD_LIMITATIONS:
            if std_lim not in limits_text:
                violations.append(f"missing standard limitation: {std_lim}")
    else:
        violations.append("limitations must be a list of strings")

    no_go = response.get("no_echtgeld_go")
    if no_go is not True:
        violations.append(
            "no_echtgeld_go must be True; "
            "this response does not authorize live capital or trading actions"
        )

    return violations


def _validate_ok_response(response: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []

    for field in REQUIRED_OK_FIELDS:
        if field not in response:
            violations.append(f"missing required field: {field}")

    tool = _as_str(response.get("tool") or "")
    if not tool:
        violations.append("tool must be a non-empty string")
    elif tool not in ALLOWED_TOOLS:
        violations.append(f"tool {tool!r} not in allowed set: {sorted(ALLOWED_TOOLS)}")

    source = _as_str(response.get("source") or "")
    if source and source not in ALLOWED_SOURCES:
        violations.append(f"source {source!r} not in {sorted(ALLOWED_SOURCES)}")

    violations.extend(_validate_metadata(response))

    records = response.get("records")
    if not isinstance(records, list):
        violations.append("records must be a list")
    record_count = response.get("record_count")
    if isinstance(records, list) and isinstance(record_count, int):
        if record_count != len(records):
            violations.append(
                f"record_count ({record_count}) must equal len(records) ({len(records)})"
            )
    elif not isinstance(record_count, int):
        violations.append("record_count must be an integer")

    filters = response.get("filters_applied")
    if not isinstance(filters, Mapping):
        violations.append("filters_applied must be a mapping")

    violations.extend(
        _validate_trust(
            response, source, isinstance(records, list) and len(records) or 0
        )
    )
    violations.extend(_validate_freshness(response))

    return violations


def _validate_error_response(response: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []

    for field in REQUIRED_ERROR_FIELDS:
        if field not in response:
            violations.append(f"missing required field: {field}")

    error = response.get("error")
    if isinstance(error, Mapping):
        code = _as_str(error.get("code") or "")
        message = _as_str(error.get("message") or "")
        if not code:
            violations.append("error.code must be a non-empty string")
        if not message:
            violations.append("error.message must be a non-empty string")
    else:
        violations.append("error must be a mapping with code and message")

    violations.extend(_validate_metadata(response))
    return violations


def _validate_metadata(response: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    metadata = response.get("metadata")
    if not isinstance(metadata, Mapping):
        violations.append("metadata must be a mapping")
        return violations

    for field in REQUIRED_METADATA_FIELDS:
        if field not in metadata:
            violations.append(f"metadata missing required field: {field}")

    read_only = metadata.get("read_only")
    if read_only is not True:
        violations.append("metadata.read_only must be True")

    return violations


def _validate_trust(
    response: Mapping[str, Any],
    source: str,
    record_count: int,
) -> list[str]:
    violations: list[str] = []
    trust = response.get("trust")
    if not isinstance(trust, Mapping):
        violations.append("trust must be a mapping")
        return violations

    for field in REQUIRED_TRUST_FIELDS:
        if field not in trust:
            violations.append(f"trust missing required field: {field}")

    level = _as_str(trust.get("level") or "")
    if level and level not in ALLOWED_TRUST_LEVELS:
        violations.append(
            f"trust.level {level!r} not in {sorted(ALLOWED_TRUST_LEVELS)}"
        )

    classification = _as_str(trust.get("classification") or "")
    if classification and classification not in ALLOWED_TRUST_CLASSIFICATIONS:
        violations.append(
            f"trust.classification {classification!r} not in "
            f"{sorted(ALLOWED_TRUST_CLASSIFICATIONS)}"
        )

    confidence = trust.get("confidence")
    if confidence is not None:
        if not isinstance(confidence, (int, float)):
            violations.append("trust.confidence must be a numeric value")
        elif not (0.0 <= float(confidence) <= 1.0):
            violations.append(
                f"trust.confidence must be between 0.0 and 1.0, got {confidence}"
            )

    src_priority = _as_str(trust.get("source_priority") or "")
    if src_priority and src_priority not in ALLOWED_SOURCE_PRIORITIES:
        violations.append(
            f"trust.source_priority {src_priority!r} not in "
            f"{sorted(ALLOWED_SOURCE_PRIORITIES)}"
        )

    # Cross-validate: trust level should be consistent with source + classification
    if level and classification and source:
        expected_level = derive_trust_level(source, classification, record_count)
        if level != expected_level:
            violations.append(
                f"trust.level {level!r} inconsistent: expected {expected_level!r} "
                f"for source={source!r} classification={classification!r} record_count={record_count}"
            )

    return violations


def _validate_freshness(response: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    freshness = response.get("freshness")
    if not isinstance(freshness, Mapping):
        violations.append("freshness must be a mapping")
        return violations

    for field in REQUIRED_FRESHNESS_FIELDS:
        if field not in freshness:
            violations.append(f"freshness missing required field: {field}")

    is_stale = freshness.get("is_stale")
    if is_stale is not None and not isinstance(is_stale, bool):
        violations.append("freshness.is_stale must be a boolean")

    age = freshness.get("age_seconds")
    if isinstance(age, (int, float)) and age < 0:
        violations.append("freshness.age_seconds must be >= 0")

    threshold = freshness.get("stale_threshold_seconds")
    if isinstance(threshold, (int, float)) and threshold <= 0:
        violations.append("freshness.stale_threshold_seconds must be > 0")

    signal = _as_str(freshness.get("freshness_signal") or "")
    if signal and signal not in ALLOWED_FRESHNESS_SIGNALS:
        violations.append(
            f"freshness.freshness_signal {signal!r} not in "
            f"{sorted(ALLOWED_FRESHNESS_SIGNALS)}"
        )

    # Cross-validate: is_stale should match freshness_signal
    if isinstance(is_stale, bool) and signal:
        if is_stale and signal == "fresh":
            violations.append(
                "freshness.is_stale=True inconsistent with freshness_signal='fresh'"
            )
        if not is_stale and signal == "stale":
            violations.append(
                "freshness.is_stale=False inconsistent with freshness_signal='stale'"
            )

    return violations


def build_ok_response(
    tool: str,
    source: str,
    records: list[dict[str, Any]],
    *,
    query_time_ms: int = 0,
    filters_applied: dict[str, Any] | None = None,
    trust_level: str | None = None,
    trust_classification: str | None = None,
    trust_confidence: float | None = None,
    trust_source_priority: str | None = None,
    age_seconds: int = 0,
    stale_threshold_seconds: int = 3600,
    extra_limitations: list[str] | None = None,
) -> dict[str, Any]:
    """Build a schema-compliant ok response envelope.

    Source and record count drive automatic trust derivation when explicit
    trust parameters are not provided.
    """
    if source not in ALLOWED_SOURCES:
        source = "in_memory"

    record_count = len(records)
    classification = trust_classification or (
        "valid_db_backed"
        if source == "surrealdb-local" and record_count > 0
        else (
            "partial"
            if source in ("surrealdb-local", "surrealdb-local-unavailable")
            else "in_memory_fixture"
        )
    )
    level = trust_level or derive_trust_level(source, classification, record_count)
    confidence = (
        trust_confidence
        if trust_confidence is not None
        else (
            0.9
            if source == "surrealdb-local" and record_count > 0
            else 0.5 if source == "surrealdb-local" else 0.3
        )
    )
    src_priority = trust_source_priority or (
        "surrealdb_context" if source == "surrealdb-local" else "repo_files"
    )
    freshness_signal = derive_freshness_signal(age_seconds, stale_threshold_seconds)

    limitations = list(STANDARD_LIMITATIONS)
    if extra_limitations:
        limitations.extend(extra_limitations)

    return {
        "schema_version": SCHEMA_VERSION,
        "tool": tool,
        "status": "ok",
        "source": source,
        "metadata": {
            "source": source,
            "read_only": True,
            "query_time_ms": query_time_ms,
        },
        "record_count": record_count,
        "records": records,
        "filters_applied": filters_applied or {},
        "trust": {
            "level": level,
            "classification": classification,
            "confidence": confidence,
            "source_priority": src_priority,
        },
        "freshness": {
            "age_seconds": age_seconds,
            "stale_threshold_seconds": stale_threshold_seconds,
            "is_stale": freshness_signal == "stale",
            "freshness_signal": freshness_signal,
        },
        "limitations": limitations,
        "no_echtgeld_go": True,
    }


def build_error_response(
    tool: str,
    *,
    code: str,
    message: str,
    source: str = "in_memory",
) -> dict[str, Any]:
    """Build a schema-compliant error response envelope."""
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": tool,
        "status": "error",
        "source": source,
        "error": {
            "code": code,
            "message": message,
        },
        "metadata": {
            "source": "in_memory",
            "read_only": True,
            "query_time_ms": 0,
        },
        "limitations": list(STANDARD_LIMITATIONS),
        "no_echtgeld_go": True,
    }


def enforce_response_contract(response: Mapping[str, Any]) -> None:
    """Raise ``DbRecordEvidenceResponseError`` if *response* violates the schema."""
    violations = validate_db_record_evidence_response(response)
    if violations:
        raise DbRecordEvidenceResponseError(
            f"DB-Record Evidence Response Schema violations: {'; '.join(violations)}"
        )
