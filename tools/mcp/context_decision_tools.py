from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from tools.surrealdb.decision_history_query import (
    DecisionHistoryQueryError,
    DecisionHistoryQueryRequest,
    query_decision_history_v1,
)
from tools.surrealdb.decision_replay_builder import (
    DecisionReplayError,
    DecisionReplayRequest,
    build_decision_replay_v1,
)
from tools.surrealdb.context_query import ContextQueryError
from tools.mcp.surrealdb_adapter_factory import (
    build_adapter_from_params,
    derive_guarded_source_label,
)

TOOL_CDB_CONTEXT_DECISION_HISTORY = "cdb_context_decision_history"
TOOL_CDB_CONTEXT_DECISION_REPLAY = "cdb_context_decision_replay"

# ── DB query helpers (Issue #2461: filter-pushdown) ────────────────────────────

_SURQL_SAFE_RE = re.compile(r"^[a-zA-Z0-9/_.@:#+ \-]+$")


def _safe_surql_str(value: str | None) -> str | None:
    """Return *value* if safe for SurrealQL string embedding, else None."""
    if not value:
        return None
    text = value.strip()
    return text if (text and _SURQL_SAFE_RE.match(text)) else None


def _build_decision_event_where(params: Mapping[str, Any]) -> str:
    """Build a SurrealQL WHERE clause for the decision_event table."""

    def _opt(key: str) -> str | None:
        v = params.get(key)
        if v is None:
            return None
        return _safe_surql_str(str(v).strip() or None)

    mode_raw = params.get("mode")
    mode = str(mode_raw).strip() if mode_raw is not None else ""
    if mode == "by_scope":
        val = _opt("scope")
        if val:
            return f"WHERE scope = '{val}'"
    elif mode == "by_status":
        val = _opt("status")
        if val:
            return f"WHERE status = '{val}'"
    elif mode == "by_decision_id":
        val = _opt("decision_id")
        if val:
            return f"WHERE decision_id = '{val}'"
    # Replay mode aliases: decision_replay sends replay_* prefixed mode names.
    elif mode == "replay_by_scope":
        val = _opt("scope")
        if val:
            return f"WHERE scope = '{val}'"
    elif mode == "replay_by_status":
        val = _opt("status")
        if val:
            return f"WHERE status = '{val}'"
    elif mode == "replay_by_decision_id":
        val = _opt("decision_id")
        if val:
            return f"WHERE decision_id = '{val}'"
    elif mode == "replay_by_artifact":
        # decision_event schema uses affected_artifacts for artifact references
        val = _opt("artifact")
        if val:
            return f"WHERE affected_artifacts CONTAINS '{val}'"
    # replay_current_for_topic / replay_superseded_for_topic: no direct topic
    # field in the decision_event DB schema; in-memory filter handles them.
    return ""


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
            message=f"expected tool {expected_tool}, got {tool!r}",
        )

    parameters = _as_mapping(request.get("parameters")) or request
    return _ToolRequest(tool=expected_tool, parameters=parameters)


def _metadata(*, source: str, query_time_ms: int = 0) -> dict[str, Any]:
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
        "metadata": _metadata(source="in_memory"),
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


def _extract_decision_events(
    parameters: Mapping[str, Any],
) -> Iterable[Mapping[str, Any]] | dict[str, Any]:
    raw = parameters.get("decision_events")
    events = _as_list_of_mappings(raw)
    if events is None:
        return _error_response(
            parameters.get("tool", ""),
            code="missing_decision_events",
            message="decision_events is required (list of objects) for the local-only adapter",
        )
    return events


def handle_cdb_context_decision_history(request: Mapping[str, Any]) -> dict[str, Any]:
    parsed = _parse_tool_request(
        request, expected_tool=TOOL_CDB_CONTEXT_DECISION_HISTORY
    )
    if isinstance(parsed, dict):
        return parsed

    params = parsed.parameters

    # Adapter opt-in (Issue #2461): DB-backed mode when adapter_config_path is set.
    if params.get("adapter_config_path") is not None:
        _adapter_result = build_adapter_from_params(
            params, TOOL_CDB_CONTEXT_DECISION_HISTORY
        )
        if isinstance(_adapter_result, dict):
            return _adapter_result
        _adapter, _config = _adapter_result
        _limit = min(
            int(params.get("limit", 200)), _config.max_limit_hard if _config else 200
        )
        _where = _build_decision_event_where(params)
        _suffix = f" {_where}" if _where else ""
        try:
            decision_events: list[Mapping[str, Any]] = _adapter.execute(
                f"SELECT * FROM decision_event{_suffix} LIMIT {_limit}"
            )
        except ContextQueryError as exc:
            return _error_response(
                TOOL_CDB_CONTEXT_DECISION_HISTORY,
                code="adapter_query_error",
                message=str(exc),
            )
        _source = derive_guarded_source_label(params, adapter=_adapter)
    else:
        decision_events = _extract_decision_events(params)
        if isinstance(decision_events, dict):
            decision_events["tool"] = TOOL_CDB_CONTEXT_DECISION_HISTORY
            return decision_events
        _source = derive_guarded_source_label(params)

    mode = params.get("mode")
    try:
        history_request = DecisionHistoryQueryRequest(
            mode=str(mode) if mode is not None else "",
            decision_id=(
                str(params["decision_id"]).strip()
                if params.get("decision_id") is not None
                else None
            ),
            topic=(
                str(params["topic"]).strip()
                if params.get("topic") is not None
                else None
            ),
            scope=(
                str(params["scope"]).strip()
                if params.get("scope") is not None
                else None
            ),
            artifact=(
                str(params["artifact"]).strip()
                if params.get("artifact") is not None
                else None
            ),
            issue=(
                str(params["issue"]).strip()
                if params.get("issue") is not None
                else None
            ),
            status=(
                str(params["status"]).strip()
                if params.get("status") is not None
                else None
            ),
            limit=int(params.get("limit", 200)),
        )
    except Exception as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_DECISION_HISTORY,
            code="invalid_parameters",
            message=str(exc),
        )

    known_evidence_ids_raw = params.get("known_evidence_ids")
    known_claim_ids_raw = params.get("known_claim_ids")
    known_evidence_ids = (
        set(known_evidence_ids_raw)
        if isinstance(known_evidence_ids_raw, list)
        else None
    )
    known_claim_ids = (
        set(known_claim_ids_raw) if isinstance(known_claim_ids_raw, list) else None
    )

    try:
        result = query_decision_history_v1(
            decision_events,
            history_request,
            known_evidence_ids=known_evidence_ids,
            known_claim_ids=known_claim_ids,
        )
    except DecisionHistoryQueryError as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_DECISION_HISTORY,
            code="invalid_request",
            message=str(exc),
            details={"mode": history_request.mode},
        )

    # Ensure explicit non-authorizing semantics for the MCP surface.
    semantics = dict(result.get("approval_semantics") or {})
    semantics.setdefault("no_echtgeld_go", True)
    semantics.setdefault(
        "note",
        "Decision history retrieval only. This output does not grant approval and does not authorize live capital.",
    )
    result["approval_semantics"] = semantics

    return _ok_response(
        TOOL_CDB_CONTEXT_DECISION_HISTORY, result=result, source=_source
    )


