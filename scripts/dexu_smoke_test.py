
import asyncio
import os
import sys

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

ENDPOINT = "https://mcp.dexu.ai/mcp"


async def main():
    api_key = os.getenv("DEXU_MCP_KEY")

    if not api_key:
        raise RuntimeError("DEXU_MCP_KEY is not configured")

    headers = {"X-MCP-Key": api_key}

    timeout = httpx2.Timeout(30.0, read=300.0)

    async with httpx2.AsyncClient(
        headers=headers,
        timeout=timeout,
    ) as http_client:

        transport = streamable_http_client(
            ENDPOINT,
            http_client=http_client,
        )

        async with Client(transport) as client:
            print("MCP connection: OK")

            result = await client.list_tools()
            tools = result.tools

            print(f"Discovered tools: {len(tools)}")

            if not tools:
                raise RuntimeError("Dexu returned no available tools")

            for tool in tools:
                print(f"\nTOOL: {tool.name}")
                print(f"DESCRIPTION: {tool.description or 'N/A'}")
                print(f"INPUT SCHEMA: {tool.inputSchema}")

            print("\nDEXU DISCOVERY TEST: PASSED")
            print("No trading or account-changing action was executed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(
            f"DEXU TEST FAILED: "
            f"{type(exc).__name__}: {exc}"
        )
        sys.exit(1)
