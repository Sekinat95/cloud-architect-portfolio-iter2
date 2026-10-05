# Retrieval Augmented Generation (RAG) pipeline (for document Q&A) with Model Context Protocol (MCP) Client

[Architecture Diagram](../RAG%20pipeline/diagram/RAG%20pipeline%20with%20MCP.png)<br>
```mermaid
graph TD
  GCS["Data ingestion"] --> EMBC
  subgraph EMBC["Vector Embedding"]
    DOCUP["Document pre-processing <br/> Langchain document loaders"]-->CHNK
    CHNK["Langchain text splitters"]-->EMB
    EMB["Vector Embedding <br/> postresql pgvector extension"]
  end
  subgraph RAGPL["RAG Pipeline"]
    R["Retreival <br/> input query --> top-k relevant chunks (pgvector similarity search)"] -->A
    A["Augmentation <br/> input query + pgvector chunks --> context + question(input query) template(LCEL langchain expression language)"] -->G
    G["Generation <br/> context + question template (ChatVertexAI) --> LLM (External or Internal Gemini) answer "]
  end
  subgraph MCP["MCP functionality"]
    USR["user question"] --> MCPC
    MCPC["MCP Client"] --> RAGPPL
    %% RAGPPL["RAG Pipeline"]
  end
  subgraph RAGPPL ["RAG Pipeline"]
    OAUTH["API key/ Oauth/ OIDC"] --> RAGP
    RAGP["RAG pipline"] --> FLT
    FLT["RAGAS Safety Filters"]
  end
  subgraph OBSV["GCP observability suite <br/> Logging enabled on the pipeline"]
  end

EMBC --> RAGPL --> MCP --> RAGPPL --> OBSV
```
## Brief Description
### Introduction: Objective, definitions, Scope
In this project, RAG for document query is implemented with MCP client wrapper endpoint (enabling access from external models) and RAGAS filtering.<br>
The tools utilised for the implementation include: <br>
1. Langchain (document loaders, text splitters, vector embedding, langchain expression language(LCEL))<br>
2. GCP tools (storage buckets, cloudsql(postgresql instance), servers(cloudrun, cloudrun job))<br>
At the end, an MCP client endpoint wrapper is implemented over the RAG tooling to enable access from external models and to also seamlessly incorporate authentication/authorisation before access to the RAG tool.<br>
### Component
1. document ingestion (GCP storage buckets)<br>
2. document embedding (langchain document loaders)<br>
3. document spliting, chunk and vector creation (langchain document splitters, pgvector extension)<br>
4. RAG workflow
### Results
The include a successful request call through the MCP client wrapper to the RAG pipeline and a response in accordance with the documents and safety filters in accordance with checks and balances implemented in the project.<br>

## Set Up Instructions

## Instant Replication Instructions