def handle_cdb_context_decision_replay(request: Mapping[str, Any]) -> dict[str, Any]:
    parsed = _parse_tool_request(
        request, expected_tool=TOOL_CDB_CONTEXT_DECISION_REPLAY
    )
    if isinstance(parsed, dict):
        return parsed

    params = parsed.parameters

    # Adapter opt-in (Issue #2461)
    if params.get("adapter_config_path") is not None:
        _adapter_result = build_adapter_from_params(
            params, TOOL_CDB_CONTEXT_DECISION_REPLAY
        )
        if isinstance(_adapter_result, dict):
            return _adapter_result
        _adapter, _config = _adapter_result
        _limit = min(
            int(params.get("limit", 50)), _config.max_limit_hard if _config else 50
        )
        _where = _build_decision_event_where(params)
        _suffix = f" {_where}" if _where else ""
        try:
            decision_events: list[Mapping[str, Any]] = _adapter.execute(
                f"SELECT * FROM decision_event{_suffix} LIMIT {_limit}"
            )
        except ContextQueryError as exc:
            return _error_response(
                TOOL_CDB_CONTEXT_DECISION_REPLAY,
                code="adapter_query_error",
                message=str(exc),
            )
        _source = derive_guarded_source_label(params, adapter=_adapter)
    else:
        decision_events = _extract_decision_events(params)
        if isinstance(decision_events, dict):
            decision_events["tool"] = TOOL_CDB_CONTEXT_DECISION_REPLAY
            return decision_events
        _source = derive_guarded_source_label(params)

    mode = params.get("mode")
    try:
        replay_request = DecisionReplayRequest(
            mode=str(mode) if mode is not None else "",
            decision_id=(
                str(params["decision_id"]).strip()
                if params.get("decision_id") is not None
                else None
            ),
            topic=(
                str(params["topic"]).strip()
                if params.get("topic") is not None
                else None
            ),
            scope=(
                str(params["scope"]).strip()
                if params.get("scope") is not None
                else None
            ),
            artifact=(
                str(params["artifact"]).strip()
                if params.get("artifact") is not None
                else None
            ),
            status=(
                str(params["status"]).strip()
                if params.get("status") is not None
                else None
            ),
            date_range=(
                _as_mapping(params.get("date_range"))
                if params.get("date_range") is not None
                else None
            ),
            limit=int(params.get("limit", 50)),
        )
    except Exception as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_DECISION_REPLAY,
            code="invalid_parameters",
            message=str(exc),
        )

    known_evidence_ids_raw = params.get("known_evidence_ids")
    known_claim_ids_raw = params.get("known_claim_ids")
    known_evidence_ids = (
        set(known_evidence_ids_raw)
        if isinstance(known_evidence_ids_raw, list)
        else None
    )
    known_claim_ids = (
        set(known_claim_ids_raw) if isinstance(known_claim_ids_raw, list) else None
    )

    evidence_summaries = _as_mapping(params.get("evidence_summaries"))
    claim_summaries = _as_mapping(params.get("claim_summaries"))

    stop_conditions_raw = params.get("stop_conditions")
    stop_conditions: list[dict[str, Any]] | None = None
    if isinstance(stop_conditions_raw, list) and all(
        isinstance(x, Mapping) for x in stop_conditions_raw
    ):
        stop_conditions = [dict(x) for x in stop_conditions_raw]

    try:
        result = build_decision_replay_v1(
            decision_events,
            replay_request,
            known_evidence_ids=known_evidence_ids,
            known_claim_ids=known_claim_ids,
            evidence_summaries=evidence_summaries,
            claim_summaries=claim_summaries,
            stop_conditions=stop_conditions,
        )
    except DecisionReplayError as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_DECISION_REPLAY,
            code="invalid_request",
            message=str(exc),
            details={"mode": replay_request.mode},
        )

    return _ok_response(TOOL_CDB_CONTEXT_DECISION_REPLAY, result=result, source=_source)
