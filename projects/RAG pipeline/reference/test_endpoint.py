"""
Quick test client for the deployed MCP RAG pipeline server.
"""

import asyncio
from mcp import Client

SERVER_URL = "https://rag-pipe-mcp-mcp-server-514728048358.europe-west4.run.app/mcp"


async def main() -> None:
    async with Client(SERVER_URL) as client:
        result = await client.call_tool(
            "query_rag_pipeline",
            {"question": "What roles is this candidate applying for?"},
        )
        print(result)


if __name__ == "__main__":
    asyncio.run(main())