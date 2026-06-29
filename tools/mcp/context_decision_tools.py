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
    build_decision_replay_v2,
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


def _count_records(records: list[Mapping[str, Any]] | None) -> int:
    return len(records or [])


def _build_replay_brain_evidence_fields(
    *,
    source: str,
    decision_events: list[Mapping[str, Any]],
    evidence_records: list[Mapping[str, Any]] | None,
    claim_records: list[Mapping[str, Any]] | None,
    memory_records: list[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    record_count = (
        len(decision_events)
        + _count_records(evidence_records)
        + _count_records(claim_records)
        + _count_records(memory_records)
    )
    if source == "surrealdb-local":
        return {
            "brain_source": "surrealdb-local",
            "brain_status": "used",
            "context_brain_attempted": True,
            "context_brain_used": True,
            "context_available": True,
            "repo_fallback_used": False,
            "repo_fallback_reason": "none",
            "context_tool_status": "available",
            "context_trust_level": "medium",
            "records_found": record_count,
        }

    if record_count > 0:
        return {
            "brain_source": "in_memory",
            "brain_status": "used",
            "context_brain_attempted": True,
            "context_brain_used": True,
            "context_available": True,
            "repo_fallback_used": False,
            "repo_fallback_reason": "none",
            "context_tool_status": "available",
            "context_trust_level": "medium",
            "records_found": record_count,
        }

    return {
        "brain_source": "repo-only",
        "brain_status": "not-used",
        "context_brain_attempted": True,
        "context_brain_used": False,
        "context_available": False,
        "repo_fallback_used": True,
        "repo_fallback_reason": "insufficient_evidence",
        "context_tool_status": "available",
        "context_trust_level": "none",
        "records_found": "none",
    }


def _build_replay_brain_evidence_block(
    fields: Mapping[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    limitations = [
        "Replay is read-only and non-authorizing.",
        "Repo text, PR narrative, and staged files do not become DB-backed evidence.",
    ]
    if source != "surrealdb-local":
        limitations.append(
            "Decision replay uses repo or in-memory surfaces only; no DB-backed claim "
            "may be inferred from this output."
        )
    return {
        "brain_source": fields["brain_source"],
        "brain_status": fields["brain_status"],
        "context_brain_attempted": fields["context_brain_attempted"],
        "context_brain_used": fields["context_brain_used"],
        "repo_fallback_used": fields["repo_fallback_used"],
        "repo_fallback_reason": fields["repo_fallback_reason"],
        "context_tool_status": fields["context_tool_status"],
        "context_trust_level": fields["context_trust_level"],
        "records_found": fields["records_found"],
        "tools_or_queries": [
            "cdb_context_decision_replay",
            "build_decision_replay_v2",
        ],
        "records_or_results": [
            f"replay_source={source}",
            f"records_found={fields['records_found']}",
        ],
        "repo_crosscheck": [
            "decision_chain",
            "evidence_chain",
            "claim_chain",
        ],
        "impact_on_plan": [
            "Keep replay status proof read-only, evidence-bound, and fail-closed.",
        ],
        "limitations": limitations,
    }


def _normalize_status_claims(raw_claims: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_claims, list):
        return []
    return [dict(item) for item in raw_claims if isinstance(item, Mapping)]


def _build_status_proof_block(
    *,
    status_claims: list[dict[str, Any]],
    brain_fields: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    status_proof_block: dict[str, Any] = {
        "github_live": {
            "issue_state": {
                "proof_status": "missing_live_truth",
                "blocking_findings": [],
                "sources_considered": [],
                "state": "unknown",
            },
            "merge_state": {
                "proof_status": "missing_live_truth",
                "blocking_findings": [],
                "issue_closure_inferred": False,
                "state": "unknown",
            },
        },
        "repo_live": {
            "delivery_state": {
                "proof_status": "repo_only_observation",
                "blocking_findings": [],
                "state": "unknown",
            }
        },
        "ledger": {
            "roadmap_state": {
                "proof_status": "non_db_backed",
                "blocking_findings": [],
                "db_backed_claim": False,
                "state": "unknown",
            }
        },
        "brain": {
            "brain_source": brain_fields["brain_source"],
            "brain_status": brain_fields["brain_status"],
            "context_trust_level": brain_fields["context_trust_level"],
            "records_found": brain_fields["records_found"],
        },
    }
    closure_drift_markers: set[str] = set()

    issue_state = status_proof_block["github_live"]["issue_state"]
    merge_state = status_proof_block["github_live"]["merge_state"]
    delivery_state = status_proof_block["repo_live"]["delivery_state"]
    roadmap_state = status_proof_block["ledger"]["roadmap_state"]

    for claim in status_claims:
        surface = str(claim.get("surface") or "").strip()
        sources = [
            str(source).strip()
            for source in claim.get("sources", [])
            if isinstance(source, str) and source.strip()
        ]

        if surface == "issue_state":
            issue_state["state"] = str(claim.get("state") or "unknown")
            issue_state["sources_considered"] = sources
            if "ledger" in sources:
                issue_state["blocking_findings"].append("ledger_only_issue_state")
            if "pr_body" in sources:
                issue_state["blocking_findings"].append("pr_body_issue_state")
        elif surface == "merge_state":
            merge_state["state"] = str(claim.get("state") or "unknown")
            if merge_state["state"] == "merged" and not bool(
                claim.get("closing_reference_present")
            ):
                merge_state["blocking_findings"].append("missing_closing_reference")
                merge_state["issue_closure_inferred"] = False
        elif surface == "delivery_reconcile":
            delivery_state["state"] = str(claim.get("repo_delivery_state") or "unknown")
            if (
                str(claim.get("github_issue_state") or "").strip().lower() == "open"
                and delivery_state["state"] == "delivered"
            ):
                closure_drift_markers.update({"closure_drift", "partial_delivery"})
        elif surface == "roadmap_state":
            roadmap_state["state"] = str(claim.get("state") or "unknown")
            if "local_staged_files" in sources:
                roadmap_state["blocking_findings"].append(
                    "staged_files_non_db_backed"
                )
            if "pr_narrative" in sources:
                roadmap_state["blocking_findings"].append(
                    "pr_narrative_non_db_backed"
                )

    issue_state["blocking_findings"] = sorted(set(issue_state["blocking_findings"]))
    merge_state["blocking_findings"] = sorted(set(merge_state["blocking_findings"]))
    roadmap_state["blocking_findings"] = sorted(set(roadmap_state["blocking_findings"]))
    return status_proof_block, sorted(closure_drift_markers)


def _build_decision_replay_gate(
    *,
    source: str,
    evidence_records: list[Mapping[str, Any]] | None,
    claim_records: list[Mapping[str, Any]] | None,
    memory_records: list[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    missing_inputs: list[str] = []
    if not evidence_records:
        missing_inputs.append("evidence_records")
    if not claim_records:
        missing_inputs.append("claim_records")
    if source != "surrealdb-local":
        missing_inputs.append("decision_events")
    if not memory_records:
        missing_inputs.append("memory_records")
    return {
        "status": "ready" if not missing_inputs else "degraded",
        "missing_inputs": missing_inputs,
        "non_authorizing": True,
        "db_backed_only_when_recorded": source == "surrealdb-local",
        "notes": [
            "Replay cannot promote repo text, PR body, ledger text, or staged files to DB-backed proof.",
            "Missing record surfaces degrade trust before any status claim can be treated as proven.",
        ],
    }


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
    evidence_records = _as_list_of_mappings(params.get("evidence_records"))
    claim_records = _as_list_of_mappings(params.get("claim_records"))
    memory_records = _as_list_of_mappings(params.get("memory_records"))
    status_claims = _normalize_status_claims(params.get("status_claims"))

    stop_conditions_raw = params.get("stop_conditions")
    stop_conditions: list[dict[str, Any]] | None = None
    if isinstance(stop_conditions_raw, list) and all(
        isinstance(x, Mapping) for x in stop_conditions_raw
    ):
        stop_conditions = [dict(x) for x in stop_conditions_raw]

    try:
        result = build_decision_replay_v2(
            decision_events,
            replay_request,
            known_evidence_ids=known_evidence_ids,
            known_claim_ids=known_claim_ids,
            evidence_summaries=evidence_summaries,
            claim_summaries=claim_summaries,
            evidence_records=evidence_records,
            claim_records=claim_records,
            stop_conditions=stop_conditions,
        )
    except DecisionReplayError as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_DECISION_REPLAY,
            code="invalid_request",
            message=str(exc),
            details={"mode": replay_request.mode},
        )

    brain_evidence_fields = _build_replay_brain_evidence_fields(
        source=_source,
        decision_events=list(decision_events),
        evidence_records=evidence_records,
        claim_records=claim_records,
        memory_records=memory_records,
    )
    status_proof_block, closure_drift_markers = _build_status_proof_block(
        status_claims=status_claims,
        brain_fields=brain_evidence_fields,
    )
    result["brain_evidence_block"] = _build_replay_brain_evidence_block(
        brain_evidence_fields,
        source=_source,
    )
    result["status_proof_block"] = status_proof_block
    result["decision_replay_gate"] = _build_decision_replay_gate(
        source=_source,
        evidence_records=evidence_records,
        claim_records=claim_records,
        memory_records=memory_records,
    )
    result["closure_drift_markers"] = closure_drift_markers
    return _ok_response(TOOL_CDB_CONTEXT_DECISION_REPLAY, result=result, source=_source)
