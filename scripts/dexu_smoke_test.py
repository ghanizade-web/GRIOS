
import asyncio
import os
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ENDPOINT = "https://mcp.dexu.ai/mcp"


async def main():
    api_key = os.getenv("DEXU_MCP_KEY")

    if not api_key:
        raise RuntimeError("DEXU_MCP_KEY is not configured")

    headers = {"X-MCP-Key": api_key}

    async with streamable_http_client(
        ENDPOINT,
        headers=headers,
    ) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tool_list = await session.list_tools()
            names = [tool.name for tool in tool_list.tools]

            print(f"MCP connection: OK")
            print(f"Discovered tools: {len(names)}")

            required_tool = "get_market_overview"

            if required_tool not in names:
                raise RuntimeError(
                    f"Required tool not available: {required_tool}"
                )

            result = await session.call_tool(
                required_tool,
                {"window": "24h", "limit": 5},
            )

            if result.isError:
                raise RuntimeError("Dexu tool call returned an error")

            print("Read-only market overview call: OK")

            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text[:12000])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"DEXU TEST FAILED: {type(exc).__name__}: {exc}")
        sys.exit(1)
