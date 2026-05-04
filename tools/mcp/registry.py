"""
Context MCP Tool Registry.

Defines the registry of read-only Context Tools v0.
Each tool is mapped to its contract and handler placeholder.

Reference: docs/surrealdb/context-tool-contracts-v0.md
"""

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
        description="Show audit trail for a specific entity or action.",
        input_schema={
            "type": "object",
            "properties": {
                "entity_id": {"type": "string"},
                "audit_type": {"type": "string", "default": "all"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["entity_id"],
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
]


def register_all_tools() -> None:
    """Register all v0 tools with the registry."""
    for tool in TOOLS_V0:
        ContextToolRegistry.register(tool)


register_all_tools()
