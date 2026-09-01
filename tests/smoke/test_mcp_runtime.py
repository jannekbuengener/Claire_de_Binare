"""
MCP Runtime Smoke Test
Verifies that the CDB Context MCP stdio server can be started and responds to tool calls.

NOTE: This is an environment smoke test to ensure dependencies and basic IPC
(Inter-Process Communication) are functional. It does not provide a semantic
correctness proof for Context Intelligence payloads.
"""

import asyncio
import json
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
@pytest.mark.smoke
async def test_mcp_context_server_runtime():
    """Verify that the CDB Context MCP server is functional and returns expected tools."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "tools.mcp.server"],
        env=None,
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.list_tools()
                tools = result.tools

                tool_names = [t.name for t in tools]
                assert "cdb_context_trust_summary" in tool_names, (
                    "Missing 'cdb_context_trust_summary' tool"
                )

                response = await session.call_tool(
                    "cdb_context_trust_summary",
                    arguments={"scope": "smoke"},
                )

                assert not response.is_error, f"Tool call failed: {response}"
                assert len(response.content) > 0, "Empty response content"

                payload = json.loads(response.content[0].text)
                assert payload["status"] == "ok", f"Unexpected payload: {payload}"
                assert payload["result"]["approval_semantics"]["no_echtgeld_go"] is True

    except Exception as e:
        pytest.fail(
            f"CDB Context MCP server failed to respond or encountered an error: {e}"
        )


if __name__ == "__main__":
    asyncio.run(test_mcp_context_server_runtime())
