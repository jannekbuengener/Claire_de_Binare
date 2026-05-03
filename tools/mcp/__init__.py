"""
Context MCP Bridge - Read-only MCP bridge for SurrealDB Context Intelligence.

This package provides an MCP-compatible interface to the Context Intelligence System,
exposing read-only tools for agents without direct table access.

Note: This is a scaffold implementation. Individual tool handlers are stubs
that fail-closed until implemented in subsequent issues (#2094-#2097).
"""

from tools.mcp.context_bridge import ContextBridge

__all__ = ["ContextBridge"]
__version__ = "0.0.0"
