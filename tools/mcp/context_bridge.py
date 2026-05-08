"""
Context MCP Bridge - Read-only bridge for Context Intelligence.

This module provides the MCP-compatible bridge to the SurrealDB Context Intelligence System.
All tools are read-only and fail-closed.

Reference:
- Issue: #2093
- Tool Contracts: docs/surrealdb/context-tool-contracts-v0.md
- Parent: #2091 (Wave-12 MCP bridge)
"""

import logging
import json
from copy import deepcopy
from typing import Any, Optional

from tools.mcp.permission_guard import PermissionGuard
from tools.mcp.registry import ContextToolRegistry, ToolDefinition

logger = logging.getLogger(__name__)

CDB_CONTEXT_BRIEFING_MAX_RESPONSE_BYTES = 200_000


def context_search_handler(**kwargs) -> dict[str, Any]:
    """
    Read-only handler for context.search tool.

    Uses mocked NoopQueryAdapter (no live DB/network).
    Fails closed on invalid inputs.
    """
    # Validate required query
    query = kwargs.get("query")
    if not query or not isinstance(query, str) or not query.strip():
        return {
            "tool": "context.search",
            "status": "error",
            "error": {
                "code": "invalid_query",
                "message": "query is required and must be a non-empty string",
            },
        }

    # Validate limit
    limit = kwargs.get("limit", 10)
    if not isinstance(limit, int) or limit <= 0:
        limit = 10

    # Validate filters
    filters = kwargs.get("filters", {})
    if not isinstance(filters, dict):
        filters = {}

    # Use mocked NoopQueryAdapter (no live DB/network)
    from tools.surrealdb.context_query import NoopQueryAdapter

    adapter = NoopQueryAdapter()
    # Mocked execution: returns empty results (override in tests)
    try:
        raw_results = adapter.execute(query)
    except Exception as e:
        logger.error(f"Search query failed: {e}")
        return {
            "tool": "context.search",
            "status": "error",
            "error": {
                "code": "execution_error",
                "message": str(e),
            },
        }

    # Format results to match contract
    results = []
    for item in raw_results[:limit]:
        results.append(
            {
                "id": item.get("id", ""),
                "type": item.get("type", "unknown"),
                "title": item.get("title", ""),
                "summary": item.get("summary", ""),
                "source_ref": item.get("source_ref", ""),
                "confidence": item.get("confidence", 0.0),
                "warnings": item.get("warnings", []),
            }
        )

    return {
        "tool": "context.search",
        "status": "ok",
        "results": results,
        "metadata": {
            "query_time_ms": 0,
            "total_hits": len(results),
        },
    }


def context_trace_handler(**kwargs) -> dict[str, Any]:
    """
    Read-only handler for context.trace tool.

    Traces decision or event lineage through the Context Intelligence system.
    Uses mocked adapter (no live DB/network).
    Fails closed on invalid inputs.
    """
    # Validate required target_id
    target_id = kwargs.get("target_id")
    if not target_id or not isinstance(target_id, str) or not target_id.strip():
        return {
            "tool": "context.trace",
            "status": "error",
            "error": {
                "code": "target_not_found",
                "message": "target_id is required and must be a non-empty string",
            },
        }

    # Validate depth
    depth = kwargs.get("depth", 5)
    if not isinstance(depth, int) or depth <= 0:
        depth = 5
    if depth > 20:
        return {
            "tool": "context.trace",
            "status": "error",
            "error": {
                "code": "depth_exceeded",
                "message": f"depth {depth} exceeds maximum of 20",
            },
        }

    # Mocked trace results (no live DB/network)
    # In production, this would query the context graph
    root = {
        "id": target_id,
        "type": "unknown",
        "title": f"Mock trace target: {target_id}",
    }

    lineage = []
    for i in range(min(depth, 3)):  # Mock up to 3 levels
        lineage.append(
            {
                "id": f"mock_related_{i}",
                "type": "derived",
                "relationship": "related_to",
                "depth": i + 1,
            }
        )

    return {
        "tool": "context.trace",
        "status": "ok",
        "trace": {
            "root": root,
            "lineage": lineage,
        },
    }


def context_explain_source_handler(**kwargs) -> dict[str, Any]:
    """
    Read-only handler for context.explain_source tool.

    Explains provenance of a context source/evidence item.
    Uses mocked responses (no live DB/network).
    Fails closed on invalid inputs.
    """
    # Validate required source_ref
    source_ref = kwargs.get("source_ref")
    if not source_ref or not isinstance(source_ref, str) or not source_ref.strip():
        return {
            "tool": "context.explain_source",
            "status": "error",
            "error": {
                "code": "invalid_source_ref",
                "message": "source_ref is required and must be a non-empty string",
            },
        }

    # Validate include_chain
    include_chain = kwargs.get("include_chain", True)
    if not isinstance(include_chain, bool):
        include_chain = True

    # Mocked explain result (no live DB/network)
    mocked_explanation = {
        "source_ref": source_ref,
        "source_type": "evidence",
        "provenance": {
            "source_path": f"/mock/path/{source_ref}",
            "hash": "mock_hash_123",
            "commit": "mock_commit_456",
            "run_id": "mock_run_789",
            "import_audit_ref": "mock_audit_012",
            "evidence_refs": ["mock_ev_1", "mock_ev_2"],
        },
        "source_refs": [
            {"ref": "mock_audit_012", "type": "import_audit"},
            {"ref": "mock_ev_1", "type": "evidence"},
        ],
        "confidence": 0.9,
        "warnings": [],
        "stale": False,
        "tombstone": False,
    }

    if include_chain:
        mocked_explanation["provenance"]["chain"] = [
            {"level": 1, "ref": "mock_parent_1", "type": "derived"},
            {"level": 2, "ref": "mock_parent_2", "type": "source"},
        ]

    return {
        "tool": "context.explain_source",
        "status": "ok",
        "explanation": mocked_explanation,
        "metadata": {
            "explained_at": "2026-05-03T12:00:00Z",
            "include_chain": include_chain,
        },
    }


def context_package_handler(**kwargs) -> dict[str, Any]:
    """
    Read-only handler for context.package tool.

    Packages context artifacts for handoff between agents or sessions.
    Uses mocked responses (no live DB/network).
    Fails closed on invalid inputs.
    """
    # Validate required artifacts
    artifacts = kwargs.get("artifacts")
    if not artifacts or not isinstance(artifacts, list):
        return {
            "tool": "context.package",
            "status": "error",
            "error": {
                "code": "invalid_artifacts",
                "message": "artifacts is required and must be a non-empty list",
            },
        }

    # Validate format
    format_opt = kwargs.get("format", "json")
    if format_opt not in ("json", "markdown"):
        return {
            "tool": "context.package",
            "status": "error",
            "error": {
                "code": "format_unsupported",
                "message": "format must be 'json' or 'markdown'",
            },
        }

    # Validate include_metadata
    include_metadata = kwargs.get("include_metadata", True)
    if not isinstance(include_metadata, bool):
        include_metadata = True

    # Mocked package result (no live DB/network)
    # Follows #2097 requirements: bounded package, SourceRefs, confidence/freshness/warnings, stop_conditions
    package_items = []
    for artifact_id in artifacts[:10]:  # Limit to 10 items
        package_items.append(
            {
                "id": artifact_id,
                "type": "evidence",
                "summary": f"Mock summary for {artifact_id}",
                "source_refs": [f"src_{artifact_id}_1", f"src_{artifact_id}_2"],
                "confidence": 0.85,
                "freshness": "2026-05-03T00:00:00Z",
            }
        )

    warnings = []
    if len(artifacts) > 10:
        warnings.append("artifacts_limit_exceeded_truncated")
    if len(package_items) == 0:
        warnings.append("empty_package")

    missing_context = []
    if len(artifacts) == 0:
        missing_context.append("no_artifacts_provided")

    package = {
        "request_scope": kwargs.get("scope", "default"),
        "query_summary": f"Package request for {len(artifacts)} artifacts",
        "top_artifacts": package_items[:5],
        "top_docs": [],
        "top_symbols": [],
        "graph_paths": [],
        "source_refs": [
            item
            for sub in [a.get("source_refs", []) for a in package_items]
            for item in sub
        ],
        "confidence_summary": {"average": 0.85, "lowest": 0.8, "highest": 0.9},
        "warnings": warnings,
        "stale_flags": [],
        "missing_context": missing_context,
        "recommended_next_queries": [],
        "stop_conditions": [
            "no_live_go",
            "no_echtgeld_authorization",
            "no_risk_approval",
        ],
    }

    return {
        "tool": "context.package",
        "status": "ok",
        "package": {
            "format": format_opt,
            "items": package_items[:10],
            "created_at": "2026-05-03T12:00:00Z",
            "package_id": f"pkg_{'-'.join(str(a) for a in sorted(artifacts[:10]))}",
            "warnings": warnings,
            "stale_flags": package.get("stale_flags", []),
            "missing_context": missing_context,
            "stop_conditions": package["stop_conditions"],
            "metadata": (
                {
                    "include_metadata": include_metadata,
                    "scope": package["request_scope"],
                    "truncated": len(artifacts) > 10,
                    "total_requested": len(artifacts),
                }
                if include_metadata
                else {}
            ),
        },
    }


