"""
MCP Runtime Smoke Test
Verifies that the MCP time server can be started and responds to tool calls.
Ensures environment independence by using pinned dependencies.
"""

import asyncio
import pytest
import sys
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
                assert 'get_current_time' in tool_names
                assert 'convert_time' in tool_names

                # Call a tool (deterministic check: response should be successful)
                response = await session.call_tool(
                    'get_current_time',
                    arguments={'timezone': 'UTC'}
                )

                assert not response.isError
                assert len(response.content) > 0
                assert 'UTC' in response.content[0].text
    except Exception as e:
        pytest.fail(f"MCP Time Server failed to respond: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_time_server_runtime())
