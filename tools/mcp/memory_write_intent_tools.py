"""MCP dry-run surface for gated memory write intents — #2704 / G3a #2741.

Issue: #2704 — design gated memory write surface (dry-run default)
G3a: #2741 — operation_mode fail-closed scaffold (G2 refusal codes)
Parent: #2606 (Langzeitgedaechtnis / Persistent Agent Memory)

Exposes ``cdb_context_memory_write_intent`` as a read-only MCP tool that
evaluates Human-GO memory write gates only. No DB adapter, no SQL client,
no persistence, no mutation execution.

Guardrails:
    - MUTATION_ALLOWED is always False in this slice.
    - Default path is dry-run gate evaluation via ``evaluate_memory_write_gate``.
    - Non-dry-run ``operation_mode`` values are refused per G2 design (#2739).
    - Mutation flags fail closed with ``mutation_blocked_by_default``.
    - Raw human_go_token must never appear in responses or logs.
    - LR remains NO-GO.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping

from tools.mcp.memory_output_contract import stamp_limitations
from tools.surrealdb.memory_write_gate import (
    MemoryWriteAuthorization,
    evaluate_memory_write_gate,
)

logger = logging.getLogger(__name__)

TOOL_CDB_CONTEXT_MEMORY_WRITE_INTENT = "cdb_context_memory_write_intent"
MUTATION_ALLOWED = False
MCP_PHASE = "1"

_VALID_OPERATION_MODES: frozenset[str] = frozenset(
    {
        "dry_run",
        "audit_persist_local",
        "audit_persist_productive",
        "agent_memory_write",
    }
)

_MUTATION_FLAGS = frozenset(
    {
        "mutation_requested",
        "execute_write",
        "execute",
        "persist",
        "audit_persist_local",
    }
)

_FORBIDDEN_INJECTION_FIELDS = frozenset({"query", "sql", "surql", "statement"})
_FORBIDDEN_SQL_TOKENS = frozenset(
    {"INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"}
)


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    return None


def _error_response(
    *,
    code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tool": TOOL_CDB_CONTEXT_MEMORY_WRITE_INTENT,
        "status": "error",
        "error": {"code": code, "message": message},
        "metadata": {
            "query_time_ms": 0,
            "source": "in_memory",
            "read_only": True,
        },
    }
    if details:
        payload["error"]["details"] = dict(details)
    return payload


def _refused_response(
    *,
    code: str,
    message: str,
    operation_mode_resolved: str,
    gate_status: str,
) -> dict[str, Any]:
    return {
        "tool": TOOL_CDB_CONTEXT_MEMORY_WRITE_INTENT,
        "status": "refused",
        "code": code,
        "message": message,
        "operation_mode_resolved": operation_mode_resolved,
        "gate_status": gate_status,
        "productive_audit_status": "not_activated",
        "mcp_phase": MCP_PHASE,
        "metadata": {
            "query_time_ms": 0,
            "source": "in_memory",
            "read_only": True,
        },
    }


def _ok_response(*, result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "tool": TOOL_CDB_CONTEXT_MEMORY_WRITE_INTENT,
        "status": "ok",
        "result": dict(result),
        "metadata": {
            "query_time_ms": 0,
            "source": "in_memory",
            "read_only": True,
        },
    }


def _parse_authorization(raw: Any) -> MemoryWriteAuthorization | None:
    mapping = _as_mapping(raw)
    if mapping is None:
        return None
    return MemoryWriteAuthorization(
        human_go_token=str(mapping.get("human_go_token") or ""),
        authorized_by=str(mapping.get("authorized_by") or ""),
        authorized_at=str(mapping.get("authorized_at") or ""),
        scope=str(mapping.get("scope") or ""),
        target_issue=str(mapping.get("target_issue") or ""),
        evidence_refs=tuple(str(r) for r in (mapping.get("evidence_refs") or [])),
        operation=str(mapping.get("operation") or "create"),  # type: ignore[arg-type]
    )


def _parse_human_go_tier(raw: Any) -> str | None:
    mapping = _as_mapping(raw)
    if mapping is None:
        return None
    tier = mapping.get("human_go_tier")
    if tier is None:
        return None
    text = str(tier).strip().upper()
    return text or None


def _resolve_operation_mode(
    parameters: Mapping[str, Any],
) -> tuple[str | None, dict[str, Any] | None]:
    raw = parameters.get("operation_mode")
    if raw is None or raw == "":
        return "dry_run", None
    if not isinstance(raw, str):
        return None, _refused_response(
            code="operation_mode_invalid",
            message="operation_mode must be a string",
            operation_mode_resolved=str(raw),
            gate_status="blocked_operation_mode_invalid",
        )
    mode = raw.strip()
    if mode not in _VALID_OPERATION_MODES:
        return None, _refused_response(
            code="operation_mode_invalid",
            message=f"unsupported operation_mode: {mode!r}",
            operation_mode_resolved=mode,
            gate_status="blocked_operation_mode_invalid",
        )
    return mode, None


def _refuse_non_dry_run_mode(
    mode: str,
    authorization_raw: Any,
) -> dict[str, Any] | None:
    if mode == "dry_run":
        return None
    if mode == "audit_persist_local":
        return _refused_response(
            code="local_audit_mcp_not_activated",
            message=(
                "MCP is not authorized for audit_persist_local; use the "
                "operator write path (memory_write_path_v1) instead."
            ),
            operation_mode_resolved=mode,
            gate_status="blocked_local_audit_mcp_not_activated",
        )
    if mode == "audit_persist_productive":
        tier = _parse_human_go_tier(authorization_raw)
        if tier == "HG-L":
            return _refused_response(
                code="hg_p_required",
                message=(
                    "audit_persist_productive requires Human-GO tier HG-P; "
                    "HG-L is insufficient for T3 productive audit."
                ),
                operation_mode_resolved=mode,
                gate_status="blocked_hg_p_required",
            )
        return _refused_response(
            code="productive_audit_not_activated",
            message=(
                "MCP Phase 2 productive audit persist is design-only; "
                "G3b/G3c implementation required."
            ),
            operation_mode_resolved=mode,
            gate_status="blocked_productive_audit_not_implemented",
        )
    if mode == "agent_memory_write":
        return _refused_response(
            code="agent_memory_write_not_activated",
            message=(
                "agent_memory_write (T4) is not activated; G4 scope remains blocked."
            ),
            operation_mode_resolved=mode,
            gate_status="blocked_agent_memory_write_not_activated",
        )
    return None


def _resolve_record(parameters: Mapping[str, Any]) -> Mapping[str, Any] | None:
    record = _as_mapping(parameters.get("record"))
    if record is not None:
        return record
    return _as_mapping(parameters.get("memory_record"))


def _scan_injection_fields(parameters: Mapping[str, Any]) -> str | None:
    for key, value in parameters.items():
        if key not in _FORBIDDEN_INJECTION_FIELDS:
            continue
        if not isinstance(value, str):
            continue
        upper = value.upper()
        for token in _FORBIDDEN_SQL_TOKENS:
            if token in upper:
                return f"{key} contains forbidden SQL keyword {token}"
    return None


def _wrap_gate_envelope(
    envelope: Mapping[str, Any],
    *,
    operation_mode_resolved: str = "dry_run",
) -> dict[str, Any]:
    memory_id = envelope.get("memory_id")
    result: dict[str, Any] = {
        "memory_id": memory_id,
        "gate_status": envelope.get("gate_status"),
        "gate_envelope": dict(envelope),
        "dry_run_only": True,
        "persist_allowed": False,
        "operation_mode_resolved": operation_mode_resolved,
        "productive_audit_status": "not_activated",
        "mcp_phase": MCP_PHASE,
        "approval_semantics": dict(envelope.get("approval_semantics") or {}),
    }
    if memory_id:
        result["matched_memory"] = [
            {"memory_id": str(memory_id), "trust_level": "pending_write"}
        ]
        result["memory_summary"] = {"overall_trust": "pending_write"}
    stamp_limitations(
        result,
        extra=[
            "MCP memory write intent is dry-run gate evaluation only.",
            "mutation_blocked_by_default; no DB write via MCP.",
            "no_persistence",
            "no_mcp_mutation",
            "t3_productive_audit_not_activated",
        ],
    )
    return result


def _response_has_raw_token(payload: Mapping[str, Any]) -> bool:
    serialized = json.dumps(payload, default=str)
    return '"human_go_token"' in serialized


def handle_cdb_context_memory_write_intent(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate a memory write intent through the Human-GO gate (dry-run only).

    Parameters (under ``parameters`` or top-level):
        record / memory_record: memory record dict (required)
        authorization: optional Human-GO authorization block
        operation_mode: dry_run (default) | audit_persist_* | agent_memory_write
        dry_run: ignored; always dry-run in v1 when operation_mode is dry_run
        mutation_requested / execute_write / execute / persist: fail-closed
    """
    if not MUTATION_ALLOWED:
        pass

    tool = request.get("tool")
    if tool is not None and tool != TOOL_CDB_CONTEXT_MEMORY_WRITE_INTENT:
        return _error_response(
            code="invalid_tool",
            message=(
                f"expected tool {TOOL_CDB_CONTEXT_MEMORY_WRITE_INTENT!r}, "
                f"got {tool!r}"
            ),
        )

    parameters = _as_mapping(request.get("parameters")) or request

    operation_mode, mode_error = _resolve_operation_mode(parameters)
    if mode_error is not None:
        return mode_error
    assert operation_mode is not None

    authorization_raw = parameters.get("authorization")
    refusal = _refuse_non_dry_run_mode(operation_mode, authorization_raw)
    if refusal is not None:
        return refusal

    for flag in _MUTATION_FLAGS:
        if parameters.get(flag):
            return _error_response(
                code="mutation_blocked_by_default",
                message=(
                    "Memory write mutation is blocked by default on the MCP "
                    "surface. Dry-run gate evaluation only."
                ),
                details={"flag": flag, "mutations_allowed": MUTATION_ALLOWED},
            )

    injection_issue = _scan_injection_fields(parameters)
    if injection_issue:
        return _error_response(
            code="unsafe_input",
            message=injection_issue,
        )

    record = _resolve_record(parameters)
    if record is None:
        return _error_response(
            code="invalid_parameters",
            message="record (or memory_record) is required (object)",
        )

    authorization = _parse_authorization(authorization_raw)

    envelope = evaluate_memory_write_gate(dict(record), authorization)
    if _response_has_raw_token(envelope):
        logger.error("gate envelope leaked human_go_token; blocking response")
        return _error_response(
            code="internal_error",
            message="gate envelope must not contain raw human_go_token",
        )

    result = _wrap_gate_envelope(envelope, operation_mode_resolved=operation_mode)
    response = _ok_response(result=result)
    if _response_has_raw_token(response):
        return _error_response(
            code="internal_error",
            message="response must not contain raw human_go_token",
        )
    return response