def context_self_explain_handler(**kwargs) -> dict[str, Any]:
    """
    Read-only handler for context.self_explain tool.

    Generates a structured self-explanation for governance-relevant conditions
    using the Self-Explanation Builder (#2189). No DB access, no network,
    no MCP live write, no secrets.

    Input:
        question: str (required) — the question or condition to explain
        explanation_type: str (required) — one of 9 supported types
        scope: str (optional) — scope context identifier
        evidence_refs: list[str] (required) — at least one non-empty reference
        reasons: list[str] (optional) — derived from question if empty
        confidence: float (optional) — 0.0–1.0
        recommended_next_reads: list[str] (optional)

    Output conforms to the context.self_explain contract:
        tool, status, explanation, source_refs, evidence_refs,
        graph_path, confidence, recommended_next_reads, guardrails
    """
    from tools.surrealdb.context_self_explanation import (
        SelfExplanationError,
        SelfExplanationInput,
        build_self_explanation,
        supported_explanation_types,
    )

    question = kwargs.get("question")
    if not question or not isinstance(question, str) or not question.strip():
        return {
            "tool": "context.self_explain",
            "status": "error",
            "error": {
                "code": "invalid_question",
                "message": "question is required and must be a non-empty string",
            },
        }

    explanation_type = kwargs.get("explanation_type")
    valid_types = supported_explanation_types()
    if explanation_type not in valid_types:
        return {
            "tool": "context.self_explain",
            "status": "error",
            "error": {
                "code": "invalid_explanation_type",
                "message": (
                    f"explanation_type must be one of {sorted(valid_types)}, "
                    f"got {explanation_type!r}"
                ),
            },
        }

    evidence_refs = kwargs.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or not evidence_refs:
        return {
            "tool": "context.self_explain",
            "status": "error",
            "error": {
                "code": "invalid_evidence_refs",
                "message": (
                    "evidence_refs is required and must be a non-empty list "
                    "of non-empty strings"
                ),
            },
        }

    evidence_refs_clean: list[str] = []
    for r in evidence_refs:
        if not isinstance(r, str) or not r.strip():
            return {
                "tool": "context.self_explain",
                "status": "error",
                "error": {
                    "code": "invalid_evidence_refs",
                    "message": (
                        "evidence_refs is required and must be a non-empty list "
                        "of non-empty strings"
                    ),
                },
            }
        evidence_refs_clean.append(r)

    scope = kwargs.get("scope")
    scope_clean = scope.strip() if isinstance(scope, str) and scope.strip() else None
    if scope_clean:
        summary = f"[{scope_clean}] {question.strip()}"
    else:
        summary = question.strip()

    reasons_raw = kwargs.get("reasons", [])
    if reasons_raw and not isinstance(reasons_raw, list):
        return {
            "tool": "context.self_explain",
            "status": "error",
            "error": {
                "code": "invalid_reasons",
                "message": "reasons must be a list of non-empty strings",
            },
        }
    if not reasons_raw:
        reasons_raw = [f"Selbsterklaerung angefordert fuer: {question.strip()}"]
    reasons_clean: list[str] = []
    for r in reasons_raw:
        if not isinstance(r, str) or not r.strip():
            return {
                "tool": "context.self_explain",
                "status": "error",
                "error": {
                    "code": "invalid_reasons",
                    "message": "reasons must be a list of non-empty strings",
                },
            }
        reasons_clean.append(r)
    reasons = tuple(reasons_clean)

    confidence = kwargs.get("confidence")
    if confidence is not None:
        if isinstance(confidence, bool):
            return {
                "tool": "context.self_explain",
                "status": "error",
                "error": {
                    "code": "invalid_confidence",
                    "message": (
                        "confidence must be a number between 0.0 and 1.0, "
                        f"got bool: {confidence!r}"
                    ),
                },
            }
        if not isinstance(confidence, (int, float)):
            return {
                "tool": "context.self_explain",
                "status": "error",
                "error": {
                    "code": "invalid_confidence",
                    "message": (
                        "confidence must be a number between 0.0 and 1.0, "
                        f"got {type(confidence).__name__}: {confidence!r}"
                    ),
                },
            }
        if not (0.0 <= float(confidence) <= 1.0):
            return {
                "tool": "context.self_explain",
                "status": "error",
                "error": {
                    "code": "invalid_confidence",
                    "message": (
                        f"confidence must be between 0.0 and 1.0, got {confidence}"
                    ),
                },
            }
        confidence_float = float(confidence)
    else:
        confidence_float = None

    recommended_next_reads = kwargs.get("recommended_next_reads", [])
    if not isinstance(recommended_next_reads, list):
        recommended_next_reads = []

    required_next_step = (
        "Pruefe Kontext gegen aktuelle Canon-Evidenz und Governance-Regeln."
    )

    try:
        inp = SelfExplanationInput(
            explanation_type=explanation_type,
            summary=summary,
            reasons=reasons,
            evidence_refs=tuple(evidence_refs_clean),
            required_next_step=required_next_step,
            confidence=confidence_float,
            scope_context=scope_clean,
        )
        output = build_self_explanation(inp)
        payload = output.to_payload()

        return {
            "tool": "context.self_explain",
            "status": "ok",
            "explanation": payload,
            "source_refs": [],
            "evidence_refs": list(output.evidence_refs),
            "graph_path": [],
            "confidence": output.confidence,
            "recommended_next_reads": recommended_next_reads,
            "guardrails": list(output.guardrails),
        }
    except SelfExplanationError as e:
        return {
            "tool": "context.self_explain",
            "status": "error",
            "error": {
                "code": e.code,
                "message": e.message,
            },
        }
    except Exception as e:
        logger.exception("Self-explanation handler failed")
        return {
            "tool": "context.self_explain",
            "status": "error",
            "error": {
                "code": "execution_error",
                "message": str(e),
            },
        }


