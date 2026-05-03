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
from copy import deepcopy
from typing import Any, Optional

from tools.mcp.registry import ContextToolRegistry, ToolDefinition

logger = logging.getLogger(__name__)


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

        parameters = parameters or {}
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
