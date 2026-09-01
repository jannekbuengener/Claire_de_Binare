"""
CDB Context MCP stdio server.

Wraps ContextBridge and exposes all registered read-only Context Intelligence
tools via the MCP stdio transport (mcp==2.1.1).

Usage:
    python -m tools.mcp.server

Guardrails:
- All tools are read-only (enforced by ContextBridge + PermissionGuard).
- Default adapter is in-memory/noop; no Docker or SurrealDB required to start.
- DB-backed mode is explicit opt-in: pass ``adapter_config_path`` per tool call.
- No schema apply, no import, no reset, no writes, no remote DB connections.
- LR remains NO-GO.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Sequence

from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)

from tools.mcp.context_bridge import create_bridge

logger = logging.getLogger(__name__)

_bridge = create_bridge()


async def list_tools() -> list[Tool]:
    """Return all registered read-only Context Intelligence tools."""
    return [
        Tool(
            name=t["name"],
            description=t.get("description", ""),
            inputSchema=t.get("inputSchema", {"type": "object", "properties": {}}),
        )
        for t in _bridge.list_tools()
    ]


async def call_tool(
    name: str, arguments: dict[str, Any]
) -> Sequence[TextContent]:
    """Dispatch a tool call to ContextBridge.execute_tool()."""
    result = _bridge.execute_tool(name, arguments or {})
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def _handle_list_tools(
    ctx: ServerRequestContext,
    params: PaginatedRequestParams | None,
) -> ListToolsResult:
    return ListToolsResult(tools=await list_tools())


async def _handle_call_tool(
    ctx: ServerRequestContext,
    params: CallToolRequestParams,
) -> CallToolResult:
    content = await call_tool(params.name, params.arguments or {})
    return CallToolResult(content=list(content), isError=False)


_server = Server(
    "cdb-context",
    instructions=(
        "Read-only CDB Context Intelligence tools. "
        "No writes, no live trading, no Echtgeld scope. "
        "LR=NO-GO."
    ),
    on_list_tools=_handle_list_tools,
    on_call_tool=_handle_call_tool,
)


async def _main() -> None:
    options = _server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(read_stream, write_stream, options)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