def context_readiness_handler(**kwargs) -> dict[str, Any]:
    """
    Read-only handler for context.readiness tool.

    Implements Agent Action Readiness Check v0 per #2098.
    Consumes the readiness contract from #2021:
    docs/surrealdb/context-action-readiness-contract.md

    Pure in-process evaluation. No DB/network. Fail-closed.
    """
    # --- Input extraction ---
    task_scope = kwargs.get("task_scope")
    target_issue = kwargs.get("target_issue")
    target_paths = kwargs.get("target_paths", [])
    operation_mode = kwargs.get("operation_mode", "")
    context_package_ref = kwargs.get("context_package_ref")
    required_reads = kwargs.get("required_reads", [])
    evidence_refs = kwargs.get("evidence_refs", [])
    impact_refs = kwargs.get("impact_refs", [])
    stop_conditions_in = kwargs.get("stop_conditions", [])
    uncertainties_in = kwargs.get("uncertainties")

    # --- Normalize ---
    if not isinstance(target_issue, str):
        target_issue = None
    if not isinstance(context_package_ref, str):
        context_package_ref = None
    if not isinstance(target_paths, list):
        target_paths = []
    if not isinstance(required_reads, list):
        required_reads = []
    if not isinstance(evidence_refs, list):
        evidence_refs = []
    if not isinstance(impact_refs, list):
        impact_refs = []
    if not isinstance(stop_conditions_in, list):
        stop_conditions_in = []
    if uncertainties_in is None:
        uncertainties = []
    elif not isinstance(uncertainties_in, list):
        uncertainties = []
    else:
        uncertainties = [
            u for u in uncertainties_in if isinstance(u, str) and u.strip()
        ]

    # --- Validate operation_mode against contract enum ---
    VALID_OPERATION_MODES = frozenset({
        "read_only",
        "dry_run",
        "write (code/docs)",
        "write (config/infra)",
        "write (DB/migration)",
        "write (MCP live)",
    })
    if not isinstance(operation_mode, str) or operation_mode not in VALID_OPERATION_MODES:
        return {
            "tool": "context.readiness",
            "status": "ok",
            "readiness": {
                "status": "blocked_missing_context",
                "reasons": ["Invalid or missing operation_mode"],
                "required_next_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "human_go_required": False,
                "stop_conditions": [
                    "S1: invalid operation_mode — must be one of: "
                    + ", ".join(sorted(VALID_OPERATION_MODES)),
                ],
                "missing_context": [
                    "invalid operation_mode: "
                    + repr(operation_mode)
                    + " — expected one of: "
                    + ", ".join(sorted(VALID_OPERATION_MODES)),
                ],
                "missing_evidence": [],
                "scope_drift_findings": [],
                "uncertainties": [],
                "guardrails": [
                    "Do not proceed. Resolve missing context first.",
                    "Readiness is not authorization. LR remains NO-GO. "
                    "Board stage (trade-capable) is orthogonal.",
                ],
            },
        }

    # --- Accumulators ---
    blocked_context: list[str] = []
    blocked_evidence: list[str] = []
    scope_drift_findings: list[str] = []
    reasons: list[str] = []
    required_next_reads: list[str] = []
    guardrails: list[str] = []
    output_stop_conditions: list[str] = []

    MINIMUM_READS = [
        "AGENTS.md",
        "agents/AGENTS.md",
        "agents/OPEN_CODE_AGENTS.md",
        "docs/runbooks/CONTROL_REGISTER.md",
        "CURRENT_STATUS.md",
        "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
    ]

    # --- Derive characteristics ---
    is_write = isinstance(operation_mode, str) and operation_mode.startswith("write")
    task_lower = task_scope.lower() if isinstance(task_scope, str) else ""
    paths_lower = " ".join(target_paths).lower()

    triggers = ["trading", "risk", "execution", "strategy"]
    touches_trading_risk = any(
        t in task_lower or t in paths_lower for t in triggers
    )

    live_kw = [
        "live", "echtgeld", "production deploy", "go-live",
        "live readiness", "lr-go", "live trading authorization",
    ]
    has_live_claim = any(kw in task_lower for kw in live_kw)

    # --- Check 1: Scope defined ---
    if not task_scope or not isinstance(task_scope, str) or not task_scope.strip():
        blocked_context.append("scope not defined")

    # --- Check 3: Required Reads (minimum baseline) ---
    missing_reads = [r for r in MINIMUM_READS if r not in required_reads]
    if missing_reads:
        blocked_context.append(
            f"minimum required reads missing: {', '.join(missing_reads)}"
        )

    # --- Check 2: Context Package or Required Reads ---
    if not context_package_ref and not required_reads:
        blocked_context.append("no context package and no required reads")

    # --- Check 5: Impact Report for write operations ---
    if is_write and not impact_refs:
        blocked_context.append("write operation without impact report")

    # --- Check 6: Stop Conditions ---
    if not stop_conditions_in:
        blocked_context.append("no stop conditions defined")

    # --- Check 4: Evidence for core assumptions ---
    if is_write and not evidence_refs:
        blocked_evidence.append("write operation without evidence refs")

    # --- Check 7: Human-GO required ---
    # Human-GO is required for any write operation_mode (H1-H5),
    # but read-only/dry-run inspections of trading/risk/execution
    # scope do NOT require Human-GO (per contract Example 11.1).
    human_go_required = is_write

    # --- Check 8: Uncertainties ---
    # uncertainties=[] is OK. For v0, detecting suppressed material
    # uncertainties (governance/LR/Echtgeld) is deferred to Check 9;
    # this check is informational-only at this stage.

    # --- Check 9: No Live/Trading Derivation ---
    if has_live_claim:
        scope_drift_findings.append(
            "task scope contains live/echtgeld/production claim — "
            "readiness assessment must not derive or imply any Live-Readiness, "
            "Echtgeld, or Trading authorization"
        )

    # --- Build output stop conditions from detected issues ---
    if missing_reads:
        for r in missing_reads:
            output_stop_conditions.append(f"S3: minimum read unavailable: {r}")
    if not context_package_ref and not required_reads:
        output_stop_conditions.append(
            "S2: no context package and no required reads"
        )
    if is_write and not impact_refs:
        output_stop_conditions.append("S6: write without impact report")
    if not stop_conditions_in:
        output_stop_conditions.append("S1: no stop conditions — task_scope ambiguous")
    if is_write and not evidence_refs:
        output_stop_conditions.append("S4: core assumptions lack evidence")
    if has_live_claim:
        output_stop_conditions.append(
            "S8: live/echtgeld claims outside LR SSOT"
        )
    if touches_trading_risk and is_write:
        output_stop_conditions.append("S7: trading/risk/execution scope touched")

    # Accumulate user-provided stop conditions
    for sc in stop_conditions_in:
        if sc not in output_stop_conditions:
            output_stop_conditions.append(sc)

    # --- Status derivation (deterministic, fail-closed) ---
    if blocked_context:
        status = "blocked_missing_context"
        reasons.append("Missing required context")
        required_next_reads = list(MINIMUM_READS)
        guardrails.append("Do not proceed. Resolve missing context first.")
    elif blocked_evidence:
        status = "blocked_missing_evidence"
        reasons.append("Missing evidence for core assumptions")
        guardrails.append("Do not proceed. Evidence is missing.")
    elif scope_drift_findings:
        status = "blocked_scope_drift"
        reasons.append("Scope drift detected")
        guardrails.append("Do not proceed. Scope is not stable.")
    elif human_go_required:
        status = "ready_for_human_go"
        reasons.append(
            "Context sufficient. Write operation or trading/risk scope "
            "requires Human-GO."
        )
        guardrails.append(
            "Stop. Request Human-GO. Do not write until approved."
        )
    elif operation_mode == "dry_run":
        status = "ready_for_dry_run"
        reasons.append("Dry-run mode. Plan and preview, but do not execute.")
        guardrails.append("Plan and diff only. No writes without Human-GO.")
    else:
        status = "ready_for_read_only"
        reasons.append("Read-only scope, no writes required.")
        guardrails.append("No writes. No issue comments. No PR creation.")

    # Boundary guardrail — always present
    guardrails.append(
        "Readiness is not authorization. LR remains NO-GO. "
        "Board stage (trade-capable) is orthogonal."
    )

    return {
        "tool": "context.readiness",
        "status": "ok",
        "readiness": {
            "status": status,
            "reasons": reasons,
            "required_next_reads": required_next_reads,
            "human_go_required": human_go_required,
            "stop_conditions": output_stop_conditions,
            "missing_context": blocked_context if blocked_context else [],
            "missing_evidence": blocked_evidence if blocked_evidence else [],
            "scope_drift_findings": scope_drift_findings,
            "uncertainties": uncertainties,
            "guardrails": guardrails,
        },
    }


