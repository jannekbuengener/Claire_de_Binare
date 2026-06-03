"""DB-record evidence contract for context/tooling agent claims (Issue #2851).

Read-only validation helpers. No DB access, no MCP mutations, no writes.
LR remains NO-GO. Caller-supplied brain_source/metadata.source is not evidence.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash

SCHEMA_VERSION = "db-record-evidence-contract/v1"

# Must stay aligned with tools.surrealdb.context_live_invocation_harness.PASS_WITH_LIMITS_ERROR_CODES
ACCEPTED_LIMITATION_CODES = frozenset(
    {
        "missing_evidence_records",
        "missing_claim_records",
        "missing_memory_records",
        "missing_decision_events",
        "missing_records",
        "missing_bundle",
    }
)

CALLER_ONLY_EVIDENCE_KEYS = frozenset(
    {
        "brain_source",
        "brain_status",
        "metadata_source",
        "metadata.source",
        "adapter_status",
        "caller_brain_source",
        "caller_metadata_source",
    }
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

REQUIRED_CLAIM_FIELDS = (
    "claim_id",
    "claim_type",
    "claim_text_or_summary",
    "producer_tool",
    "tool_invocation_id_or_hash",
    "query_or_lookup_fingerprint",
    "record_source",
    "record_ids",
    "record_hashes_or_content_fingerprints",
    "record_timestamps_or_freshness_signal",
    "repo_crosscheck",
    "source_priority",
    "trust_classification",
    "limitations",
    "redaction_summary",
    "determinism_hash",
)

ALLOWED_RECORD_SOURCES = frozenset(
    {
        "surrealdb-local",
        "surrealdb-local-unavailable",
        "in_memory",
        "repo-only",
    }
)

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

ALLOWED_SOURCE_PRIORITIES = frozenset(
    {
        "live_github",
        "repo_files",
        "surrealdb_context",
        "ledger_snapshots",
        "fallback",
    }
)

HASH_EXCLUDED_FIELDS = frozenset(
    {
        "determinism_hash",
        "record_timestamps_or_freshness_signal",
    }
)

_SECRET_RE = re.compile(
    "|".join(re.escape(s) for s in sorted(SECRET_SUBSTRINGS, key=len, reverse=True)),
    re.IGNORECASE,
)


class DbRecordEvidenceContractError(ValueError):
    """Raised when a claim object cannot be interpreted."""


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                out.append(text)
        return out
    text = str(value).strip()
    return [text] if text else []


def _claim_has_secret_leak(text: str) -> bool:
    return bool(_SECRET_RE.search(text))


def _serialize_claim_fragment(obj: Any) -> str:
    if isinstance(obj, Mapping):
        parts = []
        for key in sorted(obj.keys()):
            parts.append(f"{key}={_serialize_claim_fragment(obj[key])}")
        return "{" + ",".join(parts) + "}"
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(_serialize_claim_fragment(v) for v in obj) + "]"
    return str(obj)


def _has_nonempty_record_proof(claim: Mapping[str, Any]) -> bool:
    return bool(_as_str_list(claim.get("record_ids"))) or bool(
        _as_str_list(claim.get("record_hashes_or_content_fingerprints"))
    )


def _has_tool_query_proof(claim: Mapping[str, Any]) -> bool:
    tool = str(claim.get("producer_tool") or "").strip()
    query = str(claim.get("query_or_lookup_fingerprint") or "").strip()
    invocation = str(claim.get("tool_invocation_id_or_hash") or "").strip()
    return bool(tool and (query or invocation))


def _repo_crosscheck_present(claim: Mapping[str, Any]) -> bool:
    crosscheck = claim.get("repo_crosscheck")
    if isinstance(crosscheck, str) and crosscheck.strip():
        return True
    if isinstance(crosscheck, Mapping):
        path = str(crosscheck.get("path") or crosscheck.get("file") or "").strip()
        symbol = str(crosscheck.get("symbol") or "").strip()
        commit = str(crosscheck.get("commit") or crosscheck.get("sha") or "").strip()
        return bool(path or symbol or commit)
    if isinstance(crosscheck, list) and crosscheck:
        return True
    return False


def _caller_only_evidence_present(claim: Mapping[str, Any]) -> bool:
    for key in CALLER_ONLY_EVIDENCE_KEYS:
        if key in claim and claim.get(key) not in (None, "", [], {}):
            return True
    nested = claim.get("caller_evidence")
    if isinstance(nested, Mapping) and nested:
        return True
    return False


def hash_payload_for_determinism(claim: Mapping[str, Any]) -> dict[str, Any]:
    """Build the stable subset used for determinism_hash (wall-clock excluded)."""
    payload = {k: v for k, v in claim.items() if k not in HASH_EXCLUDED_FIELDS}
    version = claim.get("schema_version")
    if version is None:
        payload["schema_version"] = SCHEMA_VERSION
    return payload


def compute_determinism_hash(claim: Mapping[str, Any]) -> str:
    """Deterministic SHA-256 over canonical JSON of the stable claim subset."""
    return canonical_hash(hash_payload_for_determinism(claim))


def redact_for_summary(claim: Mapping[str, Any]) -> dict[str, Any]:
    """Return a redacted copy safe for logs and redaction_summary derivation."""

    def _redact_value(value: Any) -> Any:
        if isinstance(value, str):
            if _claim_has_secret_leak(value):
                return "[REDACTED]"
            return value
        if isinstance(value, Mapping):
            return {k: _redact_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_redact_value(v) for v in value]
        return value

    return _redact_value(dict(claim))


def classify_trust(claim: Mapping[str, Any]) -> str:
    """Classify trust outcome for a claim mapping (best-effort, after field checks)."""
    declared = str(claim.get("trust_classification") or "").strip()
    if declared in ALLOWED_TRUST_CLASSIFICATIONS:
        # Honor explicit invalid/limitation classifications when consistent.
        if declared == "invalid_fake_db":
            return declared
        if declared == "accepted_limitation":
            return declared

    record_source = str(claim.get("record_source") or "").strip()
    limitations = _as_str_list(claim.get("limitations"))

    for item in limitations:
        for code in ACCEPTED_LIMITATION_CODES:
            if code in item:
                return "accepted_limitation"

    if _caller_only_evidence_present(claim) and not _has_nonempty_record_proof(claim):
        if record_source == "surrealdb-local":
            return "invalid_fake_db"

    if record_source == "surrealdb-local-unavailable":
        return "partial"

    if record_source == "repo-only":
        return "repo_only"

    if record_source == "in_memory":
        return "in_memory_fixture"

    if record_source == "surrealdb-local":
        if (
            _has_tool_query_proof(claim)
            and _has_nonempty_record_proof(claim)
            and not _caller_only_evidence_present(claim)
        ):
            return "valid_db_backed"
        if _caller_only_evidence_present(claim):
            return "invalid_fake_db"
        return "partial"

    if declared in ALLOWED_TRUST_CLASSIFICATIONS:
        return declared
    return "partial"


def validate_db_record_evidence_claim(claim: Mapping[str, Any]) -> list[str]:
    """Return violation messages; empty list means contract-compliant."""
    violations: list[str] = []

    if not isinstance(claim, Mapping):
        return ["claim must be a mapping"]

    for field in REQUIRED_CLAIM_FIELDS:
        if field not in claim:
            violations.append(f"missing required field: {field}")

    version = claim.get("schema_version")
    if version is not None and version != SCHEMA_VERSION:
        violations.append(
            f"schema_version must be {SCHEMA_VERSION!r} or omitted, got {version!r}"
        )

    serialized = _serialize_claim_fragment(claim)
    if _claim_has_secret_leak(serialized):
        violations.append("claim contains forbidden secret-like substrings")

    record_source = str(claim.get("record_source") or "").strip()
    if record_source and record_source not in ALLOWED_RECORD_SOURCES:
        violations.append(
            f"record_source {record_source!r} not in {sorted(ALLOWED_RECORD_SOURCES)}"
        )

    trust = str(claim.get("trust_classification") or "").strip()
    if trust and trust not in ALLOWED_TRUST_CLASSIFICATIONS:
        violations.append(
            f"trust_classification {trust!r} not in "
            f"{sorted(ALLOWED_TRUST_CLASSIFICATIONS)}"
        )

    priority = str(claim.get("source_priority") or "").strip()
    if priority and priority not in ALLOWED_SOURCE_PRIORITIES:
        violations.append(
            f"source_priority {priority!r} not in {sorted(ALLOWED_SOURCE_PRIORITIES)}"
        )

    expected_hash = str(claim.get("determinism_hash") or "").strip()
    if expected_hash:
        actual = compute_determinism_hash(claim)
        if expected_hash != actual:
            violations.append(
                "determinism_hash mismatch: expected stable canonical hash "
                f"(got {expected_hash[:12]}..., expected {actual[:12]}...)"
            )

    classified = classify_trust(claim)
    if trust and classified != trust:
        violations.append(
            f"trust_classification {trust!r} inconsistent with derived {classified!r}"
        )

    if classified == "valid_db_backed":
        if record_source != "surrealdb-local":
            violations.append("valid_db_backed requires record_source=surrealdb-local")
        if not _has_tool_query_proof(claim):
            violations.append(
                "valid_db_backed requires producer_tool and "
                "query_or_lookup_fingerprint or tool_invocation_id_or_hash"
            )
        if not _has_nonempty_record_proof(claim):
            violations.append(
                "valid_db_backed requires non-empty record_ids or "
                "record_hashes_or_content_fingerprints"
            )
        if _caller_only_evidence_present(claim):
            violations.append(
                "valid_db_backed cannot rely on caller-only evidence keys"
            )

    if classified == "repo_only":
        if not _repo_crosscheck_present(claim):
            violations.append(
                "repo_only requires repo_crosscheck path/symbol/commit or text"
            )
        if _has_nonempty_record_proof(claim) and record_source == "surrealdb-local":
            violations.append("repo_only cannot assert surrealdb-local record proof")

    if classified == "accepted_limitation":
        if record_source == "surrealdb-local" and _has_nonempty_record_proof(claim):
            violations.append(
                "accepted_limitation cannot present as verified DB-backed"
            )
        has_limit_code = any(
            any(code in lim for code in ACCEPTED_LIMITATION_CODES)
            for lim in _as_str_list(claim.get("limitations"))
        )
        if not has_limit_code:
            violations.append(
                "accepted_limitation requires a limitation referencing "
                f"one of {sorted(ACCEPTED_LIMITATION_CODES)}"
            )

    if classified == "invalid_fake_db":
        if not _caller_only_evidence_present(claim):
            violations.append(
                "invalid_fake_db should document caller-only evidence in claim"
            )

    redaction = str(claim.get("redaction_summary") or "")
    if redaction and _claim_has_secret_leak(redaction):
        violations.append("redaction_summary must not contain raw secret-like values")

    return violations


def build_example_claim(**overrides: Any) -> dict[str, Any]:
    """Helper for tests: minimal valid repo-only claim with deterministic hash."""
    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "claim_id": "claim-example-001",
        "claim_type": "context_tooling_benchmark",
        "claim_text_or_summary": "Harness minimal profile documents fail-closed record paths.",
        "producer_tool": "context_live_invocation_harness",
        "tool_invocation_id_or_hash": "inv-minimal-cdb_context_evidence_resolve",
        "query_or_lookup_fingerprint": "bridge:cdb_context_evidence_resolve:minimal",
        "record_source": "repo-only",
        "record_ids": [],
        "record_hashes_or_content_fingerprints": [],
        "record_timestamps_or_freshness_signal": "not_applicable",
        "repo_crosscheck": {
            "path": "docs/evidence/context_tooling/CDB_PASS_WITH_LIMITS_RATIFICATION_2026-06-03.md",
            "commit": "71a02158",
        },
        "source_priority": "repo_files",
        "trust_classification": "repo_only",
        "limitations": [
            "brain_source=repo-only; no surrealdb-local record IDs in this benchmark slice",
        ],
        "redaction_summary": "no sensitive values present",
    }
    base.update(overrides)
    base["determinism_hash"] = compute_determinism_hash(base)
    return base
