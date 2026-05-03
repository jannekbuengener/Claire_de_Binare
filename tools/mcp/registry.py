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
        description="Show read-only readiness evaluation metadata (NOT Live Readiness).",
        input_schema={
            "type": "object",
            "properties": {
                "component": {"type": "string"},
                "include_details": {"type": "boolean", "default": False},
            },
            "required": ["component"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "status": {"type": "string"},
                "readiness": {"type": "object"},
            },
        },
        read_only=True,
        handler=create_not_implemented_handler("context.readiness"),
    ),
]


def register_all_tools() -> None:
    """Register all v0 tools with the registry."""
    for tool in TOOLS_V0:
        ContextToolRegistry.register(tool)


register_all_tools()