def context_briefing_handler(**kwargs) -> dict[str, Any]:
    """
    Read-only handler for context.briefing tool.

    Implements Agent Briefing Builder v1 per #2105.
    Consumes the Briefing Schema v1 from #2104:
    docs/surrealdb/context-agent-briefing-schema-v1.md

    Delegates to context.readiness and context.package for context assembly.
    Pure in-process evaluation. No DB/network. Fail-closed.
    Generates deterministic briefing_id from request fields.

    Guardrails: Briefing is context, not authorisation.
    No Live/Echtgeld Go. LR remains NO-GO.
    """
    import hashlib
    import json

    _MISSING = object()

    # --- Input extraction (no defaults for required fields) ---
    task_id = kwargs.get("task_id")
    task_scope = kwargs.get("task_scope")
    target_issue = kwargs.get("target_issue", _MISSING)
    requested_depth = kwargs.get("requested_depth", _MISSING)
    operation_mode = kwargs.get("operation_mode", _MISSING)
    target_paths = kwargs.get("target_paths", [])
    target_symbols = kwargs.get("target_symbols", [])
    target_concepts = kwargs.get("target_concepts", [])
    agent_type = kwargs.get("agent_type", "")
    risk_level = kwargs.get("risk_level", "medium")

    # --- Wave-14 enrichment record inputs (all optional, fail-closed if absent) ---
    _evidence_records_raw = kwargs.get("evidence_records")
    _claim_records_raw = kwargs.get("claim_records")
    _decision_events_raw = kwargs.get("decision_events")
    _memory_records_raw = kwargs.get("memory_records")
    _enrichment_scope = kwargs.get("enrichment_scope", "wave14")
    if not isinstance(_enrichment_scope, str) or not _enrichment_scope.strip():
        _enrichment_scope = "wave14"
    else:
        _enrichment_scope = _enrichment_scope.strip()

    # --- Validate required fields (fail-closed, sentinel for missing keys) ---
    if not task_id or not isinstance(task_id, str) or not task_id.strip():
        return {
            "tool": "context.briefing",
            "status": "error",
            "error": {
                "code": "invalid_task_id",
                "message": "task_id is required and must be a non-empty string",
            },
        }

    if not task_scope or not isinstance(task_scope, str) or not task_scope.strip():
        return {
            "tool": "context.briefing",
            "status": "error",
            "error": {
                "code": "invalid_task_scope",
                "message": "task_scope is required and must be a non-empty string",
            },
        }

    if target_issue is _MISSING:
        return {
            "tool": "context.briefing",
            "status": "error",
            "error": {
                "code": "invalid_target_issue",
                "message": "target_issue is required (must be a string or null)",
            },
        }

    if target_issue is not None and not isinstance(target_issue, str):
        return {
            "tool": "context.briefing",
            "status": "error",
            "error": {
                "code": "invalid_target_issue",
                "message": "target_issue must be a string or null",
            },
        }

    if requested_depth is _MISSING:
        return {
            "tool": "context.briefing",
            "status": "error",
            "error": {
                "code": "invalid_depth",
                "message": "requested_depth is required",
            },
        }

    valid_depths = frozenset({"quick", "standard", "deep"})
    if not isinstance(requested_depth, str) or requested_depth not in valid_depths:
        return {
            "tool": "context.briefing",
            "status": "error",
            "error": {
                "code": "invalid_depth",
                "message": (
                    f"requested_depth must be one of {sorted(valid_depths)}, "
                    f"got {requested_depth!r}"
                ),
            },
        }

    if operation_mode is _MISSING:
        return {
            "tool": "context.briefing",
            "status": "error",
            "error": {
                "code": "invalid_operation_mode",
                "message": "operation_mode is required",
            },
        }

    valid_modes = frozenset({
        "read_only",
        "dry_run",
        "write (code/docs)",
        "write (config/infra)",
        "write (DB/migration)",
        "write (MCP live)",
    })
    if not isinstance(operation_mode, str) or operation_mode not in valid_modes:
        return {
            "tool": "context.briefing",
            "status": "error",
            "error": {
                "code": "invalid_operation_mode",
                "message": (
                    f"operation_mode must be one of {sorted(valid_modes)}, "
                    f"got {operation_mode!r}"
                ),
            },
        }

    if risk_level not in frozenset({"low", "medium", "high"}):
        risk_level = "medium"

    # --- Normalize arrays ---
    if not isinstance(target_paths, list):
        target_paths = []
    if not isinstance(target_symbols, list):
        target_symbols = []
    if not isinstance(target_concepts, list):
        target_concepts = []

    # --- Generate deterministic briefing_id from all request fields ---
    target_paths_norm = [str(p) for p in target_paths if isinstance(p, str)]
    target_symbols_norm = [str(s) for s in target_symbols if isinstance(s, str)]
    target_concepts_norm = [str(c) for c in target_concepts if isinstance(c, str)]
    agent_type_norm = agent_type.strip() if isinstance(agent_type, str) else ""
    risk_level_norm = risk_level if risk_level in frozenset({"low", "medium", "high"}) else "medium"

    request_for_hash: dict[str, Any] = {
        "task_id": task_id.strip(),
        "target_issue": target_issue if target_issue is not None else None,
        "task_scope": task_scope.strip(),
        "target_paths": target_paths_norm,
        "target_symbols": target_symbols_norm,
        "target_concepts": target_concepts_norm,
        "requested_depth": requested_depth,
        "operation_mode": operation_mode,
        "agent_type": agent_type_norm,
        "risk_level": risk_level_norm,
    }
    briefing_id = hashlib.sha256(
        json.dumps(request_for_hash, sort_keys=True).encode()
    ).hexdigest()[:16]

    # --- Delegate to context.readiness with minimum reads ---
    MINIMUM_READS = [
        "AGENTS.md",
        "agents/AGENTS.md",
        "agents/OPEN_CODE_AGENTS.md",
        "docs/runbooks/CONTROL_REGISTER.md",
        "CURRENT_STATUS.md",
        "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
    ]
    readiness_result = context_readiness_handler(
        task_scope=task_scope,
        target_issue=target_issue,
        target_paths=target_paths,
        operation_mode=operation_mode,
        required_reads=MINIMUM_READS,
        stop_conditions=[
            "S1: briefing scope ambiguous",
            "S3: required canon reads unavailable",
        ],
    )
    readiness = readiness_result.get("readiness", {})
    human_go_required = readiness.get("human_go_required", False)
    readiness_status = readiness.get("status", "ready_for_read_only")

    # --- Derive stop conditions ---
    stop_conditions = list(readiness.get("stop_conditions", []))
    if human_go_required:
        stop_conditions.append("H1: write action requires explicit Human-GO")
    stop_conditions.append("S10: STOP if LR/Stage/Live claims surface")

    # --- Internal resolver usage: enrich stop conditions without new fields ---
    resolver_error: Optional[str] = None
    try:
        from tools.surrealdb.context_stop_resolver import resolve_stop_conditions

        resolved = resolve_stop_conditions(
            stop_conditions=stop_conditions,
            operation_mode=operation_mode,
        )
        for rc in resolved:
            sc_type = rc.get("type", "")
            sc_text = (
                f"{rc.get('severity', 'warning')}: {sc_type} — "
                f"{rc.get('reason', '')}"
            )
            if sc_text not in stop_conditions:
                stop_conditions.append(sc_text)
    except Exception as e:
        resolver_error = (
            f"stop resolver unavailable: {type(e).__name__}: {e}"
        )

    # --- Guardrails (always present) ---
    guardrails = [
        "Briefing is context, not authorisation.",
        "No Runtime write.",
        "No MCP live action.",
        "No DB/migration write.",
        "No Trading/Risk/Execution decision.",
        "No Live/Echtgeld Go.",
        "LR remains NO-GO (SSOT: docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md).",
    ]

    # --- Required reads (from readiness, minimum baseline always present) ---
    required_reads = readiness.get("required_next_reads", MINIMUM_READS) or MINIMUM_READS

    # --- Delegate to context.package for standard/deep depth ---
    package_artifacts: list[dict[str, Any]] = []
    package_symbols: list[dict[str, Any]] = []
    package_docs: list[dict[str, Any]] = []
    dependency_paths: list[dict[str, Any]] = []
    known_risks: list[str] = []
    unresolved_questions: list[str] = []
    context_package_ref: Optional[str] = None

    if requested_depth in ("standard", "deep"):
        package_result = context_package_handler(
            artifacts=["briefing_artifact_001", "briefing_artifact_002"],
            format="json",
        )
        pkg = package_result.get("package", {})
        context_package_ref = pkg.get("package_id")

        # Map package items to briefing fields
        for item in pkg.get("items", []):
            package_artifacts.append(
                {
                    "id": item.get("id", ""),
                    "type": item.get("type", "doc"),
                    "title": f"Artifact: {item.get('id', '')}",
                    "source_ref": (
                        item.get("source_refs", [""])[0]
                        if item.get("source_refs")
                        else ""
                    ),
                    "confidence": item.get("confidence", 0.5),
                }
            )

        if target_symbols:
            for sym in target_symbols[:10]:
                package_symbols.append(
                    {
                        "symbol_name": sym,
                        "symbol_type": "function",
                        "file_path": f"<mocked>/path/to/{sym}",
                        "dependents": [],
                    }
                )

        if target_paths:
            for path in target_paths[:5]:
                package_docs.append(
                    {
                        "doc_id": f"doc_{hashlib.md5(path.encode()).hexdigest()[:8]}",
                        "title": path,
                        "path": path,
                        "summary": f"Mocked documentation for {path}.",
                    }
                )

        if target_paths and len(target_paths) > 1:
            dependency_paths.append(
                {
                    "from": target_paths[0],
                    "to": target_paths[1],
                    "relationship": "references",
                }
            )

    # --- Agent attribution for scope summary ---
    agent_label = f" [{agent_type.strip()}]" if agent_type and agent_type.strip() else ""

    # --- Depth-dependent content ---
    if requested_depth == "quick":
        scope_summary = (
            f"Task {task_id}: {task_scope.strip()}{agent_label}. "
            f"Depth: quick — summary only. "
            f"Readiness status: {readiness_status}. "
            f"Human-GO required: {human_go_required}."
        )
    elif requested_depth == "standard":
        scope_summary = (
            f"Task {task_id}: {task_scope.strip()}{agent_label}. "
            f"Depth: standard — key artifacts + stop conditions. "
            f"Readiness status: {readiness_status}. "
            f"Context package: {context_package_ref or 'mocked-v0'}. "
            f"Human-GO required: {human_go_required}."
        )
    else:  # deep
        scope_summary = (
            f"Task {task_id}: {task_scope.strip()}{agent_label}. "
            f"Depth: deep — full context package requested. "
            f"Readiness status: {readiness_status}. "
            f"Context package: {context_package_ref or 'mocked-v0'}. "
            f"Human-GO required: {human_go_required}. "
            f"Note: deep depth requires full SurrealDB Context Package — "
            f"mocked/synthetic in v0."
        )
        unresolved_questions.append(
            "deep depth requires full Context Package from SurrealDB; "
            "v0 uses synthetic/mock package inputs"
        )

    # --- Known risks ---
    known_risks.append("v0 briefing builder uses synthetic/mock package inputs")
    if readiness_status.startswith("blocked"):
        known_risks.append(
            f"Readiness check blocked: {readiness_status}; "
            f"briefing may be incomplete"
        )
    if not target_paths and not target_symbols:
        known_risks.append(
            "no target_paths or target_symbols specified; "
            "context may be minimal"
        )

    # --- Surface resolver failure ---
    if resolver_error:
        known_risks.append(resolver_error)
        unresolved_questions.append(
            "stop condition resolver failed; flat stop_conditions preserved"
        )

    # --- Readiness blocker surfaced ---
    if readiness_status.startswith("blocked"):
        unresolved_questions.append(
            f"readiness check returned {readiness_status}: "
            f"{'; '.join(readiness.get('reasons', ['unknown']))}"
        )
        stop_conditions.append(
            f"S2/S3: readiness blocked ({readiness_status}) — "
            f"resolve missing context/evidence before proceeding"
        )

    # --- Validation plan ---
    is_write = operation_mode.startswith("write")
    validation_plan = []
    if is_write:
        validation_plan.append(
            {
                "step": "Verify Human-GO received",
                "method": "Check that explicit GO was given for this specific action",
                "evidence_required": "Human-GO confirmation (issue comment or explicit GO message)",
            }
        )
    validation_plan.append(
        {
            "step": "Re-read required canon files",
            "method": "Read AGENTS.md chain + CONTROL_REGISTER + CURRENT_STATUS + LR-AUDIT-STATUS",
            "evidence_required": "Self-attestation that all required reads were completed",
        }
    )
    validation_plan.append(
        {
            "step": "Verify all guardrails acknowledged",
            "method": "Review guardrails list in this briefing",
            "evidence_required": "Explicit acknowledgement in session log",
        }
    )

    # --- Enrichment (#2122) ---
    enrichment_id = hashlib.sha256(
        (briefing_id + requested_depth).encode()
    ).hexdigest()[:16]

    enriched_decisions: list[Any] = []
    enriched_evidence: list[Any] = []
    enriched_memory: list[Any] = []
    stale_evidence_notice: list[str] = []
    contradictory_evidence_notice: list[str] = []
    missing_evidence_notice: list[str] = []
    blocking_trust_findings: list[str] = []
    recommended_next_reads_enrichment: list[str] = []

    _has_records = any([
        isinstance(_evidence_records_raw, list) and bool(_evidence_records_raw),
        isinstance(_claim_records_raw, list) and bool(_claim_records_raw),
        isinstance(_decision_events_raw, list) and bool(_decision_events_raw),
        isinstance(_memory_records_raw, list) and bool(_memory_records_raw),
    ])

    if not _has_records:
        # Fail-closed: no records provided — controlled-empty enrichment
        missing_evidence_notice = [
            "no_evidence_records_provided",
            "no_decision_events_provided",
        ]
        trust_summary = (
            "Enrichment skipped: no evidence_records, claim_records, decision_events, "
            "or memory_records provided. Supply records to enable evidence/decision enrichment."
        )
        stop_conditions.append(
            "S5: no enrichment records provided — supply evidence_records, claim_records, "
            "decision_events, or memory_records to enable enrichment"
        )
    else:
        # Real enrichment using Wave-14 services (#2122)
        # Read-only, fail-closed, no DB/network/write.
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

        _evidence_service_result: Optional[dict[str, Any]] = None
        _claim_service_result: Optional[dict[str, Any]] = None
        _decision_service_result: Optional[dict[str, Any]] = None
        _memory_service_result: Optional[dict[str, Any]] = None

        # Evidence lookup: by_freshness to capture all records incl. null-confidence
        if isinstance(_evidence_records_raw, list) and _evidence_records_raw:
            try:
                _ev_req = EvidenceLookupRequest(
                    mode="by_freshness",
                    freshness_days=36500,  # 100 years — match all dated records
                )
                _evidence_service_result = lookup_evidence_v1(
                    _evidence_records_raw, _ev_req
                )
                _matched_ev = _evidence_service_result.get("matched_evidence", [])
                # Filter matched evidence to requested scope — by_freshness does not
                # filter by scope, unlike claim/decision/memory enrichers.
                _matched_ev = [
                    ev for ev in _matched_ev
                    if ev.get("scope") == _enrichment_scope
                ]
                enriched_evidence = [
                    {
                        "evidence_id": _ev.get("evidence_id"),
                        "title": _ev.get("title"),
                        "confidence": _ev.get("confidence"),
                        "stale": _ev.get("stale"),
                        "blocking_missing": _ev.get("blocking_missing"),
                        "evidence_type": _ev.get("evidence_type"),
                        "scope": _ev.get("scope"),
                    }
                    for _ev in _matched_ev[:20]
                ]
                # by_freshness silently excludes records with no created_at.
                # Detect and preserve those records so they are never invisible.
                # Filter to Mapping instances first — non-dict items (strings,
                # None, ints) must not reach .get() or they raise AttributeError.
                _matched_ev_ids = {_ev.get("evidence_id") for _ev in _matched_ev}
                _undated_recs = [
                    rec for rec in _evidence_records_raw
                    if isinstance(rec, dict)
                    and not rec.get("created_at")
                    and rec.get("evidence_id") not in _matched_ev_ids
                    and rec.get("scope") == _enrichment_scope
                ]
                _malformed_count = sum(
                    1 for rec in _evidence_records_raw if not isinstance(rec, dict)
                )
                if _malformed_count:
                    blocking_trust_findings.append(
                        f"malformed_evidence_records_skipped: {_malformed_count}"
                    )
                if _undated_recs:
                    for _urec in _undated_recs[:20]:
                        enriched_evidence.append({
                            "evidence_id": _urec.get("evidence_id"),
                            "title": _urec.get("title"),
                            "confidence": _urec.get("confidence"),
                            "stale": _urec.get("stale"),
                            "blocking_missing": _urec.get("blocking_missing"),
                            "evidence_type": _urec.get("evidence_type"),
                            "scope": _urec.get("scope"),
                        })
                    _undated_ids = [r.get("evidence_id") for r in _undated_recs]
                    blocking_trust_findings.append(
                        f"undated_evidence_missing_created_at: {_undated_ids}"
                    )
                    recommended_next_reads_enrichment.append(
                        "Add created_at to undated evidence records for freshness tracking"
                    )
                _stale_ev_ids = _evidence_service_result.get("stale_evidence_ids", [])
                if _stale_ev_ids:
                    stale_evidence_notice.append(
                        f"stale_evidence: {_stale_ev_ids}"
                    )
                    recommended_next_reads_enrichment.append(
                        "Review stale evidence before proceeding"
                    )
                _blocking_ids = _evidence_service_result.get("blocking_missing_ids", [])
                if _blocking_ids:
                    blocking_trust_findings.append(
                        f"blocking_missing_evidence: {_blocking_ids}"
                    )
                    missing_evidence_notice.append(
                        f"blocking_missing_evidence: {_blocking_ids}"
                    )
                    recommended_next_reads_enrichment.append(
                        "Resolve blocking missing evidence before proceeding"
                    )
            except EvidenceLookupError as _e:
                known_risks.append(f"evidence_lookup_error: {_e}")
                missing_evidence_notice.append("evidence_lookup_failed")

        # Claim resolution: by_scope with enrichment_scope.
        # Pre-filter to exact scope — ClaimResolver.by_scope uses substring
        # matching, so scope='wave1' would match records scoped to 'wave14'.
        if isinstance(_claim_records_raw, list) and _claim_records_raw:
            try:
                _scoped_claims = [
                    r for r in _claim_records_raw
                    if isinstance(r, dict) and r.get("scope") == _enrichment_scope
                ]
                _cl_req = ClaimResolveRequest(
                    mode="by_scope",
                    scope=_enrichment_scope,
                )
                if _scoped_claims:
                    _claim_service_result = resolve_claims_v1(_scoped_claims, _cl_req)
                    _disputed = _claim_service_result.get("disputed_claim_ids", [])
                    if _disputed:
                        contradictory_evidence_notice.append(
                            f"disputed_claims: {_disputed}"
                        )
            except ClaimResolverError as _e:
                known_risks.append(f"claim_resolve_error: {_e}")

        # Decision history: by_scope with enrichment_scope.
        # Pre-filter to exact scope — DecisionHistoryQuery.by_scope uses
        # substring matching, so scope='wave1' would match 'wave14' events.
        if isinstance(_decision_events_raw, list) and _decision_events_raw:
            try:
                _scoped_decisions = [
                    r for r in _decision_events_raw
                    if isinstance(r, dict) and r.get("scope") == _enrichment_scope
                ]
                _dec_req = DecisionHistoryQueryRequest(
                    mode="by_scope",
                    scope=_enrichment_scope,
                )
                if _scoped_decisions:
                    _decision_service_result = query_decision_history_v1(
                        _scoped_decisions, _dec_req
                    )
                    _matched_dec = _decision_service_result.get("matched_decisions", [])
                    # Post-filter to exact scope as defence-in-depth.
                    _matched_dec = [
                        d for d in _matched_dec
                        if d.get("scope") == _enrichment_scope
                    ]
                    enriched_decisions = [
                        {
                            "decision_id": _d.get("decision_id"),
                            "title": _d.get("title"),
                            "status": _d.get("status"),
                            "scope": _d.get("scope"),
                        }
                        for _d in _matched_dec[:20]
                    ]
            except DecisionHistoryQueryError as _e:
                known_risks.append(f"decision_history_error: {_e}")

        # Memory read: by_scope with enrichment_scope
        if isinstance(_memory_records_raw, list) and _memory_records_raw:
            try:
                _mem_req = MemoryReadRequest(
                    mode="by_scope",
                    scope=_enrichment_scope,
                )
                _memory_service_result = read_memory_v1(
                    _memory_records_raw, _mem_req
                )
                _matched_mem = _memory_service_result.get("matched_memory", [])
                enriched_memory = [
                    {
                        "memory_id": _m.get("memory_id"),
                        "title": _m.get("title"),
                        "memory_type": _m.get("memory_type"),
                        "stale": _m.get("stale"),
                        "scope": _m.get("scope"),
                        "evidence_backed": _m.get("evidence_backed"),
                    }
                    for _m in _matched_mem[:20]
                ]
                _stale_mem_ids = _memory_service_result.get("stale_memory_ids", [])
                if _stale_mem_ids:
                    stale_evidence_notice.append(
                        f"stale_memory: {_stale_mem_ids}"
                    )
            except MemoryReadError as _e:
                known_risks.append(f"memory_read_error: {_e}")

        # Trust summary from all service results
        try:
            _ts_req = TrustSummaryRequest(
                scope=_enrichment_scope,
                topic=(
                    target_concepts_norm[0]
                    if target_concepts_norm
                    else None
                ),
            )
            _ts_result = build_trust_summary_v1(
                _ts_req,
                evidence_result=_evidence_service_result,
                claim_result=_claim_service_result,
                decision_result=_decision_service_result,
                memory_result=_memory_service_result,
            )
            _trust_level = _ts_result.get("trust_level", "blocked")
            _composite_score = _ts_result.get("composite_score", 0.0)
            _ts_blocking = _ts_result.get("blocking_trust_findings", [])
            if _ts_blocking:
                blocking_trust_findings.extend(
                    [str(_f) for _f in _ts_blocking]
                )
            _stale_ts_flags = _ts_result.get("stale_flags", [])
            if _stale_ts_flags:
                stale_evidence_notice.extend(
                    [str(_f) for _f in _stale_ts_flags]
                )
            trust_summary = (
                f"Trust level: {_trust_level}. "
                f"Composite score: {_composite_score:.2f}. "
                f"Evidence items: {len(enriched_evidence)}. "
                f"Decisions: {len(enriched_decisions)}. "
                f"Memory items: {len(enriched_memory)}. "
                f"Scope: {_enrichment_scope}. "
                f"no_echtgeld_go: true."
            )
            # S6 fires on ALL blocking findings — trust-service findings AND
            # locally detected findings (undated records, malformed items).
            # blocking_trust_findings already contains both at this point.
            if blocking_trust_findings:
                trust_summary += (
                    f" Blocking findings: {len(blocking_trust_findings)}. "
                    "Review before proceeding."
                )
                if not any("S6" in sc for sc in stop_conditions):
                    stop_conditions.append(
                        "S6: blocking trust findings present — "
                        "review evidence before proceeding"
                    )
        except TrustSummaryError as _e:
            trust_summary = f"Trust summary unavailable: {_e}. no_echtgeld_go: true."
            known_risks.append(f"trust_summary_error: {_e}")

    # --- Assemble briefing result ---
    briefing: dict[str, Any] = {
        "briefing_id": briefing_id,
        "enrichment_id": f"cdb-enrich-{enrichment_id}",
        "enriched_briefing_id": briefing_id,
        "scope_summary": scope_summary,
        "trust_summary": trust_summary,
        "context_package_ref": context_package_ref,
        "required_reads": required_reads,
        "relevant_artifacts": package_artifacts[:10],
        "relevant_symbols": package_symbols[:10],
        "relevant_docs": package_docs[:5],
        "relevant_decisions": enriched_decisions,
        "relevant_evidence": enriched_evidence,
        "enriched_decisions": enriched_decisions,
        "enriched_evidence": enriched_evidence,
        "enriched_memory": enriched_memory,
        "enriched_stop_conditions": stop_conditions,
        "stale_evidence_notice": stale_evidence_notice,
        "contradictory_evidence_notice": contradictory_evidence_notice,
        "missing_evidence_notice": missing_evidence_notice,
        "blocking_trust_findings": blocking_trust_findings,
        "recommended_next_reads": recommended_next_reads_enrichment,
        "approval_semantics": {"no_echtgeld_go": True},
        "dependency_paths": dependency_paths,
        "known_risks": known_risks,
        "guardrails": guardrails,
        "stop_conditions": stop_conditions,
        "validation_plan": validation_plan,
        "unresolved_questions": unresolved_questions,
        "human_go_required": human_go_required,
    }

    return {
        "tool": "context.briefing",
        "status": "ok",
        "briefing": briefing,
    }


