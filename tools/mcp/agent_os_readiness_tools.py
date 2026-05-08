"""Agent OS Readiness MCP Tool v1 — thin MCP adapter.

Issues:
    #2192 — [SURREALDB][CONTEXT][AGENT-OS-MCP] Implement Agent OS readiness MCP tool
    Parent: #2188 (Wave-20 anchor)
    Epic: #1976

Scope:
    Thin MCP adapter for the Wave-20 Agent OS Readiness Evaluator.
    Bundle-driven, read-only, fail-closed.
    No DB. No network. No writes. No trading console. No runtime control.
    No Live-Go. No Echtgeld-Go.

    Delegates all evaluation logic to evaluate_agent_os_readiness_v1.
"""

from __future__ import annotations

from typing import Any

TOOL_CDB_AGENT_OS_READINESS = "cdb_agent_os_readiness"
SCHEMA_VERSION = "agent-os-readiness-mcp/v1"


def handle_agent_os_readiness(
    bundle: Any = None,
    as_of: str | None = None,
    include_report: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """MCP handler for cdb_agent_os_readiness (Wave-20).

    Evaluates Agent OS readiness from an in-memory context bundle.
    Fail-closed: returns status="error" on any invalid input or evaluator
    failure.  Always returns guardrails.

    Args:
        bundle:         In-memory context bundle (required).  Must be a
                        mapping with at least a ``meta.scope_id`` string.
        as_of:          Optional ISO-8601 UTC timestamp for deterministic
                        output.
        include_report: If True, include a ``report_markdown`` field with
                        the full Markdown readiness report (#2193).
        **kwargs:       Ignored extra parameters (forward-compatibility).

    Returns:
        Dict with ``status``, ``tool``, ``schema_version``, ``readiness_level``,
        ``result``, ``guardrails``, and ``metadata``.
        On error: ``status="error"`` with ``error.code`` and ``error.message``.
    """
    from tools.surrealdb.agent_os_readiness import (
        GUARDRAILS,
        AgentOsReadinessError,
        evaluate_agent_os_readiness_v1,
    )

    _BASE = {
        "tool": TOOL_CDB_AGENT_OS_READINESS,
        "schema_version": SCHEMA_VERSION,
    }

    # --- Input validation (fail-closed) ---
    if bundle is None:
        return {
            **_BASE,
            "status": "error",
            "error": {
                "code": "missing_bundle",
                "message": (
                    "bundle is required. "
                    "Provide an in-memory context bundle mapping."
                ),
            },
            "guardrails": list(GUARDRAILS),
        }

    if not isinstance(bundle, dict):
        return {
            **_BASE,
            "status": "error",
            "error": {
                "code": "invalid_bundle",
                "message": (
                    "bundle must be a dict/mapping "
                    "(got %s)" % type(bundle).__name__
                ),
            },
            "guardrails": list(GUARDRAILS),
        }

    # --- Delegate to evaluator ---
    try:
        result = evaluate_agent_os_readiness_v1(bundle, as_of=as_of)
    except AgentOsReadinessError as exc:
        return {
            **_BASE,
            "status": "error",
            "error": {
                "code": "evaluator_error",
                "message": str(exc),
            },
            "guardrails": list(GUARDRAILS),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            **_BASE,
            "status": "error",
            "error": {
                "code": "internal_error",
                "message": str(exc),
            },
            "guardrails": list(GUARDRAILS),
        }

    # --- Build success response ---
    response: dict[str, Any] = {
        **_BASE,
        "status": "ok",
        "readiness_level": result.readiness_level,
        "result": result.to_dict(),
        "guardrails": list(result.guardrails),
        "metadata": {
            "evaluated_by": "agent_os_readiness/v1",
            "target_scope": result.target_scope,
            "generated_at": result.generated_at,
            "readiness_id": result.readiness_id,
            "blocking_count": len(result.blocking_findings),
            "weak_count": len(result.weak_findings),
            "missing_input_count": len(result.missing_inputs),
            "confidence": round(result.confidence, 4),
        },
    }

    if include_report:
        response["report_markdown"] = result.to_report_markdown()

    return response
