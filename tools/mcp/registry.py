"""
Context MCP Tool Registry.

Defines the registry of read-only Context Tools v0.
Each tool is mapped to its contract and handler placeholder.

Reference: docs/surrealdb/context-tool-contracts-v0.md
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    read_only: bool
    handler: Optional[Callable] = None


class ContextToolRegistry:
    """
    Registry for Context MCP tools.

    All tools are read-only by default.
    Write tools are not registered.

    Defense in depth (#2099):
    - register() blocks non-read-only tools at registration time.
    - assert_read_only_consistency() verifies post-init integrity
      after handler replacements, catching any bypass that sets
      read_only=False on an existing tool.
    """

    _tools: dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, tool: ToolDefinition) -> None:
        if not tool.read_only:
            raise ValueError(f"Cannot register non-read-only tool: {tool.name}")
        cls._tools[tool.name] = tool

    @classmethod
    def get_tool(cls, name: str) -> Optional[ToolDefinition]:
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> list[ToolDefinition]:
        return list(cls._tools.values())

    @classmethod
    def list_tool_names(cls) -> list[str]:
        return list(cls._tools.keys())

    @classmethod
    def assert_read_only_consistency(cls) -> None:
        """Post-init guard: verify all tools in the registry are read-only.

        Called after ContextBridge.__init__() handler replacements to
        catch any unexpected read_only=False that bypassed register().

        Raises ValueError if any tool is not read-only.
        """
        non_read_only = [
            name for name, tool in cls._tools.items() if not tool.read_only
        ]
        if non_read_only:
            raise ValueError(
                f"Registry consistency violation: non-read-only tools found: "
                f"{non_read_only}. All Context MCP tools must be read-only."
            )


def create_not_implemented_handler(tool_name: str) -> Callable:
    """Create a fail-closed handler for not-yet-implemented tools."""

    def not_implemented_handler(**kwargs) -> dict:
        return {
            "tool": tool_name,
            "status": "error",
            "error": {
                "code": "not_implemented",
                "message": f"Tool {tool_name} is not yet implemented. This is a scaffold placeholder.",
            },
        }

    return not_implemented_handler


# Tool definitions for Context Tools v0
# Reference: docs/surrealdb/context-tool-contracts-v0.md

TOOLS_V0 = [
    ToolDefinition(
        name="context.search",
        description="Search the Context Intelligence knowledge base using keyword and structured queries.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
                "filters": {
                    "type": "object",
                    "properties": {
                        "source_types": {"type": "array", "items": {"type": "string"}},
                        "date_from": {"type": "string"},
                        "date_to": {"type": "string"},
                    },
                },
            },
            "required": ["query"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "results": {"type": "array"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.search"),
    ),
    ToolDefinition(
        name="context.trace",
        description="Trace decision or event lineage through the Context Intelligence system.",
        input_schema={
            "type": "object",
            "properties": {
                "target_id": {"type": "string"},
                "depth": {"type": "integer", "default": 5, "maximum": 20},
            },
            "required": ["target_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "trace": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.trace"),
    ),
    ToolDefinition(
        name="context.explain_source",
        description="Explain the provenance and reasoning behind a specific source or evidence item.",
        input_schema={
            "type": "object",
            "properties": {
                "source_ref": {"type": "string"},
                "include_chain": {"type": "boolean", "default": True},
            },
            "required": ["source_ref"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "explanation": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.explain_source"),
    ),
    ToolDefinition(
        name="context.show_snapshot",
        description="Show a point-in-time snapshot of the context state.",
        input_schema={
            "type": "object",
            "properties": {
                "snapshot_id": {"type": "string"},
                "include_details": {"type": "boolean", "default": True},
            },
            "required": ["snapshot_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "snapshot": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.show_snapshot"),
    ),
    ToolDefinition(
        name="context.show_audit",
        description="Show deterministic registry audit snapshot for a target tool (no DB/network).",
        input_schema={
            "type": "object",
            "properties": {
                "target_tool": {
                    "type": "string",
                    "description": "Target tool name to audit (preferred).",
                },
                "entity_id": {
                    "type": "string",
                    "description": "Deprecated alias for target_tool (backward compatible).",
                },
                "audit_type": {"type": "string", "default": "all"},
                "limit": {"type": "integer", "default": 50},
            },
            "anyOf": [{"required": ["target_tool"]}, {"required": ["entity_id"]}],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "audit": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.show_audit"),
    ),
    ToolDefinition(
        name="context.package",
        description="Package context artifacts for handoff between agents or sessions.",
        input_schema={
            "type": "object",
            "properties": {
                "artifacts": {"type": "array", "items": {"type": "string"}},
                "format": {
                    "type": "string",
                    "enum": ["json", "markdown"],
                    "default": "json",
                },
                "include_metadata": {"type": "boolean", "default": True},
            },
            "required": ["artifacts"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "package": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.package"),
    ),
    ToolDefinition(
        name="context.readiness",
        description="Assess agent action readiness for a given task scope. Read-only, fails closed. Requires task_scope and operation_mode.",
        input_schema={
            "type": "object",
            "properties": {
                "task_scope": {
                    "type": "string",
                    "description": "What the agent is asked to do (one concise sentence).",
                },
                "target_issue": {
                    "type": ["string", "null"],
                    "description": "GitHub issue driving the task, or null for exploratory.",
                },
                "target_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File paths or glob patterns in scope.",
                },
                "operation_mode": {
                    "type": "string",
                    "enum": [
                        "read_only",
                        "dry_run",
                        "write (code/docs)",
                        "write (config/infra)",
                        "write (DB/migration)",
                        "write (MCP live)",
                    ],
                    "description": "Operational mode for the task.",
                },
                "context_package_ref": {
                    "type": ["string", "null"],
                    "description": "Reference to an assembled Context Package.",
                },
                "required_reads": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Canonical files the agent must read before acting.",
                },
                "evidence_refs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "References to evidence sources backing core assumptions.",
                },
                "impact_refs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Issues/PRs/paths impacted by the proposed action.",
                },
                "stop_conditions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Known stop conditions that would abort the task.",
                },
                "uncertainties": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Explicitly acknowledged unknowns or assumptions.",
                },
            },
            "required": ["task_scope", "operation_mode"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "readiness": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": [
                                "ready_for_read_only",
                                "ready_for_dry_run",
                                "ready_for_human_go",
                                "blocked_missing_context",
                                "blocked_missing_evidence",
                                "blocked_scope_drift",
                            ],
                        },
                        "reasons": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "required_next_reads": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "human_go_required": {"type": "boolean"},
                        "stop_conditions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "missing_context": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "missing_evidence": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "scope_drift_findings": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "uncertainties": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "guardrails": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.readiness"),
    ),
    ToolDefinition(
        name="context.self_explain",
        description="Generate a structured self-explanation for governance-relevant conditions. Read-only, no action authorization, no Live-Go, no Echtgeld-Go.",
        input_schema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question or condition to explain.",
                },
                "explanation_type": {
                    "type": "string",
                    "enum": [
                        "why_blocked",
                        "why_risky",
                        "why_stale",
                        "why_decision_current",
                        "why_decision_superseded",
                        "why_scope_blocked",
                        "why_evidence_weak",
                        "why_agent_needs_go",
                        "why_doc_untrusted",
                    ],
                },
                "scope": {"type": "string"},
                "evidence_refs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "reasons": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "confidence": {
                    "type": ["number", "null"],
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "recommended_next_reads": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["question", "explanation_type", "evidence_refs"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "explanation": {"type": "object"},
                "source_refs": {"type": "array"},
                "evidence_refs": {"type": "array"},
                "graph_path": {"type": "array"},
                "confidence": {"type": ["number", "null"]},
                "recommended_next_reads": {"type": "array"},
                "guardrails": {"type": "array"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.self_explain"),
    ),
    ToolDefinition(
        name="context.briefing",
        description="Generate a task-specific Agent Briefing v1 from Briefing Request schema (docs/surrealdb/context-agent-briefing-schema-v1.md). Delegates to context.readiness and context.package for context assembly. Read-only, no authorization, no Live/Echtgeld Go.",
        input_schema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Unique task identifier. Convention: cdb-briefing-<issue>-<short-slug>.",
                },
                "target_issue": {
                    "type": ["string", "null"],
                    "description": "GitHub issue number driving the task, or null for exploratory.",
                },
                "task_scope": {
                    "type": "string",
                    "description": "What the agent is asked to do (one concise sentence).",
                },
                "target_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File paths or glob patterns in scope.",
                },
                "target_symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Code symbols relevant to the task.",
                },
                "target_concepts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domain concepts from the CIS ontology relevant to the task.",
                },
                "requested_depth": {
                    "type": "string",
                    "enum": ["quick", "standard", "deep"],
                    "description": "Briefing depth.",
                },
                "operation_mode": {
                    "type": "string",
                    "enum": [
                        "read_only",
                        "dry_run",
                        "write (code/docs)",
                        "write (config/infra)",
                        "write (DB/migration)",
                        "write (MCP live)",
                    ],
                    "description": "Intended agent operation mode.",
                },
                "agent_type": {
                    "type": "string",
                    "description": "Agent identifier (e.g. OPENCODE/codex, GEMINI, CLAUDE).",
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Pre-assessed risk level of the task.",
                },
                "repo_state": {
                    "type": "object",
                    "description": "Optional caller-provided repo session state.",
                },
                "github_state": {
                    "type": "object",
                    "description": "Optional caller-provided GitHub session state.",
                },
                "brain_source": {
                    "type": "string",
                    "enum": [
                        "repo-only",
                        "in_memory",
                        "surrealdb-local",
                        "unavailable",
                    ],
                    "description": "Optional session memory source classification.",
                },
                "brain_status": {
                    "type": "string",
                    "enum": ["used", "partial", "not-used", "blocked"],
                    "description": "Optional session memory usage status.",
                },
                "working_assumptions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional short-lived assumptions supplied by the caller.",
                },
                "limitations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional session limitations supplied by the caller.",
                },
            },
            "required": [
                "task_id",
                "task_scope",
                "target_issue",
                "requested_depth",
                "operation_mode",
            ],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "briefing": {
                    "type": "object",
                    "properties": {
                        "briefing_id": {"type": "string"},
                        "enrichment_id": {"type": "string"},
                        "enriched_briefing_id": {"type": "string"},
                        "scope_summary": {"type": "string"},
                        "trust_summary": {"type": "string"},
                        "context_package_ref": {"type": ["string", "null"]},
                        "required_reads": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "relevant_artifacts": {"type": "array"},
                        "relevant_symbols": {"type": "array"},
                        "relevant_docs": {"type": "array"},
                        "relevant_decisions": {"type": "array"},
                        "relevant_evidence": {"type": "array"},
                        "enriched_decisions": {"type": "array"},
                        "enriched_evidence": {"type": "array"},
                        "enriched_memory": {"type": "array"},
                        "enriched_stop_conditions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "stale_evidence_notice": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "contradictory_evidence_notice": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "missing_evidence_notice": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "session_context": {
                            "type": "object",
                            "properties": {
                                "memory_type": {"type": "string"},
                                "session_only": {"type": "boolean"},
                                "ttl_seconds": {"type": "integer"},
                                "brain_source": {"type": "string"},
                                "brain_status": {"type": "string"},
                                "repo_state": {"type": "object"},
                                "github_state": {"type": "object"},
                                "agent_operating_mode": {"type": "object"},
                                "working_assumptions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "limitations": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                        "dependency_paths": {"type": "array"},
                        "known_risks": {"type": "array", "items": {"type": "string"}},
                        "guardrails": {"type": "array", "items": {"type": "string"}},
                        "stop_conditions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "validation_plan": {"type": "array"},
                        "unresolved_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "human_go_required": {"type": "boolean"},
                    },
                },
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.briefing"),
    ),
    ToolDefinition(
        name="context.stop_resolver",
        description="Resolve flat stop-condition strings to typed stop condition objects. Read-only, deterministic, fail-closed. No DB/network/GitHub access.",
        input_schema={
            "type": "object",
            "properties": {
                "stop_conditions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Flat stop condition strings to resolve (S1-S10, H1-H8 patterns).",
                },
                "warnings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional warning strings to scan for secrets/live/runtime keywords.",
                },
                "readiness_result": {
                    "type": "object",
                    "description": "Optional readiness result from context.readiness for additional stop conditions.",
                },
                "operation_mode": {
                    "type": "string",
                    "enum": [
                        "read_only",
                        "dry_run",
                        "write (code/docs)",
                        "write (config/infra)",
                        "write (DB/migration)",
                        "write (MCP live)",
                    ],
                    "description": "Operation mode affecting severity of some conditions.",
                    "default": "read_only",
                },
            },
            "required": [],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "resolved": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": [
                                    "missing_context",
                                    "missing_evidence",
                                    "scope_drift_risk",
                                    "runtime_surface_touched",
                                    "trading_surface_touched",
                                    "write_requires_human_go",
                                    "stale_context",
                                    "contradiction_risk",
                                    "forbidden_path",
                                    "secrets_risk",
                                ],
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["info", "warning", "blocking"],
                            },
                            "reason": {"type": "string"},
                            "required_action": {"type": "string"},
                            "human_go_required": {"type": "boolean"},
                        },
                    },
                },
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.stop_resolver"),
    ),
    ToolDefinition(
        name="context.required_reads",
        description="Resolve prioritized required reads from task scope, target issue, target paths, target symbols, and operation mode. Read-only, deterministic, fail-closed. No DB/network/GitHub access.",
        input_schema={
            "type": "object",
            "properties": {
                "task_scope": {
                    "type": "string",
                    "description": "What the agent is asked to do (one concise sentence). Required.",
                },
                "target_issue": {
                    "type": ["string", "null"],
                    "description": "GitHub issue number driving the task, or null for exploratory.",
                },
                "target_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File paths or glob patterns in scope.",
                },
                "target_symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Code symbols relevant to the task.",
                },
                "operation_mode": {
                    "type": "string",
                    "enum": [
                        "read_only",
                        "dry_run",
                        "write (code/docs)",
                        "write (config/infra)",
                        "write (DB/migration)",
                        "write (MCP live)",
                    ],
                    "description": "Intended agent operation mode. Required.",
                },
                "target_concepts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domain concepts from the CIS ontology relevant to the task.",
                },
            },
            "required": ["task_scope", "target_issue", "operation_mode"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "resolved_reads": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["must_read", "should_read", "optional"],
                            },
                            "reason": {"type": "string"},
                            "source_ref": {"type": "string"},
                            "available": {"type": "boolean"},
                            "warning": {"type": ["string", "null"]},
                        },
                        "required": [
                            "path",
                            "priority",
                            "reason",
                            "source_ref",
                            "available",
                            "warning",
                        ],
                    },
                },
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.required_reads"),
    ),
    ToolDefinition(
        name="cdb_context_impact",
        description=(
            "Impact Radar v1 MCP tool. Analyses downstream effects of a planned change "
            "across the CDB system. Returns affected items, graph paths, gate risks, "
            "required validation, and stop conditions. Read-only, deterministic, fail-closed. "
            "No DB/network/GitHub access. Does not authorize any action, Live-Go, or Echtgeld-Go."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "target_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File paths or glob patterns targeted by the planned change.",
                },
                "target_symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Code symbols targeted by the planned change.",
                },
                "target_issue": {
                    "type": ["string", "null"],
                    "description": "GitHub issue driving the planned change, or null.",
                },
                "target_concepts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domain concepts from the CIS ontology relevant to the change.",
                },
                "operation_mode": {
                    "type": "string",
                    "enum": [
                        "read_only",
                        "dry_run",
                        "write (code/docs)",
                        "write (config/infra)",
                        "write (DB/migration)",
                        "write (MCP live)",
                    ],
                    "description": "Intended agent operation mode for the change.",
                    "default": "read_only",
                },
            },
            "required": [],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "impact": {
                    "type": "object",
                    "properties": {
                        "impact_id": {"type": "string"},
                        "target_refs": {"type": "array", "items": {"type": "string"}},
                        "impact_level": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "blocking"],
                        },
                        "impact_type": {
                            "type": "string",
                            "enum": ["HARD", "SOFT"],
                        },
                        "affected_artifacts": {"type": "array"},
                        "affected_symbols": {"type": "array"},
                        "affected_tests": {"type": "array"},
                        "affected_docs": {"type": "array"},
                        "affected_decisions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "affected_evidence": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "affected_memory_refs_read_only": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "graph_paths": {"type": "array"},
                        "gate_risks": {"type": "array", "items": {"type": "string"}},
                        "confidence": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                        "required_validation": {"type": "object"},
                        "stop_conditions": {"type": "array"},
                        "schema_version": {"type": "string"},
                    },
                    "required": [
                        "impact_id",
                        "impact_level",
                        "impact_type",
                        "gate_risks",
                        "stop_conditions",
                        "required_validation",
                    ],
                },
                "guardrails": {"type": "array", "items": {"type": "string"}},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_impact"),
    ),
    # ── Wave-14 Tools (#2122 Registry/Bridge Completeness) ─────────────────
    ToolDefinition(
        name="cdb_context_evidence_resolve",
        description=(
            "Wave-14 evidence resolve MCP tool. Resolves evidence for artifacts, "
            "claims, and decisions over in-memory records. Read-only, fail-closed, "
            "no DB/network/write. No Live-Go, no Echtgeld-Go."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string"},
                        "artifact": {"type": "string"},
                        "claim": {"type": "string"},
                        "run_id": {"type": "string"},
                        "evidence_type": {"type": "string"},
                        "freshness_days": {"type": "integer"},
                        "min_confidence": {"type": "number"},
                        "evidence_records": {"type": "array"},
                        "limit": {"type": "integer"},
                    },
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "result": {"type": "object"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_evidence_resolve"),
    ),
    ToolDefinition(
        name="cdb_context_claim_resolve",
        description=(
            "Wave-14 claim resolve MCP tool. Resolves claims over in-memory records. "
            "Surfaces disputed/stale/weakly-supported claims. Read-only, fail-closed, "
            "no DB/network/write. No Live-Go, no Echtgeld-Go."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string"},
                        "topic": {"type": "string"},
                        "scope": {"type": "string"},
                        "status": {"type": "string"},
                        "artifact": {"type": "string"},
                        "claim_records": {"type": "array"},
                        "limit": {"type": "integer"},
                    },
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "result": {"type": "object"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_claim_resolve"),
    ),
    ToolDefinition(
        name="cdb_context_memory_get",
        description=(
            "Wave-14 scoped memory read MCP tool. Reads agent memory records "
            "by scope, topic, or agent. Read-only, fail-closed, "
            "no DB/network/write. No Live-Go, no Echtgeld-Go."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string"},
                        "scope": {"type": "string"},
                        "topic": {"type": "string"},
                        "agent": {"type": "string"},
                        "memory_records": {"type": "array"},
                        "limit": {"type": "integer"},
                    },
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "result": {"type": "object"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_memory_get"),
    ),
    ToolDefinition(
        name="cdb_context_memory_write_intent",
        description=(
            "Memory write intent gate MCP tool (dry-run default). Evaluates "
            "Human-GO memory write authorization against the memory contract. "
            "Read-only, fail-closed, no DB/network/write execution. "
            "Mutation flags blocked. No Live-Go, no Echtgeld-Go."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "record": {"type": "object"},
                        "memory_record": {"type": "object"},
                        "authorization": {"type": "object"},
                        "operation_mode": {
                            "type": "string",
                            "enum": [
                                "dry_run",
                                "audit_persist_local",
                                "audit_persist_productive",
                                "agent_memory_write",
                            ],
                        },
                        "dry_run": {"type": "boolean", "default": True},
                    },
                    "required": ["record"],
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "result": {"type": "object"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_memory_write_intent"),
    ),
    ToolDefinition(
        name="cdb_context_trust_summary",
        description=(
            "Wave-14 trust summary MCP tool. Builds a trust assessment from "
            "evidence, claim, decision, and memory results. Read-only, fail-closed, "
            "no DB/network/write. No Live-Go, no Echtgeld-Go."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scope": {"type": "string"},
                        "topic": {"type": "string"},
                        "artifact": {"type": "string"},
                        "evidence_result": {"type": "object"},
                        "claim_result": {"type": "object"},
                        "decision_result": {"type": "object"},
                        "memory_result": {"type": "object"},
                    },
                    "required": ["scope"],
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "result": {"type": "object"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_trust_summary"),
    ),
    ToolDefinition(
        name="cdb_context_decision_history",
        description=(
            "Wave-14 decision history MCP tool. Queries decision history over "
            "in-memory decision event records. Read-only, fail-closed, "
            "no DB/network/write. No Live-Go, no Echtgeld-Go."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string"},
                        "topic": {"type": "string"},
                        "scope": {"type": "string"},
                        "decision_id": {"type": "string"},
                        "issue": {"type": "string"},
                        "status": {"type": "string"},
                        "decision_events": {"type": "array"},
                        "limit": {"type": "integer"},
                    },
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "result": {"type": "object"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_decision_history"),
    ),
    ToolDefinition(
        name="cdb_context_decision_replay",
        description=(
            "Wave-14 decision replay MCP tool. Builds a decision replay "
            "from decision event records. Read-only, fail-closed, "
            "no DB/network/write. No Live-Go, no Echtgeld-Go."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string"},
                        "decision_id": {"type": "string"},
                        "topic": {"type": "string"},
                        "decision_events": {"type": "array"},
                        "limit": {"type": "integer"},
                    },
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "result": {"type": "object"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_decision_replay"),
    ),
    # ── Wave-15 Tools (#2148 Contradiction MCP) ─────────────────────────────
    ToolDefinition(
        name="cdb_context_contradictions",
        description=(
            "Wave-15 contradiction scan MCP tool. Detects contradictions between "
            "doc/code/decisions/evidence/claims/memory over in-memory records. "
            "Surfaces SourceRefs, EvidenceRefs, severity, confidence, and "
            "recommended_next_reads. Read-only, fail-closed, no DB/network/write. "
            "No Live-Go, no Echtgeld-Go. Detection is signal, not action permission."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "records": {
                            "type": "object",
                            "description": (
                                "In-memory input bundles keyed by domain "
                                "(e.g. doc_claims, code_symbols, decisions, claims, "
                                "evidence_records, etc.). Required."
                            ),
                        },
                        "scope": {"type": "string"},
                        "artifact": {"type": "string"},
                        "decision": {"type": "string"},
                        "claim": {"type": "string"},
                        "overrides": {
                            "type": "object",
                            "description": (
                                "Optional dict[contradiction_id → "
                                "'false_positive'|'accepted_risk'] to mark known "
                                "overrides. Findings are retained but set non-blocking."
                            ),
                        },
                        "include_non_blocking": {
                            "type": "boolean",
                            "default": True,
                        },
                        "types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter to these contradiction_type values.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max number of findings to return.",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json"],
                            "description": "Output format. Reserved; always returns dict.",
                        },
                    },
                    "required": ["records"],
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "scope": {"type": ["string", "null"]},
                "artifact": {"type": ["string", "null"]},
                "decision": {"type": ["string", "null"]},
                "claim": {"type": ["string", "null"]},
                "total_findings": {"type": "integer"},
                "blocking_count": {"type": "integer"},
                "findings": {"type": "array"},
                "recommended_next_reads": {"type": "array"},
                "guardrails": {"type": "array"},
                "no_live_go": {"type": "boolean"},
                "no_write": {"type": "boolean"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_contradictions"),
    ),
    # ── Wave-16-C Tools (#2157 Stale Context MCP) ────────────────────────────
    ToolDefinition(
        name="cdb_context_stale",
        description=(
            "Wave-16-C stale context MCP tool. Detects stale knowledge findings "
            "from an in-memory input bundle. Surfaces stale_type, severity, "
            "confidence, recommended_refresh, and source_refs for each finding. "
            "Supports scope/stale_type/severity/target_ref filters and limit. "
            "Bundle-driven: no DB/network/filesystem read. Read-only, fail-closed. "
            "Detection is signal, not authorization. No Live-Go, no Echtgeld-Go, "
            "no auto-fix, no auto-delete, no write."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "bundle": {
                    "type": "object",
                    "description": (
                        "In-memory scan input bundle with domain keys "
                        "(sources, decisions, evidence_records, memory_records, "
                        "dependency_edges, context_packages, briefings). Required."
                    ),
                },
                "scope": {
                    "type": "string",
                    "enum": [
                        "all",
                        "artifact",
                        "decision",
                        "evidence",
                        "memory",
                        "edge",
                        "package",
                        "briefing",
                    ],
                    "default": "all",
                    "description": (
                        "Restrict scan to a subset of stale_types. "
                        "'all' returns all types (default)."
                    ),
                },
                "target_ref": {
                    "type": "string",
                    "description": "Exact target_ref to filter findings by.",
                },
                "stale_type": {
                    "type": "string",
                    "description": (
                        "Exact stale_type to filter findings by. "
                        "Must be one of the 8 canonical stale types."
                    ),
                },
                "severity": {
                    "type": "string",
                    "enum": ["info", "warning", "blocking"],
                    "description": "Severity level to filter findings by.",
                },
                "include_guardrails": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include guardrail strings in output.",
                },
                "limit": {
                    "type": "integer",
                    "default": 100,
                    "maximum": 500,
                    "description": (
                        "Maximum number of findings to return. "
                        "Summary counts are always pre-limit. "
                        "summary.truncated=true when findings are capped."
                    ),
                },
                "as_of": {
                    "type": "string",
                    "description": (
                        "Optional ISO-8601 UTC reference time for TTL/expiry "
                        "comparisons. Also read from bundle['meta']['as_of']. "
                        "If absent, scan service uses cdb_utcnow()."
                    ),
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "schema_version": {"type": "string"},
                "status": {"type": "string"},
                "summary": {
                    "type": "object",
                    "properties": {
                        "total_count": {"type": "integer"},
                        "blocking_count": {"type": "integer"},
                        "truncated": {"type": "boolean"},
                        "severity_summary": {"type": "object"},
                        "stale_type_summary": {"type": "object"},
                    },
                },
                "findings": {"type": "array"},
                "recommended_refresh": {"type": "array"},
                "source_refs": {"type": "array"},
                "guardrails": {"type": "array"},
                "as_of": {"type": "string"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_stale"),
    ),
    # ── Wave-17-C Tools (#2165 Scope Drift MCP) ──────────────────────────────
    ToolDefinition(
        name="cdb_context_scope_drift",
        description=(
            "Wave-17-C scope drift MCP tool. Detects scope drift findings "
            "from an in-memory input bundle using the Wave-17-A firewall service. "
            "Supports filters for severity, scope_type (drift type), target_ref, "
            "and blocking state. Supports deterministic limit/truncation. "
            "Bundle-driven: no DB/network/filesystem read. Read-only, fail-closed. "
            "Detection is signal, not authorization. No Live-Go, no Echtgeld-Go, "
            "no auto-fix, no write."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "bundle": {
                    "type": "object",
                    "description": (
                        "In-memory scan input bundle with domain keys "
                        "(declared_scope, touched_artifacts, issue_refs, "
                        "generated_findings, forbidden_surfaces). Required."
                    ),
                },
                "severity": {
                    "type": "string",
                    "enum": ["info", "warning", "blocking"],
                    "description": "Severity level to filter findings by.",
                },
                "scope_type": {
                    "type": "string",
                    "description": (
                        "Exact drift_type to filter findings by. "
                        "Must be one of the 9 canonical drift types."
                    ),
                },
                "target_ref": {
                    "type": "string",
                    "description": (
                        "Filter to findings whose affected_artifacts contains "
                        "this reference string."
                    ),
                },
                "blocking": {
                    "type": "boolean",
                    "description": (
                        "true: return only blocking findings (human_go_required=true). "
                        "false: return only non-blocking findings."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "default": 100,
                    "maximum": 500,
                    "description": (
                        "Maximum number of findings to return. "
                        "Summary counts are always pre-limit. "
                        "summary.truncated=true when findings are capped."
                    ),
                },
                "as_of": {
                    "type": "string",
                    "description": (
                        "Optional ISO-8601 UTC reference time. "
                        "Also read from bundle['meta']['as_of']. "
                        "If absent, scan service uses cdb_utcnow()."
                    ),
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "schema_version": {"type": "string"},
                "status": {"type": "string"},
                "summary": {
                    "type": "object",
                    "properties": {
                        "total_count": {"type": "integer"},
                        "blocking_count": {"type": "integer"},
                        "truncated": {"type": "boolean"},
                        "severity_summary": {"type": "object"},
                        "drift_type_summary": {"type": "object"},
                        "filters_applied": {"type": "object"},
                    },
                },
                "findings": {"type": "array"},
                "guardrails": {"type": "array"},
                "scan_status": {"type": "string"},
                "scanned_at": {"type": "string"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_scope_drift"),
    ),
    # Wave-18: Knowledge Quality Scoring MCP tool (#2173)
    ToolDefinition(
        name="cdb_context_quality_score",
        description=(
            "Score the quality of a knowledge context bundle across 8 dimensions "
            "(coverage, freshness, evidence, contradiction, dependency confidence, "
            "memory trust, decision validity, scope risk). Returns overall grade "
            "(blocking/watch/weak/good) and per-dimension scores. "
            "Read-only, bundle-driven, fail-closed. No DB/network/writes."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "bundle": {
                    "type": "object",
                    "description": "Quality scoring bundle containing sources, decisions, evidence, findings.",
                },
                "dimension": {
                    "type": ["string", "null"],
                    "description": "Return only a single score dimension.",
                },
                "min_grade": {
                    "type": ["string", "null"],
                    "enum": ["blocking", "watch", "weak", "good", None],
                    "description": "Return only dimensions at or below this grade.",
                },
                "limit": {
                    "type": "integer",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum number of dimensions to return.",
                },
                "as_of": {
                    "type": ["string", "null"],
                    "description": "Advisory ISO-8601 UTC timestamp for the scoring run.",
                },
            },
            "required": ["bundle"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "schema_version": {"type": "string"},
                "status": {"type": "string"},
                "scope_id": {"type": "string"},
                "level": {"type": "string"},
                "scored_at": {"type": "string"},
                "overall_score": {"type": "number"},
                "overall_grade": {"type": "string"},
                "blocking_dimensions": {"type": "array"},
                "watch_dimensions": {"type": "array"},
                "recommended_next_reads": {"type": "array"},
                "dimensions": {"type": "array"},
                "guardrails": {"type": "array"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_quality_score"),
    ),
    # Wave-18: Architect Signals MCP tool (#2175)
    ToolDefinition(
        name="cdb_context_architect_signals",
        description=(
            "Detect proactive architect signals from a context bundle. "
            "Generates 11 signal types: stale_area, weakly_evidenced_decision, "
            "underdocumented_surface, undertested_surface, high_dependency_risk, "
            "contradiction_hotspot, scope_drift_hotspot, repeated_agent_confusion, "
            "redundant_docs, missing_owner, fragile_context_path. "
            "Read-only, bundle-driven, fail-closed. No DB/network/writes. "
            "No automatic issue creation. Human-GO required for blocking signals."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "bundle": {
                    "type": "object",
                    "description": "Context bundle containing sources, decisions, evidence, findings.",
                },
                "signal_type": {
                    "type": ["string", "null"],
                    "description": "Return only signals of this type.",
                },
                "min_severity": {
                    "type": ["string", "null"],
                    "enum": ["info", "watch", "blocking", None],
                    "description": "Return only signals at or above this severity.",
                },
                "limit": {
                    "type": "integer",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum number of signals to return.",
                },
                "as_of": {
                    "type": ["string", "null"],
                    "description": "Advisory ISO-8601 UTC timestamp for the scan.",
                },
            },
            "required": ["bundle"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "schema_version": {"type": "string"},
                "status": {"type": "string"},
                "scope_id": {"type": "string"},
                "scanned_at": {"type": "string"},
                "total_signals": {"type": "integer"},
                "blocking_count": {"type": "integer"},
                "watch_count": {"type": "integer"},
                "signals": {"type": "array"},
                "guardrails": {"type": "array"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_context_architect_signals"),
    ),
    # ── Wave-19 Tools (#2180/#2181 Visual Control Room & Reporting Layer) ───
    ToolDefinition(
        name="cdb_control_room_view",
        description=(
            "Wave-19 Visual Control Room View Builder v1. Builds one or all 9 "
            "read-only visual views (knowledge graph, architecture map, decision "
            "chain, evidence map, risk surface, stale knowledge, scope drift, "
            "agent memory, quality score dashboard) from an in-memory bundle. "
            "Read-only, deterministic, fail-closed. No DB/network/write. "
            "No Live-Go. No Echtgeld-Go. No runtime control. Signal surface only."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "bundle": {
                    "type": "object",
                    "description": (
                        "In-memory context bundle (required). Must be a mapping "
                        "with at least a 'meta' key."
                    ),
                },
                "view_type": {
                    "type": ["string", "null"],
                    "description": (
                        "One of: knowledge_graph_view, architecture_map, "
                        "decision_chain_view, evidence_map, risk_surface_report, "
                        "stale_knowledge_view, scope_drift_events, "
                        "agent_memory_view, quality_score_dashboard. "
                        "Omit to build all 9 views."
                    ),
                },
                "filters": {
                    "type": "object",
                    "description": "Optional filter map (key → value) passed to the view builder.",
                },
                "as_of": {
                    "type": ["string", "null"],
                    "description": "Optional ISO-8601 UTC timestamp for deterministic output.",
                },
            },
            "required": ["bundle"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "schema_version": {"type": "string"},
                "status": {"type": "string"},
                "view_type": {"type": "string"},
                "view": {"type": "object"},
                "views": {"type": "array"},
                "view_count": {"type": "integer"},
                "guardrails": {"type": "array"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_control_room_view"),
    ),
    # ── Wave-20 Tools (#2191/#2192 Agent OS Readiness Runtime v1) ───────────
    ToolDefinition(
        name="cdb_agent_os_readiness",
        description=(
            "Wave-20 Agent OS Readiness Evaluator v1. Evaluates the health and "
            "readiness of the Agent OS context intelligence system itself by "
            "aggregating signals from quality scoring, architect signals, scope "
            "drift, contradiction scan, and stale knowledge modules. Returns a "
            "readiness level (blocked/weak/acceptable/strong), blocking findings, "
            "weak findings, missing inputs, confidence, and an optional Markdown "
            "report. Read-only, deterministic, fail-closed. No DB/network/write. "
            "No Live-Go. No Echtgeld-Go. No runtime control. Signal surface only."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "bundle": {
                    "type": "object",
                    "description": (
                        "In-memory context bundle (required). Must be a mapping "
                        "with at least a 'meta' key containing a 'scope_id' string."
                    ),
                },
                "as_of": {
                    "type": ["string", "null"],
                    "description": "Optional ISO-8601 UTC timestamp for deterministic output.",
                },
                "include_report": {
                    "type": "boolean",
                    "description": (
                        "If true, include a 'report_markdown' field with the full "
                        "Markdown readiness report in the response."
                    ),
                },
            },
            "required": ["bundle"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "schema_version": {"type": "string"},
                "status": {"type": "string"},
                "readiness_level": {"type": "string"},
                "result": {"type": "object"},
                "report_markdown": {"type": "string"},
                "guardrails": {"type": "array"},
                "metadata": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("cdb_agent_os_readiness"),
    ),
]


def register_all_tools() -> None:
    """Register all v0 tools with the registry."""
    for tool in TOOLS_V0:
        ContextToolRegistry.register(tool)

    # #2110: Provide a stable alias for the briefing tool without renaming it.
    # The alias schema is deep-copied from context.briefing to prevent drift.
    base = ContextToolRegistry.get_tool("context.briefing")
    if (
        base is not None
        and ContextToolRegistry.get_tool("cdb_context_briefing") is None
    ):
        ContextToolRegistry.register(
            ToolDefinition(
                name="cdb_context_briefing",
                description=(
                    "Alias for context.briefing. Generate a task-specific Agent "
                    "Briefing v1 from Briefing Request schema "
                    "(docs/surrealdb/context-agent-briefing-schema-v1.md). "
                    "Read-only, no authorization, no Live/Echtgeld Go."
                ),
                input_schema=deepcopy(base.input_schema),
                output_schema=deepcopy(base.output_schema),
                read_only=True,
                handler=create_not_implemented_handler("cdb_context_briefing"),
            )
        )


register_all_tools()
