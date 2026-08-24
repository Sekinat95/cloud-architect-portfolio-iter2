"""
MCP server exposing the RAG pipeline as a callable tool over Streamable HTTP.
Deployed on Cloud Run — the MCP server is the public-facing layer, with the
Cloud SQL/pgvector database staying fully private behind it.
hhdjd
"""

import os

import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse

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


class LivenessProbeMiddleware(BaseHTTPMiddleware):
    """
    Some MCP client validators (e.g. Mistral's Connector registration check)
    send a bare GET with no session ID to confirm the server is reachable,
    and expect a 200 response for unauthenticated servers. The real MCP
    Streamable HTTP spec treats a sessionless GET as invalid (400), which is
    correct per-spec but fails that specific liveness check. This middleware
    special-cases that one scenario: a GET on /mcp with no session header
    returns 200 directly, without touching real session-based GET handling.
    """

    async def dispatch(self, request: Request, call_next):
        if (
            request.method == "GET"
            and request.url.path == "/mcp"
            and "mcp-session-id" not in request.headers
        ):
            return PlainTextResponse("OK", status_code=200)
        return await call_next(request)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))

    security = TransportSecuritySettings(
        allowed_hosts=[
            "rag-pipe-mcp-mcp-server-hkigjsojqa-ez.a.run.app",
            "rag-pipe-mcp-mcp-server-hkigjsojqa-ez.a.run.app:*",
            "rag-pipe-mcp-mcp-server-514728048358.europe-west4.run.app",
            "rag-pipe-mcp-mcp-server-514728048358.europe-west4.run.app:*",
        ],
        enable_dns_rebinding_protection=True,
    )

    app = mcp.streamable_http_app(transport_security=security)
    app.add_middleware(BaseHTTPMiddleware, dispatch=LivenessProbeMiddleware().dispatch)

    uvicorn.run(app, host="0.0.0.0", port=port)