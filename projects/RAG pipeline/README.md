# Retreival Augmented Generation (RAG) PIPELINE with Model Context Protocol (MCP) Endpoint
## RAG pipeline
- Retrieval: input = user query → output = top-k relevant chunks
- Augmentation: input = user query + [top-k relevant chunks] → output = filled prompt template
- Generation: input = [filled prompt template] → output = answer text
OR
- Retrieval: input = user query → output = top-k relevant chunks (from pgvector similarity search)
- Augmentation: input = user query + retrieved chunks → output = a filled prompt template (context + question combined)
- Generation: input = the augmented prompt → output = the LLM's answer text

OR
- Retrieval: tool = pgvector similarity search (via langchain retriever interface) → input = user query → output = top-k relevant chunks
- Augmentation: tool = LCEL prompt template → input = user query + [top-k relevant chunks] → output = filled prompt template
- Generation: tool = ChatVertexAI → input = [filled prompt template] → output = answer text

## POST RAG 
- API safety filters: catch harmful/inappropriate content in the LLM's output before it reaches the user — a moderation gate, not about correctness.
- Custom Python checks: your own rule-based validation — e.g. checking the answer isn't empty, checking format, checking it doesn't hallucinate specific things you can verify programmatically. Deterministic, code-level checks.
- RAGAS: measures the quality of the RAG output itself — things like faithfulness (is the answer grounded in the retrieved chunks?) and answer relevance (does it actually address the query?). This is evaluation, not gating.
- GCP observability suite: logging/metrics/monitoring across the whole pipeline — latency, error rates, throughput — so you can see how the system behaves in production over time, not just per-request correctness.

# MCP Endpoint
## Overview:
 Wrap the existing RAG pipeline (R→A→G→postprocessing) as a callable "tool" behind an MCP server, so any MCP-compatible client (Claude, other agents) can invoke it like a function call instead of you running scripts manually.
## Components/steps:
- MCP server framework (tool: Python mcp SDK) — defines the server that exposes your pipeline function as a registered "tool" with a name, description, and input schema (e.g. query: str). Intuition: this is the translation layer — it takes MCP protocol messages and turns them into a normal Python function call.
- Tool function wrapper (your existing pipeline code) — a single function that internally calls retrieval → augmentation → generation → postprocessing and returns the final (safety-checked) answer. Intuition: the MCP server doesn't know about LangChain/pgvector internals — it just calls this one function and gets a string back.
- Transport (stdio or HTTP/SSE, tool: mcp SDK's built-in transports) — how requests/responses actually move between client and server. Intuition: stdio for local/dev testing, HTTP/SSE if you want it reachable remotely (e.g. from Cloud Run).
- Deployment (tool: Cloud Run) — containerize the MCP server so it's persistently reachable rather than run locally. Intuition: same as any other service — the pipeline becomes a hosted endpoint instead of a script you run manually.
- Client invocation — an MCP client (Claude Desktop config, or another agent) points at your server and calls the tool by name with a query. Intuition: this is the "external link" — anything speaking MCP can now use your RAG pipeline as a capability, without knowing it's LangChain + pgvector under the hood.
- Connection flow: Client → MCP transport → MCP server → your wrapped pipeline function (R→A→G→postprocessing) → answer → back through transport → client.

## Network connectivity brief overview
External model (Claude/Gemini/GPT) → MCP server (Cloud Run, API key/OAuth layer) → Serverless VPC Access connector → Cloud SQL Auth Proxy / private IP → Cloud SQL (private IP only, pgvector)

## Monitoring opportunities in this iteration:

- Cloud SQL: connection count, CPU/memory utilization, disk usage — catch capacity issues on your db-f1-micro before they cause failures.
- MCP endpoint (Cloud Run): request count, latency, error rate, cold start frequency — since this is now a public-facing endpoint external models call.
- Pipeline-level: retrieval latency, generation latency, RAGAS scores over time (faithfulness/relevance trending down = silent quality drift).
- Postprocessing: safety filter trigger rate, custom check failure rate — signals if something upstream (bad ingestion, prompt drift) is degrading quality.
- IAM/auth failures on the MCP layer — repeated failed auth attempts could indicate abuse of the public endpoint.

## MCP wrapper and postprocessing
Right — the gate goes inside query_rag_pipeline (or a wrapper around it) rather than at the Cloud Run/network layer, since Cloud Run itself is set to allow unauthenticated requests. So the flow is: request reaches your container → your code checks the key/token first → only then calls ask() and returns a result.