def cdb_context_briefing_handler(**kwargs) -> dict[str, Any]:
    """Alias wrapper for context.briefing (#2110).

    - Delegates to context_briefing_handler(**kwargs)
    - Rewrites tool name to cdb_context_briefing
    - Enforces a deterministic byte-size limit fail-closed
    """
    result = context_briefing_handler(**kwargs)
    if not isinstance(result, dict):
        return {
            "tool": "cdb_context_briefing",
            "status": "error",
            "error": {
                "code": "execution_error",
                "message": "context_briefing_handler returned non-dict result",
            },
        }

    result["tool"] = "cdb_context_briefing"

    try:
        response_bytes = len(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        )
    except Exception as e:
        logger.exception("Failed to measure cdb_context_briefing payload size")
        return {
            "tool": "cdb_context_briefing",
            "status": "error",
            "error": {
                "code": "execution_error",
                "message": str(e),
            },
        }

    if response_bytes > CDB_CONTEXT_BRIEFING_MAX_RESPONSE_BYTES:
        return {
            "tool": "cdb_context_briefing",
            "status": "error",
            "error": {
                "code": "payload_too_large",
                "message": (
                    "cdb_context_briefing response exceeds byte limit; "
                    "reduce requested_depth or narrow scope."
                ),
                "details": {
                    "max_bytes": CDB_CONTEXT_BRIEFING_MAX_RESPONSE_BYTES,
                    "actual_bytes": response_bytes,
                },
            },
        }

    return result


