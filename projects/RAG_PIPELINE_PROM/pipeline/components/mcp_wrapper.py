"""
MCP server exposing the RAG pipeline as a callable tool over Streamable HTTP.
Deployed on Cloud Run — the MCP server is the public-facing layer, with the
Cloud SQL/pgvector database staying fully private behind it.
"""

import os

import uvicorn
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from generate import ask

mcp = MCPServer("rag-pipeline-mcp")


@mcp.tool()
def query_rag_pipeline(question: str) -> dict:
    """
    Answer a question using the RAG pipeline grounded in the ingested
    document collection. Returns the answer and the source documents used.
    """
    result = ask(question)
    # TODO: postprocessing hook goes here (safety filter, custom checks)
    # TODO: API key / OAuth check goes here before doing real work
    return result


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    allowed_host = os.environ["ALLOWED_HOST"]
    security = TransportSecuritySettings(
        # allowed_hosts=[
        #     "rag-pipe-mcp-dev-mcp-server-ncdlcaaczq-ez.a.run.app",
        #     "rag-pipe-mcp-dev-mcp-server-ncdlcaaczq-ez.a.run.app:*",
        # ],
        allowed_hosts=[allowed_host, f"{allowed_host}:*"],
        enable_dns_rebinding_protection=True,
    )

    app = mcp.streamable_http_app(transport_security=security)
    uvicorn.run(app, host="0.0.0.0", port=port)