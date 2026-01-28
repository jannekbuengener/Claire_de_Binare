"""
MCP Runtime Smoke Test
Verifies that the MCP time server can be started and responds to tool calls.

NOTE: This is an environment smoke test to ensure dependencies and basic IPC
(Inter-Process Communication) are functional. It does not provide a semantic
time correctness proof (e.g., monotonicity or precision).
"""

import asyncio
import pytest
import sys
import re
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@pytest.mark.asyncio
@pytest.mark.smoke
async def test_mcp_time_server_runtime():
    """Verify that the MCP time server is functional and returns expected tools."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=['-m', 'mcp_server_time'],
        env=None
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize session
                await session.initialize()

                # List tools
                result = await session.list_tools()
                tools = result.tools

                tool_names = [t.name for t in tools]
                assert 'get_current_time' in tool_names, "Missing 'get_current_time' tool"
                assert 'convert_time' in tool_names, "Missing 'convert_time' tool"

                # Call a tool
                response = await session.call_tool(
                    'get_current_time',
                    arguments={'timezone': 'UTC'}
                )

                assert not response.isError, f"Tool call failed: {response}"
                assert len(response.content) > 0, "Empty response content"

                text = response.content[0].text
                # Robust format check: expect something like 'Current time in UTC: 2026-01-28 22:00:00'
                # Just checking for ISO-ish date pattern and UTC
                assert 'UTC' in text
                assert re.search(r'\d{4}-\d{2}-\d{2}', text), f"Response does not contain a date: {text}"

    except Exception as e:
        pytest.fail(f"MCP Time Server failed to respond or encountered an error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_time_server_runtime())
