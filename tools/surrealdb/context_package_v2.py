"""Context Package v2 — side-effect-free domain component.

Issues:
    #2798 — [PHASE-2][SURREALDB][SLICE-2] Context Package v2
    Parent: #2778 (Phase-2 epic)
    Epic: #1976

Scope:
    Build a governed agent handoff envelope from in-memory package ingredients.
    Deterministic multi-artifact hashing, redaction, and guardrails.
    No DB access. No SurrealDB SDK. No MCP. No networking. No file writes.

Guardrails:
    - Context Package is orientation, not authorization.
    - LR remains NO-GO; no Live-Go; no Echtgeld-Go.
    - No automatic code or issue action from package output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash, canonical_json_dumps
from core.utils.clock import utcnow

SCHEMA_VERSION = "context-package/v2"

DEFAULT_SOURCE_PRIORITY: tuple[str, ...] = (
    "github_live",
    "repo_live",
    "verified_context_db_mcp_evidence",
    "canonical_governance_files",
    "ledger_files",
    "memory",
)

GUARDRAILS: tuple[str, ...] = (
    "Context Package is orientation, not authorization.",
    "LR remains NO-GO; no Live-Go.",
    "No Echtgeld-Go.",
    "No automatic code or issue action from package output.",
    "No DB-backed claim without tool/query/record evidence.",
)

_SENSITIVE_KEY_RE = re.compile(
    r"(token|secret|password|api[_-]?key|credential|private[_-]?key|auth)",
    re.IGNORECASE,
)

_SECRET_VALUE_RE = re.compile(
    r"(Bearer\s+\S+|sk-[A-Za-z0-9_-]{8,}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)",
    re.IGNORECASE,
)

_TRANSIENT_ARTIFACT_FIELDS = frozenset(
    {
        "generated_at",
        "created_at",
        "updated_at",
        "as_of",
    }
)


class ContextPackageV2Error(ValueError):
    """Raised when package inputs are invalid or unsafe."""


@dataclass(frozen=True)
class ContextPackageV2Request:
    target_scope: str
    artifacts: Sequence[Mapping[str, Any]]
    required_reads: Sequence[Mapping[str, Any]] | None = None
    ranked_context: Mapping[str, Any] | None = None
    evidence_links: Sequence[Mapping[str, Any]] | None = None
    decision_replay_links: Sequence[Mapping[str, Any]] | None = None
    source_priority: Sequence[str] | None = None
    generated_at_or_as_of: str | None = None


def _utc_now_iso() -> str:
    return utcnow().isoformat()


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return str(value).strip() or None


def _is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_RE.search(key))


def _looks_like_secret_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_SECRET_VALUE_RE.search(value.strip()))


def _redact_value(
    key: str,
    value: Any,
    path: str,
    summary: list[dict[str, str]],
) -> Any:
    if _is_sensitive_key(key) or _looks_like_secret_value(value):
        summary.append(
            {
                "path": path,
                "field": key,
                "redaction_type": "sensitive_key"
                if _is_sensitive_key(key)
                else "secret_value_pattern",
            }
        )
        return "[REDACTED]"
    if isinstance(value, dict):
        return _redact_mapping(value, path, summary)
    if isinstance(value, list):
        return [
            _redact_value(key, item, f"{path}[{index}]", summary)
            for index, item in enumerate(value)
        ]
    return value


def _redact_mapping(
    raw: Mapping[str, Any],
    path: str,
    summary: list[dict[str, str]],
) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in raw.items():
        key_text = str(key)
        if key_text.startswith("_"):
            continue
        child_path = f"{path}.{key_text}" if path else key_text
        redacted[key_text] = _redact_value(key_text, value, child_path, summary)
    return redacted


def _artifact_sort_key(artifact: Mapping[str, Any]) -> tuple[str, str, str]:
    artifact_id = _as_str(artifact.get("artifact_id")) or _as_str(artifact.get("id")) or ""
    artifact_type = _as_str(artifact.get("artifact_type")) or _as_str(artifact.get("type")) or ""
    payload = dict(artifact)
    for transient in _TRANSIENT_ARTIFACT_FIELDS:
        payload.pop(transient, None)
    return (artifact_id, artifact_type, canonical_json_dumps(payload))


def _normalize_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    artifact_id = _as_str(artifact.get("artifact_id")) or _as_str(artifact.get("id"))
    artifact_type = _as_str(artifact.get("artifact_type")) or _as_str(artifact.get("type"))
    if not artifact_id:
        raise ContextPackageV2Error("each artifact must include artifact_id or id")
    if not artifact_type:
        raise ContextPackageV2Error(
            f"artifact '{artifact_id}' must include artifact_type or type"
        )
    normalized = dict(artifact)
    normalized["artifact_id"] = artifact_id
    normalized["artifact_type"] = artifact_type
    return normalized


def _artifact_hash_payload(redacted_artifact: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(redacted_artifact)
    for transient in _TRANSIENT_ARTIFACT_FIELDS:
        payload.pop(transient, None)
    for key in list(payload):
        if str(key).startswith("_"):
            payload.pop(key, None)
    return payload


def _stable_required_reads(
    required_reads: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    if not required_reads:
        return []
    normalized = [dict(item) for item in required_reads]
    return sorted(
        normalized,
        key=lambda item: (
            _as_str(item.get("path")) or "",
            _as_str(item.get("priority")) or "",
            canonical_json_dumps(item),
        ),
    )


def _stable_links(links: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if not links:
        return []
    normalized = [dict(item) for item in links]
    return sorted(
        normalized,
        key=lambda item: (
            _as_str(item.get("ref")) or _as_str(item.get("id")) or "",
            canonical_json_dumps(item),
        ),
    )


def _fingerprint(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        return canonical_hash(value)
    if isinstance(value, dict):
        if not value:
            return None
        return canonical_hash(value)
    return canonical_hash(value)


def _stable_redacted_links(
    links: Sequence[Mapping[str, Any]] | None,
    path_prefix: str,
    summary: list[dict[str, str]],
) -> list[dict[str, Any]]:
    stable = _stable_links(links)
    return [
        _redact_mapping(item, f"{path_prefix}[{index}]", summary)
        for index, item in enumerate(stable)
    ]


def _dedupe_redaction_summary(
    summary: list[dict[str, str]],
) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, str]] = []
    for entry in summary:
        key = (
            entry.get("path", ""),
            entry.get("field", ""),
            entry.get("redaction_type", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return sorted(deduped, key=lambda item: (item.get("path", ""), item.get("field", "")))


def build_context_package_v2(request: ContextPackageV2Request) -> dict[str, Any]:
    """Build a Context Package v2 envelope from in-memory ingredients."""
    target_scope = _as_str(request.target_scope)
    if not target_scope:
        raise ContextPackageV2Error("target_scope is required")

    if not request.artifacts:
        raise ContextPackageV2Error("artifacts must be a non-empty sequence")

    source_priority = list(request.source_priority or DEFAULT_SOURCE_PRIORITY)
    generated_at_or_as_of = request.generated_at_or_as_of or _utc_now_iso()

    redaction_summary: list[dict[str, str]] = []
    limitations: list[str] = []

    normalized_artifacts = [_normalize_artifact(item) for item in request.artifacts]
    sorted_artifacts = sorted(normalized_artifacts, key=_artifact_sort_key)

    redacted_artifacts: list[dict[str, Any]] = []
    artifact_hashes: list[str] = []
    for index, artifact in enumerate(sorted_artifacts):
        redacted = _redact_mapping(artifact, f"artifacts[{index}]", redaction_summary)
        redacted_artifacts.append(redacted)
        artifact_hashes.append(canonical_hash(_artifact_hash_payload(redacted)))

    required_reads = _stable_required_reads(request.required_reads)
    evidence_links = _stable_redacted_links(
        request.evidence_links,
        "evidence_links",
        redaction_summary,
    )
    decision_replay_links = _stable_redacted_links(
        request.decision_replay_links,
        "decision_replay_links",
        redaction_summary,
    )

    ranked_context: dict[str, Any] | None = None
    if request.ranked_context is not None:
        ranked_context = _redact_mapping(
            request.ranked_context,
            "ranked_context",
            redaction_summary,
        )
    else:
        limitations.append("ranked_context_not_provided")

    if not decision_replay_links:
        limitations.append("decision_replay_links_not_provided")
    elif all(
        not _as_str(item.get("replay_id")) and not _as_str(item.get("content_hash"))
        for item in decision_replay_links
    ):
        limitations.append("decision_replay_links_refs_only")

    if not evidence_links:
        limitations.append("evidence_links_not_provided")
    elif all(
        item.get("verified") is not True and not _as_str(item.get("content_hash"))
        for item in evidence_links
    ):
        limitations.append("evidence_links_unverified")

    hash_input = {
        "schema_version": SCHEMA_VERSION,
        "target_scope": target_scope,
        "source_priority": source_priority,
        "required_reads": required_reads,
        "artifact_hashes": artifact_hashes,
        "ranked_context_fingerprint": _fingerprint(ranked_context),
        "evidence_links_fingerprint": _fingerprint(evidence_links),
        "decision_replay_links_fingerprint": _fingerprint(decision_replay_links),
    }
    content_hash = canonical_hash(hash_input)
    package_id = f"pkg_{content_hash[:12]}"

    return {
        "schema_version": SCHEMA_VERSION,
        "package_id": package_id,
        "generated_at_or_as_of": generated_at_or_as_of,
        "target_scope": target_scope,
        "source_priority": source_priority,
        "required_reads": required_reads,
        "artifacts": redacted_artifacts,
        "ranked_context": ranked_context,
        "evidence_links": evidence_links,
        "decision_replay_links": decision_replay_links,
        "redaction_summary": _dedupe_redaction_summary(redaction_summary),
        "limitations": sorted(set(limitations)),
        "guardrails": list(GUARDRAILS),
        "determinism": {
            "hash_algorithm": "canonical_sha256",
            "wall_clock_excluded": True,
            "artifact_count": len(redacted_artifacts),
            "content_hash": content_hash,
        },
    }
