import asyncio
from mcp import Client

SERVER_URL = "https://rag-pipe-mcp-p-mcp-server-peiqbzghaq-ez.a.run.app/mcp"
#"https://rag-pipe-mcp-dev-mcp-server-ncdlcaaczq-ez.a.run.app/mcp"

QUESTIONS = [
    "What are the themes of the essays in hashiya?",
    "What artists did RM work with for his collab exxhibition with SFMOMA?",
    "What is Willow Smith's take on mastery?",
]


async def main() -> None:
    async with Client(SERVER_URL) as client:
        for question in QUESTIONS:
            result = await client.call_tool("query_rag_pipeline", {"question": question})
            print(f"Q: {question}")
            print(result)
            print("---")


if __name__ == "__main__":
    asyncio.run(main())