def context_stop_resolver_handler(**kwargs) -> dict[str, Any]:
    """
    Read-only handler for context.stop_resolver tool.

    Resolves flat stop-condition strings to typed stop condition objects.
    Delegates to tools.surrealdb.context_stop_resolver.resolve_stop_conditions.
    Pure in-process evaluation. No DB/network. Fail-closed.

    Input:
        stop_conditions: list[str] — flat stop condition strings
        warnings: list[str] (optional) — warning strings to scan
        readiness_result: dict (optional) — readiness result for additional inputs
        operation_mode: str (optional, default "read_only")

    Output:
        tool, status, resolved (list of typed conditions)
    """
    from tools.surrealdb.context_stop_resolver import resolve_stop_conditions

    stop_conditions_in = kwargs.get("stop_conditions", [])
    warnings_in = kwargs.get("warnings")
    readiness_result_in = kwargs.get("readiness_result")
    operation_mode = kwargs.get("operation_mode", "read_only")

    if not isinstance(stop_conditions_in, list):
        stop_conditions_in = []

    if warnings_in is not None and not isinstance(warnings_in, list):
        warnings_in = []

    if readiness_result_in is not None and not isinstance(readiness_result_in, dict):
        readiness_result_in = None

    valid_modes = frozenset({
        "read_only",
        "dry_run",
        "write (code/docs)",
        "write (config/infra)",
        "write (DB/migration)",
        "write (MCP live)",
    })
    if not isinstance(operation_mode, str) or operation_mode not in valid_modes:
        operation_mode = "read_only"

    try:
        resolved = resolve_stop_conditions(
            stop_conditions=stop_conditions_in,
            warnings=warnings_in,
            readiness_result=readiness_result_in,
            operation_mode=operation_mode,
        )
    except Exception as e:
        logger.exception("Stop condition resolver failed")
        return {
            "tool": "context.stop_resolver",
            "status": "error",
            "error": {
                "code": "execution_error",
                "message": str(e),
            },
        }

    return {
        "tool": "context.stop_resolver",
        "status": "ok",
        "resolved": resolved,
    }


def context_required_reads_handler(**kwargs) -> dict[str, Any]:
    """
    Read-only handler for context.required_reads tool.

    Resolves prioritized required reads from task scope, target issue,
    target paths, target symbols, and operation mode (per #2106).

    Delegates to tools.surrealdb.context_required_reads.resolve_required_reads.
    Pure in-process evaluation. No DB/network/GitHub. Fail-closed.

    Input:
        task_scope: str (required) — what the agent is asked to do
        target_issue: str | null (required) — GitHub issue or None
        target_paths: list[str] (optional)
        target_symbols: list[str] (optional)
        target_concepts: list[str] (optional)
        operation_mode: str (required) — valid enum value

    Output:
        tool, status, resolved_reads (list of structured RequiredRead dicts)
    """
    from tools.surrealdb.context_required_reads import (
        VALID_OPERATION_MODES,
        resolve_required_reads,
    )

    _MISSING = object()

    task_scope = kwargs.get("task_scope")
    target_issue = kwargs.get("target_issue", _MISSING)
    operation_mode = kwargs.get("operation_mode", _MISSING)
    target_paths = kwargs.get("target_paths", [])
    target_symbols = kwargs.get("target_symbols", [])
    target_concepts = kwargs.get("target_concepts", [])

    # --- Validate task_scope ---
    if not task_scope or not isinstance(task_scope, str) or not task_scope.strip():
        return {
            "tool": "context.required_reads",
            "status": "error",
            "error": {
                "code": "invalid_task_scope",
                "message": "task_scope is required and must be a non-empty string",
            },
        }

    # --- Validate target_issue ---
    if target_issue is _MISSING:
        return {
            "tool": "context.required_reads",
            "status": "error",
            "error": {
                "code": "invalid_target_issue",
                "message": "target_issue is required (must be a string or null)",
            },
        }

    if target_issue is not None and not isinstance(target_issue, str):
        return {
            "tool": "context.required_reads",
            "status": "error",
            "error": {
                "code": "invalid_target_issue",
                "message": "target_issue must be a string or null",
            },
        }

    # --- Validate operation_mode ---
    if operation_mode is _MISSING:
        return {
            "tool": "context.required_reads",
            "status": "error",
            "error": {
                "code": "invalid_operation_mode",
                "message": "operation_mode is required",
            },
        }

    if not isinstance(operation_mode, str) or operation_mode not in VALID_OPERATION_MODES:
        return {
            "tool": "context.required_reads",
            "status": "error",
            "error": {
                "code": "invalid_operation_mode",
                "message": (
                    f"operation_mode must be one of {sorted(VALID_OPERATION_MODES)}, "
                    f"got {operation_mode!r}"
                ),
            },
        }

    # --- Normalize arrays ---
    if not isinstance(target_paths, list):
        target_paths = []
    if not isinstance(target_symbols, list):
        target_symbols = []
    if not isinstance(target_concepts, list):
        target_concepts = []

    # --- Resolve ---
    try:
        resolved = resolve_required_reads(
            task_scope=task_scope.strip(),
            target_issue=target_issue,
            target_paths=target_paths,
            target_symbols=target_symbols,
            operation_mode=operation_mode,
            target_concepts=target_concepts,
        )
    except Exception as e:
        logger.exception("Required reads resolver failed")
        return {
            "tool": "context.required_reads",
            "status": "error",
            "error": {
                "code": "execution_error",
                "message": str(e),
            },
        }

    return {
        "tool": "context.required_reads",
        "status": "ok",
        "resolved_reads": resolved,
    }


