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
