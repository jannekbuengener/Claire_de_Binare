"""
Context MCP Bridge - Read-only MCP bridge for SurrealDB Context Intelligence.

This package provides an MCP-compatible interface to the Context Intelligence System,
exposing read-only tools for agents without direct table access.

Permission guardrails (#2099):
- Registry Gate: non-read-only ToolDefinitions are blocked at registration.
- Execute Gate: read_only check + input scan before handler dispatch.
- Input Gate: mutative query/operation patterns in tool parameters are blocked.

Note: This is a scaffold implementation. Individual tool handlers are stubs
that fail-closed until implemented in subsequent issues (#2094-#2097).
"""

from tools.mcp.context_bridge import ContextBridge
from tools.mcp.permission_guard import PermissionGuard, PermissionCheckResult

__all__ = ["ContextBridge", "PermissionGuard", "PermissionCheckResult"]
__version__ = "0.1.0"