def cdb_context_impact_handler(**kwargs) -> dict[str, Any]:
    """
    Read-only handler for cdb_context_impact tool.

    Delegates to tools.surrealdb.context_impact_radar.compute_impact.
    Pure in-process evaluation. No DB/network/GitHub. Fail-closed.

    Input:
        target_paths: list[str] (optional)
        target_symbols: list[str] (optional)
        target_issue: str | null (optional)
        target_concepts: list[str] (optional)
        operation_mode: str (optional, default "read_only")

    Output:
        tool, status, impact (full ImpactReport payload), guardrails
    """
    from tools.surrealdb.context_impact_radar import (
        ImpactRadarInput,
        compute_impact,
    )

    target_paths = kwargs.get("target_paths", [])
    target_symbols = kwargs.get("target_symbols", [])
    target_issue = kwargs.get("target_issue")
    target_concepts = kwargs.get("target_concepts", [])
    operation_mode = kwargs.get("operation_mode", "read_only")

    if not isinstance(target_paths, list):
        target_paths = []
    if not isinstance(target_symbols, list):
        target_symbols = []
    if not isinstance(target_concepts, list):
        target_concepts = []
    if target_issue is not None and not isinstance(target_issue, str):
        target_issue = None

    valid_modes = frozenset({
        "read_only",
        "dry_run",
        "write (code/docs)",
        "write (config/infra)",
        "write (DB/migration)",
        "write (MCP live)",
    })
    if not isinstance(operation_mode, str) or operation_mode not in valid_modes:
        return {
            "tool": "cdb_context_impact",
            "status": "error",
            "error": {
                "code": "invalid_operation_mode",
                "message": (
                    f"operation_mode must be one of "
                    f"{sorted(valid_modes)}, got {operation_mode!r}"
                ),
            },
        }

    target_paths_clean = [p for p in target_paths if isinstance(p, str) and p.strip()]
    target_symbols_clean = [s for s in target_symbols if isinstance(s, str) and s.strip()]
    target_concepts_clean = [c for c in target_concepts if isinstance(c, str) and c.strip()]

    try:
        inp = ImpactRadarInput(
            target_paths=tuple(target_paths_clean),
            target_symbols=tuple(target_symbols_clean),
            target_issue=target_issue,
            target_concepts=tuple(target_concepts_clean),
            operation_mode=operation_mode,
        )
        report = compute_impact(inp)
        impact_payload = report.to_payload()
    except Exception as e:
        logger.exception("Impact radar computation failed")
        return {
            "tool": "cdb_context_impact",
            "status": "error",
            "error": {
                "code": "execution_error",
                "message": str(e),
            },
        }

    guardrails = [
        "Impact is analysis, not authorization.",
        "No Live-Go, no Echtgeld-Go, no risk approval.",
        "LR remains NO-GO (SSOT: docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md).",
        "Board stage (trade-capable) is orthogonal to live readiness.",
    ]

    return {
        "tool": "cdb_context_impact",
        "status": "ok",
        "impact": impact_payload,
        "guardrails": guardrails,
    }


# ── Wave-14 MCP Tool Handlers (#2122 Registry/Bridge Completeness) ─────────────


def cdb_context_evidence_resolve_handler(**kwargs) -> dict[str, Any]:
    """Read-only MCP handler for cdb_context_evidence_resolve.

    Thin adapter: passes **kwargs as the request mapping to the Wave-14 adapter.
    Fail-closed. No DB/network/write.
    """
    from tools.mcp.context_evidence_memory_tools import handle_cdb_context_evidence_resolve

    return handle_cdb_context_evidence_resolve(kwargs)


def cdb_context_claim_resolve_handler(**kwargs) -> dict[str, Any]:
    """Read-only MCP handler for cdb_context_claim_resolve.

    Thin adapter: passes **kwargs as the request mapping to the Wave-14 adapter.
    Fail-closed. No DB/network/write.
    """
    from tools.mcp.context_evidence_memory_tools import handle_cdb_context_claim_resolve

    return handle_cdb_context_claim_resolve(kwargs)


def cdb_context_memory_get_handler(**kwargs) -> dict[str, Any]:
    """Read-only MCP handler for cdb_context_memory_get.

    Thin adapter: passes **kwargs as the request mapping to the Wave-14 adapter.
    Fail-closed. No DB/network/write.
    """
    from tools.mcp.context_evidence_memory_tools import handle_cdb_context_memory_get

    return handle_cdb_context_memory_get(kwargs)


def cdb_context_trust_summary_handler(**kwargs) -> dict[str, Any]:
    """Read-only MCP handler for cdb_context_trust_summary.

    Thin adapter: passes **kwargs as the request mapping to the Wave-14 adapter.
    Fail-closed. No DB/network/write.
    """
    from tools.mcp.context_evidence_memory_tools import handle_cdb_context_trust_summary

    return handle_cdb_context_trust_summary(kwargs)


def cdb_context_decision_history_handler(**kwargs) -> dict[str, Any]:
    """Read-only MCP handler for cdb_context_decision_history.

    Thin adapter: passes **kwargs as the request mapping to the Wave-14 adapter.
    Fail-closed. No DB/network/write.
    """
    from tools.mcp.context_decision_tools import handle_cdb_context_decision_history

    return handle_cdb_context_decision_history(kwargs)


def cdb_context_decision_replay_handler(**kwargs) -> dict[str, Any]:
    """Read-only MCP handler for cdb_context_decision_replay.

    Thin adapter: passes **kwargs as the request mapping to the Wave-14 adapter.
    Fail-closed. No DB/network/write.
    """
    from tools.mcp.context_decision_tools import handle_cdb_context_decision_replay

    return handle_cdb_context_decision_replay(kwargs)


# ── Wave-15 MCP Tool Handlers (#2148 Contradiction MCP) ──────────────────────


def cdb_context_contradictions_handler(**kwargs) -> dict[str, Any]:
    """Read-only MCP handler for cdb_context_contradictions.

    Thin adapter: passes **kwargs as the request mapping to the Wave-15 adapter.
    Fail-closed. No DB/network/write. Detection is signal, not action permission.
    """
    from tools.mcp.context_contradiction_tools import handle_cdb_context_contradictions

    return handle_cdb_context_contradictions(kwargs)


# ── Wave-16-C MCP Tool Handlers (#2157 Stale Context MCP) ────────────────────


def cdb_context_stale_handler(**kwargs) -> dict[str, Any]:
    """Read-only MCP handler for cdb_context_stale.

    Thin adapter: passes **kwargs as the request mapping to the Wave-16-C adapter.
    Fail-closed. No DB/network/write. Bundle-driven. Detection is signal, not
    action permission. No live-go. No Echtgeld-Go.
    """
    from tools.mcp.stale_context_tools import handle_cdb_context_stale

    return handle_cdb_context_stale(kwargs)


# ── Wave-17-C MCP Tool Handlers (#2165 Scope Drift MCP) ──────────────────────


def cdb_context_scope_drift_handler(**kwargs) -> dict[str, Any]:
    """Read-only MCP handler for cdb_context_scope_drift.

    Thin adapter: passes **kwargs as the request mapping to the Wave-17-C adapter.
    Fail-closed. No DB/network/write. Bundle-driven. Detection is signal, not
    action permission. No live-go. No Echtgeld-Go.
    """
    from tools.mcp.scope_drift_tools import handle_cdb_context_scope_drift

    return handle_cdb_context_scope_drift(kwargs)


def cdb_context_quality_score_handler(**kwargs) -> dict[str, Any]:
    """Read-only MCP handler for cdb_context_quality_score.

    Thin adapter: passes **kwargs as the request mapping to the Wave-18-B adapter.
    Fail-closed. No DB/network/write. Bundle-driven. Scoring is signal, not
    action permission. No live-go. No Echtgeld-Go.
    """
    from tools.mcp.quality_scoring_tools import handle_quality_score

    return handle_quality_score(**kwargs)


def cdb_context_architect_signals_handler(**kwargs) -> dict[str, Any]:
    """Read-only MCP handler for cdb_context_architect_signals.

    Thin adapter: passes **kwargs as the request mapping to the Wave-18-D adapter.
    Fail-closed. No DB/network/write. Bundle-driven. Signals are recommendations,
    not action permissions. No automatic issue creation. No live-go. No Echtgeld-Go.
    """
    from tools.mcp.architect_signal_tools import handle_architect_signals

    return handle_architect_signals(**kwargs)


