import os
import asyncio
from mistralai.client import Mistral

client = Mistral(api_key=os.environ["MISTRALAI_API_KEY"])

async def main() -> None:
    # 1. Register your MCP server as a Connector (one-time setup)
    connector = await client.beta.connectors.create_async(
        name="rag_pipeline_mcp_dev",
        description="RAG pipeline over some articles and publications",
        server="https://rag-pipe-mcp-dev-mcp-server-ncdlcaaczq-ez.a.run.app/mcp",#"https://rag-pipe-mcp-mcp-server-514728048358.europe-west4.run.app/mcp",
        visibility="private",
    )
    print(f"Connector created: {connector.id}")

    # 2. Authenticate with empty credentials (no auth required on your server)
    await client.beta.connectors.create_or_update_user_credentials_async(
        connector_id_or_name=connector.id,
        name="no-auth",
        credentials={"headers": {}},
        is_default=True,
    )

    # 3. Use it in a conversation
    response = await client.beta.conversations.start_async(
        model="mistral-small-latest",
        inputs=[
            {
                "role": "user",
                "content": "What was SFMOMA's goal with the RM colab exhibition? Use the RAG tool to find out.",
            }
        ],
        tools=[
            {"type": "connector", "connector_id": connector.id},
        ],
    )

    for output in response.outputs:
        if output.type == "message.output":
            print(output.content)


asyncio.run(main())