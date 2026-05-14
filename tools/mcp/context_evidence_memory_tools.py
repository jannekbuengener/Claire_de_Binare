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

import logging
import re

from dataclasses import dataclass
from typing import Any, Mapping

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
from tools.surrealdb.decision_history_query import (
    DecisionHistoryQueryError,
    DecisionHistoryQueryRequest,
    query_decision_history_v1,
)
from tools.surrealdb.context_query import ContextQueryError
from tools.mcp.surrealdb_adapter_factory import (
    adapter_source,
    build_adapter_from_params,
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


def _error_response(
    tool: str, *, code: str, message: str, details: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tool": tool,
        "status": "error",
        "error": {"code": code, "message": message},
        "metadata": _metadata(),
    }
    if details:
        payload["error"]["details"] = dict(details)
    return payload


def _ok_response(
    tool: str, *, result: Mapping[str, Any], source: str = "in_memory"
) -> dict[str, Any]:
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


# ── DB query helpers (Issue #2461: filter-pushdown + schema normalisation) ───

# Strict allow-list for values embedded in SurrealQL WHERE clauses.
# Fail-closed: values with characters outside this set → filter is omitted
# and the full page is returned for in-memory filtering.
_SURQL_SAFE_RE = re.compile(r"^[a-zA-Z0-9/_.@:#+ \-]+$")


def _safe_surql_str(value: str | None) -> str | None:
    """Return *value* if safe for SurrealQL string embedding, else None."""
    if not value:
        return None
    text = value.strip()
    return text if (text and _SURQL_SAFE_RE.match(text)) else None


def _normalize_evidence_ref_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Project SurrealDB evidence_ref schema fields to the lookup-contract names.

    SurrealDB schema  → Wave-14 lookup contract
    ─────────────────────────────────────────────
    validates         → claim_refs
    related_artifacts → artifact_refs
    related_decisions → decision_refs
    source_path (str) → source_refs (list)

    Contract fields already present in the row are preserved as-is so that
    in-memory fixtures with pre-mapped field names pass through unchanged.
    """
    result = dict(row)
    if "claim_refs" not in result:
        result["claim_refs"] = list(result.get("validates") or [])
    if "artifact_refs" not in result:
        result["artifact_refs"] = list(result.get("related_artifacts") or [])
    if "decision_refs" not in result:
        result["decision_refs"] = list(result.get("related_decisions") or [])
    if "source_refs" not in result and result.get("source_path"):
        result["source_refs"] = [result["source_path"]]
    return result


def _normalize_claim_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Ensure claim rows have the fields the resolver contract expects.

    The SurrealDB claim table (context_intelligence_v0.surql) does not define
    ``topic``, ``topics``, ``artifact_refs``, or ``decision_refs``.  This
    function adds empty defaults so the resolver never KeyErrors on absent
    fields.  DB-backed lookups should use ``by_scope``, ``by_claim_id``, or
    ``by_status``; ``by_topic``/``by_artifact``/``by_decision_ref`` modes will
    return empty results for rows loaded from the local DB.
    """
    result = dict(row)
    if "topics" not in result:
        result["topics"] = []
    if "topic" not in result:
        result["topic"] = None
    if "artifact_refs" not in result:
        result["artifact_refs"] = []
    if "decision_refs" not in result:
        result["decision_refs"] = []
    return result


def _normalize_memory_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Project SurrealDB agent_memory schema fields to the memory-reader contract.

    SurrealDB agent_memory schema  → memory reader contract
    ─────────────────────────────────────────────────────────
    created_by (str)  → agent    (str)
    ttl        (int)  → ttl_days (int)   [unit assumed days; only int field present]
    scope      (str)  → agent fallback if created_by is absent

    Resolver-only fields absent from the schema receive empty defaults so that
    ``read_memory_v1`` can operate without KeyErrors.  Modes ``by_topic``,
    ``by_artifact``, and ``by_decision`` will return empty results for rows
    loaded from a local DB that does not populate those fields.
    """
    result = dict(row)
    if "agent" not in result:
        result["agent"] = result.get("created_by") or result.get("scope") or ""
    if "ttl_days" not in result and "ttl" in result:
        result["ttl_days"] = result["ttl"]
    if "topic" not in result:
        result["topic"] = None
    if "topics" not in result:
        result["topics"] = []
    if "artifact_refs" not in result:
        result["artifact_refs"] = []
    if "decision_refs" not in result:
        result["decision_refs"] = []
    return result


def _parse_db_limit(
    params: Mapping[str, Any], tool: str, *, default: int = 200
) -> int | dict[str, Any]:
    """Parse the *limit* parameter, returning a structured error on invalid input.

    The DB-backed handlers compute ``_limit`` before the main ``try`` block, so
    a raw ``int()`` call would raise ``ValueError`` for malformed client input
    instead of returning the fail-closed MCP error payload.  This helper catches
    the conversion error and returns the same ``invalid_parameters`` response
    used by the rest of the MCP surface.
    """
    raw = params.get("limit", default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return _error_response(
            tool,
            code="invalid_parameters",
            message=f"limit must be an integer, got {raw!r}",
        )


def _build_evidence_ref_where(params: Mapping[str, Any]) -> str:
    """Build a SurrealQL WHERE clause for the evidence_ref table.

    Maps lookup-contract mode names to the SurrealDB schema field names.
    Returns an empty string when no safe filter can be constructed;
    the caller falls back to fetching the full page for in-memory filtering.
    """
    mode = _as_str_or_none(params.get("mode")) or "by_artifact"
    if mode == "by_artifact":
        val = _safe_surql_str(_as_str_or_none(params.get("artifact")))
        if val:
            return f"WHERE related_artifacts CONTAINS '{val}'"
    elif mode == "by_claim":
        val = _safe_surql_str(_as_str_or_none(params.get("claim")))
        if val:
            return f"WHERE validates CONTAINS '{val}'"
    elif mode == "by_decision":
        val = _safe_surql_str(_as_str_or_none(params.get("decision")))
        if val:
            return f"WHERE related_decisions CONTAINS '{val}'"
    elif mode == "by_source_path":
        val = _safe_surql_str(_as_str_or_none(params.get("source_path")))
        if val:
            return f"WHERE string::contains(source_path, '{val}')"
    elif mode == "by_evidence_type":
        val = _safe_surql_str(_as_str_or_none(params.get("evidence_type")))
        if val:
            return f"WHERE evidence_type = '{val}'"
    elif mode == "by_confidence":
        raw = params.get("min_confidence")
        if raw is not None:
            try:
                conf = float(raw)
                if 0.0 <= conf <= 1.0:
                    return f"WHERE confidence >= {conf}"
            except (TypeError, ValueError):
                pass
    return ""


def _build_claim_where(params: Mapping[str, Any]) -> str:
    """Build a SurrealQL WHERE clause for the claim table."""
    mode = _as_str_or_none(params.get("mode")) or "by_topic"
    if mode == "by_scope":
        val = _safe_surql_str(_as_str_or_none(params.get("scope")))
        if val:
            return f"WHERE scope = '{val}'"
    elif mode == "by_status":
        val = _safe_surql_str(_as_str_or_none(params.get("status")))
        if val:
            return f"WHERE status = '{val}'"
    elif mode == "by_claim_id":
        val = _safe_surql_str(_as_str_or_none(params.get("claim_id")))
        if val:
            return f"WHERE claim_id = '{val}'"
    elif mode == "by_evidence_ref":
        val = _safe_surql_str(_as_str_or_none(params.get("evidence_ref")))
        if val:
            return f"WHERE evidence_refs CONTAINS '{val}'"
    return ""


def _build_memory_where(params: Mapping[str, Any]) -> str:
    """Build a SurrealQL WHERE clause for the agent_memory table."""
    mode = _as_str_or_none(params.get("mode")) or "by_scope"
    if mode == "by_scope":
        val = _safe_surql_str(_as_str_or_none(params.get("scope")))
        if val:
            return f"WHERE scope = '{val}'"
    elif mode == "by_memory_type":
        val = _safe_surql_str(_as_str_or_none(params.get("memory_type")))
        if val:
            return f"WHERE memory_type = '{val}'"
    return ""


# ── Evidence Resolve ─────────────────────────────────────────────────────────


def handle_cdb_context_evidence_resolve(request: Mapping[str, Any]) -> dict[str, Any]:
    """MCP handler: resolve evidence for artifacts, claims, and decisions.

    Tool: cdb_context_evidence_resolve
    Read-only, fail-closed, no writes.
    """
    parsed = _parse_tool_request(
        request, expected_tool=TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE
    )
    if isinstance(parsed, dict):
        return parsed

    params = parsed.parameters

    # Adapter opt-in (Issue #2461): DB-backed mode when adapter_config_path is set.
    if params.get("adapter_config_path") is not None:
        _adapter_result = build_adapter_from_params(
            params, TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE
        )
        if isinstance(_adapter_result, dict):
            return _adapter_result
        _adapter, _config = _adapter_result
        _limit_raw = _parse_db_limit(params, TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE)
        if isinstance(_limit_raw, dict):
            return _limit_raw
        _limit = min(_limit_raw, _config.max_limit_hard if _config else 200)
        _where = _build_evidence_ref_where(params)
        _suffix = f" {_where}" if _where else ""
        try:
            _raw_rows: list[Mapping[str, Any]] = _adapter.execute(
                f"SELECT * FROM evidence_ref{_suffix} LIMIT {_limit}"
            )
        except ContextQueryError as exc:
            return _error_response(
                TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
                code="adapter_query_error",
                message=str(exc),
            )
        evidence_records: list[Mapping[str, Any]] = [
            _normalize_evidence_ref_row(row) for row in _raw_rows
        ]
        _source = adapter_source(_adapter)
    else:
        evidence_records = _extract_records(
            params, "evidence_records", TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE
        )
        if isinstance(evidence_records, dict):
            return evidence_records
        _source = "in_memory"

    mode = _as_str_or_none(params.get("mode")) or "by_artifact"

    freshness_raw = params.get("freshness_days")
    freshness_days: int | None = None
    if freshness_raw is not None:
        try:
            freshness_days = int(freshness_raw)
        except (TypeError, ValueError):
            logging.getLogger(__name__).debug(
                "Invalid freshness_days value, ignoring", exc_info=True
            )

    min_confidence_raw = params.get("min_confidence")
    min_confidence: float | None = None
    if min_confidence_raw is not None:
        try:
            min_confidence = float(min_confidence_raw)
        except (TypeError, ValueError):
            logging.getLogger(__name__).debug(
                "Invalid min_confidence value, ignoring", exc_info=True
            )

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

    return _ok_response(
        TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE, result=result, source=_source
    )


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

    # Adapter opt-in (Issue #2461)
    if params.get("adapter_config_path") is not None:
        _adapter_result = build_adapter_from_params(
            params, TOOL_CDB_CONTEXT_CLAIM_RESOLVE
        )
        if isinstance(_adapter_result, dict):
            return _adapter_result
        _adapter, _config = _adapter_result
        _limit_raw = _parse_db_limit(params, TOOL_CDB_CONTEXT_CLAIM_RESOLVE)
        if isinstance(_limit_raw, dict):
            return _limit_raw
        _limit = min(_limit_raw, _config.max_limit_hard if _config else 200)
        _where = _build_claim_where(params)
        _suffix = f" {_where}" if _where else ""
        try:
            _raw_claim_rows: list[Mapping[str, Any]] = _adapter.execute(
                f"SELECT * FROM claim{_suffix} LIMIT {_limit}"
            )
        except ContextQueryError as exc:
            return _error_response(
                TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
                code="adapter_query_error",
                message=str(exc),
            )
        claim_records: list[Mapping[str, Any]] = [
            _normalize_claim_row(row) for row in _raw_claim_rows
        ]
        _source = adapter_source(_adapter)
    else:
        claim_records = _extract_records(
            params, "claim_records", TOOL_CDB_CONTEXT_CLAIM_RESOLVE
        )
        if isinstance(claim_records, dict):
            return claim_records
        _source = "in_memory"

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
    known_evidence_ids = (
        set(known_evidence_ids_raw)
        if isinstance(known_evidence_ids_raw, list)
        else None
    )

    try:
        result = resolve_claims_v1(
            claim_records, claim_request, known_evidence_ids=known_evidence_ids
        )
    except ClaimResolverError as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            code="invalid_request",
            message=str(exc),
        )

    semantics = dict(result.get("approval_semantics") or {})
    semantics["no_echtgeld_go"] = True
    result["approval_semantics"] = semantics

    return _ok_response(TOOL_CDB_CONTEXT_CLAIM_RESOLVE, result=result, source=_source)


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

    # Adapter opt-in (Issue #2461)
    if params.get("adapter_config_path") is not None:
        _adapter_result = build_adapter_from_params(params, TOOL_CDB_CONTEXT_MEMORY_GET)
        if isinstance(_adapter_result, dict):
            return _adapter_result
        _adapter, _config = _adapter_result
        _limit_raw = _parse_db_limit(params, TOOL_CDB_CONTEXT_MEMORY_GET)
        if isinstance(_limit_raw, dict):
            return _limit_raw
        _limit = min(_limit_raw, _config.max_limit_hard if _config else 200)
        _where = _build_memory_where(params)
        _suffix = f" {_where}" if _where else ""
        try:
            memory_records: list[Mapping[str, Any]] = _adapter.execute(
                f"SELECT * FROM agent_memory{_suffix} LIMIT {_limit}"
            )
        except ContextQueryError as exc:
            return _error_response(
                TOOL_CDB_CONTEXT_MEMORY_GET,
                code="adapter_query_error",
                message=str(exc),
            )
        memory_records = [_normalize_memory_row(r) for r in memory_records]
        _source = adapter_source(_adapter)
    else:
        memory_records = _extract_records(
            params, "memory_records", TOOL_CDB_CONTEXT_MEMORY_GET
        )
        if isinstance(memory_records, dict):
            return memory_records
        _source = "in_memory"

    mode = _as_str_or_none(params.get("mode")) or "by_scope"

    freshness_raw = params.get("freshness_days")
    freshness_days: int | None = None
    if freshness_raw is not None:
        try:
            freshness_days = int(freshness_raw)
        except (TypeError, ValueError):
            logging.getLogger(__name__).debug(
                "Invalid freshness_days param, ignoring", exc_info=True
            )

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

    return _ok_response(TOOL_CDB_CONTEXT_MEMORY_GET, result=result, source=_source)


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

    # Adapter opt-in (Issue #2461): fetch all sub-data from local SurrealDB.
    if params.get("adapter_config_path") is not None:
        _adapter_result = build_adapter_from_params(
            params, TOOL_CDB_CONTEXT_TRUST_SUMMARY
        )
        if isinstance(_adapter_result, dict):
            return _adapter_result
        _adapter, _config = _adapter_result
        _limit_raw = _parse_db_limit(params, TOOL_CDB_CONTEXT_TRUST_SUMMARY)
        if isinstance(_limit_raw, dict):
            return _limit_raw
        _limit = min(_limit_raw, _config.max_limit_hard if _config else 200)
        try:
            _ev_raw = _adapter.execute(f"SELECT * FROM evidence_ref LIMIT {_limit}")
            _cl_raw = _adapter.execute(f"SELECT * FROM claim LIMIT {_limit}")
            _mem_raw = _adapter.execute(f"SELECT * FROM agent_memory LIMIT {_limit}")
            _dec_raw = _adapter.execute(f"SELECT * FROM decision_event LIMIT {_limit}")
        except ContextQueryError as exc:
            return _error_response(
                TOOL_CDB_CONTEXT_TRUST_SUMMARY,
                code="adapter_query_error",
                message=str(exc),
            )
        _source = adapter_source(_adapter)
        _topic = _as_str_or_none(params.get("topic"))
        _artifact = _as_str_or_none(params.get("artifact"))
        evidence_result_raw: dict[str, Any] | None = None
        claim_result_raw: dict[str, Any] | None = None
        memory_result_raw: dict[str, Any] | None = None
        decision_result_raw: dict[str, Any] | None = None
        try:
            evidence_result_raw = lookup_evidence_v1(
                [_normalize_evidence_ref_row(r) for r in _ev_raw],
                EvidenceLookupRequest(
                    mode="by_artifact", artifact=_artifact, limit=_limit
                ),
            )
        except EvidenceLookupError as _exc:
            logging.getLogger(__name__).debug(
                "trust_summary: evidence lookup skipped (%s)", _exc
            )  # soft: available sub-results used
        try:
            claim_result_raw = resolve_claims_v1(
                [_normalize_claim_row(r) for r in _cl_raw],
                ClaimResolveRequest(mode="by_topic", topic=_topic, limit=_limit),
            )
        except ClaimResolverError as _exc:
            logging.getLogger(__name__).debug(
                "trust_summary: claim lookup skipped (%s)", _exc
            )  # soft: available sub-results used
        try:
            memory_result_raw = read_memory_v1(
                [_normalize_memory_row(r) for r in _mem_raw],
                MemoryReadRequest(mode="by_scope", scope=scope, limit=_limit),
            )
        except MemoryReadError as _exc:
            logging.getLogger(__name__).debug(
                "trust_summary: memory lookup skipped (%s)", _exc
            )  # soft: available sub-results used
        try:
            decision_result_raw = query_decision_history_v1(
                _dec_raw,
                DecisionHistoryQueryRequest(mode="by_scope", scope=scope, limit=_limit),
            )
        except DecisionHistoryQueryError as _exc:
            logging.getLogger(__name__).debug(
                "trust_summary: decision lookup skipped (%s)", _exc
            )  # soft: available sub-results used
    else:
        _source = "in_memory"
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

    return _ok_response(TOOL_CDB_CONTEXT_TRUST_SUMMARY, result=result, source=_source)