class ContextBridge:
    """
    MCP Bridge for Context Intelligence System.

    This bridge provides read-only access to Context Tools via MCP protocol.
    All tools are fail-closed - they return errors rather than performing
    unauthorized operations.

    Important: This bridge does NOT provide:
    - Live Readiness evaluation
    - Echtgeld authorization
    - Risk approval
    - Execution clearance

    The 'context.readiness' tool provides evaluation metadata only.
    """

    def __init__(self) -> None:
        self._registry = ContextToolRegistry
        # Replace scaffold handlers with real implementations
        old_search = self._registry.get_tool("context.search")
        if old_search:
            new_search = ToolDefinition(
                name=old_search.name,
                description=old_search.description,
                input_schema=old_search.input_schema,
                output_schema=old_search.output_schema,
                read_only=old_search.read_only,
                handler=context_search_handler,
            )
            self._registry._tools["context.search"] = new_search
        old_trace = self._registry.get_tool("context.trace")
        if old_trace:
            new_trace = ToolDefinition(
                name=old_trace.name,
                description=old_trace.description,
                input_schema=old_trace.input_schema,
                output_schema=old_trace.output_schema,
                read_only=old_trace.read_only,
                handler=context_trace_handler,
            )
            self._registry._tools["context.trace"] = new_trace
        old_explain = self._registry.get_tool("context.explain_source")
        if old_explain:
            new_explain = ToolDefinition(
                name=old_explain.name,
                description=old_explain.description,
                input_schema=old_explain.input_schema,
                output_schema=old_explain.output_schema,
                read_only=old_explain.read_only,
                handler=context_explain_source_handler,
            )
            self._registry._tools["context.explain_source"] = new_explain
        old_package = self._registry.get_tool("context.package")
        if old_package:
            new_package = ToolDefinition(
                name=old_package.name,
                description=old_package.description,
                input_schema=old_package.input_schema,
                output_schema=old_package.output_schema,
                read_only=old_package.read_only,
                handler=context_package_handler,
            )
            self._registry._tools["context.package"] = new_package
        old_self_explain = self._registry.get_tool("context.self_explain")
        if old_self_explain:
            new_self_explain = ToolDefinition(
                name=old_self_explain.name,
                description=old_self_explain.description,
                input_schema=old_self_explain.input_schema,
                output_schema=old_self_explain.output_schema,
                read_only=old_self_explain.read_only,
                handler=context_self_explain_handler,
            )
            self._registry._tools["context.self_explain"] = new_self_explain
        old_readiness = self._registry.get_tool("context.readiness")
        if old_readiness:
            new_readiness = ToolDefinition(
                name=old_readiness.name,
                description=old_readiness.description,
                input_schema=old_readiness.input_schema,
                output_schema=old_readiness.output_schema,
                read_only=old_readiness.read_only,
                handler=context_readiness_handler,
            )
            self._registry._tools["context.readiness"] = new_readiness
        old_briefing = self._registry.get_tool("context.briefing")
        if old_briefing:
            new_briefing = ToolDefinition(
                name=old_briefing.name,
                description=old_briefing.description,
                input_schema=old_briefing.input_schema,
                output_schema=old_briefing.output_schema,
                read_only=old_briefing.read_only,
                handler=context_briefing_handler,
            )
            self._registry._tools["context.briefing"] = new_briefing
        old_cdb_briefing = self._registry.get_tool("cdb_context_briefing")
        if old_cdb_briefing:
            new_cdb_briefing = ToolDefinition(
                name=old_cdb_briefing.name,
                description=old_cdb_briefing.description,
                input_schema=old_cdb_briefing.input_schema,
                output_schema=old_cdb_briefing.output_schema,
                read_only=old_cdb_briefing.read_only,
                handler=cdb_context_briefing_handler,
            )
            self._registry._tools["cdb_context_briefing"] = new_cdb_briefing
        old_stop_resolver = self._registry.get_tool("context.stop_resolver")
        if old_stop_resolver:
            new_stop_resolver = ToolDefinition(
                name=old_stop_resolver.name,
                description=old_stop_resolver.description,
                input_schema=old_stop_resolver.input_schema,
                output_schema=old_stop_resolver.output_schema,
                read_only=old_stop_resolver.read_only,
                handler=context_stop_resolver_handler,
            )
            self._registry._tools["context.stop_resolver"] = new_stop_resolver
        old_required_reads = self._registry.get_tool("context.required_reads")
        if old_required_reads:
            new_required_reads = ToolDefinition(
                name=old_required_reads.name,
                description=old_required_reads.description,
                input_schema=old_required_reads.input_schema,
                output_schema=old_required_reads.output_schema,
                read_only=old_required_reads.read_only,
                handler=context_required_reads_handler,
            )
            self._registry._tools["context.required_reads"] = new_required_reads
        old_impact = self._registry.get_tool("cdb_context_impact")
        if old_impact:
            new_impact = ToolDefinition(
                name=old_impact.name,
                description=old_impact.description,
                input_schema=old_impact.input_schema,
                output_schema=old_impact.output_schema,
                read_only=old_impact.read_only,
                handler=cdb_context_impact_handler,
            )
            self._registry._tools["cdb_context_impact"] = new_impact
        # Wave-14 handlers (#2122 Registry/Bridge completeness)
        _wave14_handler_map = {
            "cdb_context_evidence_resolve": cdb_context_evidence_resolve_handler,
            "cdb_context_claim_resolve": cdb_context_claim_resolve_handler,
            "cdb_context_memory_get": cdb_context_memory_get_handler,
            "cdb_context_trust_summary": cdb_context_trust_summary_handler,
            "cdb_context_decision_history": cdb_context_decision_history_handler,
            "cdb_context_decision_replay": cdb_context_decision_replay_handler,
        }
        for _tool_name, _handler_fn in _wave14_handler_map.items():
            _old = self._registry.get_tool(_tool_name)
            if _old:
                self._registry._tools[_tool_name] = ToolDefinition(
                    name=_old.name,
                    description=_old.description,
                    input_schema=_old.input_schema,
                    output_schema=_old.output_schema,
                    read_only=_old.read_only,
                    handler=_handler_fn,
                )
        # Wave-15 handlers (#2148 Contradiction MCP)
        _wave15_handler_map = {
            "cdb_context_contradictions": cdb_context_contradictions_handler,
        }
        for _tool_name, _handler_fn in _wave15_handler_map.items():
            _old = self._registry.get_tool(_tool_name)
            if _old:
                self._registry._tools[_tool_name] = ToolDefinition(
                    name=_old.name,
                    description=_old.description,
                    input_schema=_old.input_schema,
                    output_schema=_old.output_schema,
                    read_only=_old.read_only,
                    handler=_handler_fn,
                )
        # Wave-16-C handlers (#2157 Stale Context MCP)
        _wave16c_handler_map = {
            "cdb_context_stale": cdb_context_stale_handler,
        }
        for _tool_name, _handler_fn in _wave16c_handler_map.items():
            _old = self._registry.get_tool(_tool_name)
            if _old:
                self._registry._tools[_tool_name] = ToolDefinition(
                    name=_old.name,
                    description=_old.description,
                    input_schema=_old.input_schema,
                    output_schema=_old.output_schema,
                    read_only=_old.read_only,
                    handler=_handler_fn,
                )
        # Wave-17-C handlers (#2165 Scope Drift MCP)
        _wave17c_handler_map = {
            "cdb_context_scope_drift": cdb_context_scope_drift_handler,
        }
        for _tool_name, _handler_fn in _wave17c_handler_map.items():
            _old = self._registry.get_tool(_tool_name)
            if _old:
                self._registry._tools[_tool_name] = ToolDefinition(
                    name=_old.name,
                    description=_old.description,
                    input_schema=_old.input_schema,
                    output_schema=_old.output_schema,
                    read_only=_old.read_only,
                    handler=_handler_fn,
                )
        # Wave-18 handlers (#2173 Quality Score MCP, #2175 Architect Signals MCP)
        _wave18_handler_map = {
            "cdb_context_quality_score": cdb_context_quality_score_handler,
            "cdb_context_architect_signals": cdb_context_architect_signals_handler,
        }
        for _tool_name, _handler_fn in _wave18_handler_map.items():
            _old = self._registry.get_tool(_tool_name)
            if _old:
                self._registry._tools[_tool_name] = ToolDefinition(
                    name=_old.name,
                    description=_old.description,
                    input_schema=_old.input_schema,
                    output_schema=_old.output_schema,
                    read_only=_old.read_only,
                    handler=_handler_fn,
                )
        self._registry.assert_read_only_consistency()
        logger.info(
            f"ContextBridge initialized with tools: {self._registry.list_tool_names()}"
        )

    def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools with their definitions.

        Returns defensive copies of schema dictionaries to prevent
        caller mutations from affecting registry definitions.
        """
        tools = []
        for tool in self._registry.list_tools():
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": deepcopy(tool.input_schema),
                    "outputSchema": deepcopy(tool.output_schema),
                    "readOnly": tool.read_only,
                }
            )
        return tools

    def get_tool_schema(self, tool_name: str) -> Optional[dict[str, Any]]:
        """Get the schema for a specific tool.

        Returns defensive copies of schema dictionaries to prevent
        caller mutations from affecting registry definitions.
        """
        tool = self._registry.get_tool(tool_name)
        if tool is None:
            return None
        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": deepcopy(tool.input_schema),
            "outputSchema": deepcopy(tool.output_schema),
            "readOnly": tool.read_only,
        }

    def execute_tool(
        self, tool_name: str, parameters: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Execute a tool with the given parameters.

        All tools are read-only and fail-closed.
        If a tool is not yet implemented, it returns an error response.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool-specific parameters

        Returns:
            Tool execution result
        """
        tool = self._registry.get_tool(tool_name)
        if tool is None:
            return {
                "tool": tool_name,
                "status": "error",
                "error": {
                    "code": "unknown_tool",
                    "message": f"Unknown tool: {tool_name}",
                },
            }

        if not tool.read_only:
            return {
                "tool": tool_name,
                "status": "error",
                "error": {
                    "code": "write_not_allowed",
                    "message": f"Tool {tool_name} is not read-only and cannot be executed",
                },
            }

        if parameters is None:
            parameters = {}
        elif not isinstance(parameters, dict):
            return {
                "tool": tool_name,
                "status": "error",
                "error": {
                    "code": "invalid_parameters",
                    "message": (
                        f"Tool {tool_name} called with non-dict parameters: "
                        f"got {type(parameters).__name__}. "
                        "Parameters must be a dict."
                    ),
                },
            }

        # Input Gate (#2099): scan parameters for forbidden patterns
        input_violations = PermissionGuard.check_tool_inputs(
            tool_name, parameters
        )
        if input_violations:
            first = input_violations[0]
            return {
                "tool": tool_name,
                "status": "error",
                "error": {
                    "code": first.code,
                    "message": first.message,
                    "details": first.details,
                    "all_violations": [
                        {"code": v.code, "message": v.message, "details": v.details}
                        for v in input_violations
                    ],
                },
            }
        try:
            result = tool.handler(**parameters)
            return result
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}")
            return {
                "tool": tool_name,
                "status": "error",
                "error": {
                    "code": "execution_error",
                    "message": str(e),
                },
            }

    def get_read_only_status(self) -> dict[str, Any]:
        """Return the read-only enforcement status."""
        return {
            "enforced": True,
            "description": "All Context MCP tools are read-only. Write operations are not permitted.",
            "tools_count": len(self._registry.list_tools()),
            "read_only_tools": [
                t.name for t in self._registry.list_tools() if t.read_only
            ],
        }


def create_bridge() -> ContextBridge:
    """Factory function to create a ContextBridge instance."""
    return ContextBridge()
