"""MCP adapter layer for Wave-14 evidence, claim, and memory tools.

Issues:
    #2123 — Implement evidence resolve MCP tool v1
    #2125 — Implement scoped memory read MCP tool v1
    Parent: #2115 (Wave-14)
    Epic: #1976

Adapts the Wave-14 domain services for the MCP tool surface.
All tools are read-only, fail-closed, and carry explicit no-echtgeld-go semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from tools.surrealdb.evidence_lookup import (
    EvidenceLookupError,
    EvidenceLookupRequest,
    lookup_evidence_v1,
)
from tools.surrealdb.claim_resolver import (
    ClaimResolverError,
    ClaimResolveRequest,
    resolve_claims_v1,
)
from tools.surrealdb.memory_read import (
    MemoryReadError,
    MemoryReadRequest,
    read_memory_v1,
)
from tools.surrealdb.trust_summary import (
    TrustSummaryError,
    TrustSummaryRequest,
    build_trust_summary_v1,
)

TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE = "cdb_context_evidence_resolve"
TOOL_CDB_CONTEXT_CLAIM_RESOLVE = "cdb_context_claim_resolve"
TOOL_CDB_CONTEXT_MEMORY_GET = "cdb_context_memory_get"
TOOL_CDB_CONTEXT_TRUST_SUMMARY = "cdb_context_trust_summary"


@dataclass(frozen=True)
class _ToolRequest:
    tool: str
    parameters: Mapping[str, Any]


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    return None


def _as_list_of_mappings(value: Any) -> list[Mapping[str, Any]] | None:
    if not isinstance(value, list):
        return None
    out: list[Mapping[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            return None
        out.append(item)
    return out


def _as_str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _metadata(*, source: str = "in_memory", query_time_ms: int = 0) -> dict[str, Any]:
    return {
        "query_time_ms": query_time_ms,
        "source": source,
        "read_only": True,
    }


def _error_response(tool: str, *, code: str, message: str, details: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tool": tool,
        "status": "error",
        "error": {"code": code, "message": message},
        "metadata": _metadata(),
    }
    if details:
        payload["error"]["details"] = dict(details)
    return payload


def _ok_response(tool: str, *, result: Mapping[str, Any], source: str = "in_memory") -> dict[str, Any]:
    return {
        "tool": tool,
        "status": "ok",
        "result": dict(result),
        "metadata": _metadata(source=source),
    }


def _parse_tool_request(
    request: Mapping[str, Any],
    *,
    expected_tool: str,
) -> _ToolRequest | dict[str, Any]:
    tool = request.get("tool")
    if tool is None:
        tool = expected_tool
    if tool != expected_tool:
        return _error_response(
            expected_tool,
            code="invalid_tool",
            message=f"expected tool {expected_tool!r}, got {tool!r}",
        )
    parameters = _as_mapping(request.get("parameters")) or request
    return _ToolRequest(tool=expected_tool, parameters=parameters)


def _extract_records(
    parameters: Mapping[str, Any],
    key: str,
    tool: str,
) -> list[Mapping[str, Any]] | dict[str, Any]:
    raw = parameters.get(key)
    records = _as_list_of_mappings(raw)
    if records is None:
        return _error_response(
            tool,
            code=f"missing_{key}",
            message=f"{key} is required (list of objects) for the local-only adapter",
        )
    return records


# ── Evidence Resolve ─────────────────────────────────────────────────────────


def handle_cdb_context_evidence_resolve(request: Mapping[str, Any]) -> dict[str, Any]:
    """MCP handler: resolve evidence for artifacts, claims, and decisions.

    Tool: cdb_context_evidence_resolve
    Read-only, fail-closed, no writes.
    """
    parsed = _parse_tool_request(request, expected_tool=TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE)
    if isinstance(parsed, dict):
        return parsed

    params = parsed.parameters

    evidence_records = _extract_records(params, "evidence_records", TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE)
    if isinstance(evidence_records, dict):
        return evidence_records

    mode = _as_str_or_none(params.get("mode")) or "by_artifact"

    freshness_raw = params.get("freshness_days")
    freshness_days: int | None = None
    if freshness_raw is not None:
        try:
            freshness_days = int(freshness_raw)
        except (TypeError, ValueError):
            pass

    min_confidence_raw = params.get("min_confidence")
    min_confidence: float | None = None
    if min_confidence_raw is not None:
        try:
            min_confidence = float(min_confidence_raw)
        except (TypeError, ValueError):
            pass

    try:
        ev_request = EvidenceLookupRequest(
            mode=mode,
            artifact=_as_str_or_none(params.get("artifact")),
            claim=_as_str_or_none(params.get("claim")),
            decision=_as_str_or_none(params.get("decision")),
            source_path=_as_str_or_none(params.get("source_path")),
            run_id=_as_str_or_none(params.get("run_id")),
            evidence_type=_as_str_or_none(params.get("evidence_type")),
            freshness_days=freshness_days,
            min_confidence=min_confidence,
            limit=int(params.get("limit", 200)),
        )
    except Exception as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            code="invalid_parameters",
            message=str(exc),
        )

    try:
        result = lookup_evidence_v1(evidence_records, ev_request)
    except EvidenceLookupError as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            code="invalid_request",
            message=str(exc),
        )

    semantics = dict(result.get("approval_semantics") or {})
    semantics["no_echtgeld_go"] = True
    result["approval_semantics"] = semantics

    return _ok_response(TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE, result=result)


# ── Claim Resolve ────────────────────────────────────────────────────────────


def handle_cdb_context_claim_resolve(request: Mapping[str, Any]) -> dict[str, Any]:
    """MCP handler: resolve claims including evidence-binding and status.

    Tool: cdb_context_claim_resolve
    Read-only, fail-closed, no writes.
    """
    parsed = _parse_tool_request(request, expected_tool=TOOL_CDB_CONTEXT_CLAIM_RESOLVE)
    if isinstance(parsed, dict):
        return parsed

    params = parsed.parameters

    claim_records = _extract_records(params, "claim_records", TOOL_CDB_CONTEXT_CLAIM_RESOLVE)
    if isinstance(claim_records, dict):
        return claim_records

    mode = _as_str_or_none(params.get("mode")) or "by_topic"

    try:
        claim_request = ClaimResolveRequest(
            mode=mode,
            claim_id=_as_str_or_none(params.get("claim_id")),
            topic=_as_str_or_none(params.get("topic")),
            scope=_as_str_or_none(params.get("scope")),
            status=_as_str_or_none(params.get("status")),
            artifact=_as_str_or_none(params.get("artifact")),
            evidence_ref=_as_str_or_none(params.get("evidence_ref")),
            decision_ref=_as_str_or_none(params.get("decision_ref")),
            limit=int(params.get("limit", 200)),
        )
    except Exception as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            code="invalid_parameters",
            message=str(exc),
        )

    known_evidence_ids_raw = params.get("known_evidence_ids")
    known_evidence_ids = set(known_evidence_ids_raw) if isinstance(known_evidence_ids_raw, list) else None

    try:
        result = resolve_claims_v1(claim_records, claim_request, known_evidence_ids=known_evidence_ids)
    except ClaimResolverError as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            code="invalid_request",
            message=str(exc),
        )

    semantics = dict(result.get("approval_semantics") or {})
    semantics["no_echtgeld_go"] = True
    result["approval_semantics"] = semantics

    return _ok_response(TOOL_CDB_CONTEXT_CLAIM_RESOLVE, result=result)


# ── Memory Get ───────────────────────────────────────────────────────────────


def handle_cdb_context_memory_get(request: Mapping[str, Any]) -> dict[str, Any]:
    """MCP handler: read scoped agent memory.

    Tool: cdb_context_memory_get
    Read-only, fail-closed, no writes. scope is required.
    """
    parsed = _parse_tool_request(request, expected_tool=TOOL_CDB_CONTEXT_MEMORY_GET)
    if isinstance(parsed, dict):
        return parsed

    params = parsed.parameters

    memory_records = _extract_records(params, "memory_records", TOOL_CDB_CONTEXT_MEMORY_GET)
    if isinstance(memory_records, dict):
        return memory_records

    mode = _as_str_or_none(params.get("mode")) or "by_scope"

    freshness_raw = params.get("freshness_days")
    freshness_days: int | None = None
    if freshness_raw is not None:
        try:
            freshness_days = int(freshness_raw)
        except (TypeError, ValueError):
            pass

    try:
        mem_request = MemoryReadRequest(
            mode=mode,
            scope=_as_str_or_none(params.get("scope")),
            topic=_as_str_or_none(params.get("topic")),
            artifact=_as_str_or_none(params.get("artifact")),
            decision=_as_str_or_none(params.get("decision")),
            agent=_as_str_or_none(params.get("agent")),
            freshness_days=freshness_days,
            memory_type=_as_str_or_none(params.get("memory_type")),
            limit=int(params.get("limit", 200)),
        )
    except Exception as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_MEMORY_GET,
            code="invalid_parameters",
            message=str(exc),
        )

    try:
        result = read_memory_v1(memory_records, mem_request)
    except MemoryReadError as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_MEMORY_GET,
            code="invalid_request",
            message=str(exc),
        )

    semantics = dict(result.get("approval_semantics") or {})
    semantics["no_echtgeld_go"] = True
    result["approval_semantics"] = semantics

    return _ok_response(TOOL_CDB_CONTEXT_MEMORY_GET, result=result)


# ── Trust Summary ─────────────────────────────────────────────────────────────


def handle_cdb_context_trust_summary(request: Mapping[str, Any]) -> dict[str, Any]:
    """MCP handler: build context trust summary.

    Tool: cdb_context_trust_summary
    Read-only, fail-closed, no writes.
    """
    parsed = _parse_tool_request(request, expected_tool=TOOL_CDB_CONTEXT_TRUST_SUMMARY)
    if isinstance(parsed, dict):
        return parsed

    params = parsed.parameters

    scope = _as_str_or_none(params.get("scope"))
    if not scope:
        return _error_response(
            TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            code="missing_scope",
            message="scope is required for trust summary",
        )

    evidence_result_raw = _as_mapping(params.get("evidence_result"))
    claim_result_raw = _as_mapping(params.get("claim_result"))
    decision_result_raw = _as_mapping(params.get("decision_result"))
    memory_result_raw = _as_mapping(params.get("memory_result"))

    try:
        trust_request = TrustSummaryRequest(
            scope=scope,
            topic=_as_str_or_none(params.get("topic")),
            artifact=_as_str_or_none(params.get("artifact")),
        )
    except Exception as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            code="invalid_parameters",
            message=str(exc),
        )

    try:
        result = build_trust_summary_v1(
            trust_request,
            evidence_result=evidence_result_raw,
            claim_result=claim_result_raw,
            decision_result=decision_result_raw,
            memory_result=memory_result_raw,
        )
    except TrustSummaryError as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            code="invalid_request",
            message=str(exc),
        )

    semantics = dict(result.get("approval_semantics") or {})
    semantics["no_echtgeld_go"] = True
    result["approval_semantics"] = semantics

    return _ok_response(TOOL_CDB_CONTEXT_TRUST_SUMMARY, result=result)
