
# Retreival Augmented Generation (RAG) Pipeline With Model Context Protocol (MCP) Interface Endpoint

[Architectural Diagram](../RAG_PIPELINE_PROM/diagram/RAG%20pipeline%20with%20MCP.png)

<img src="../RAG_PIPELINE_PROM/diagram/RAG%20pipeline%20with%20MCP.png" width="500" height="300">


## Infrastructure Architecture 
### Networking
1. This project uses a private VPC ``myvpc`` <br>
2. ``myvpc`` uses VPC peering via private service access (PSA) which gives it access to GCP managed services <br>
3. It enables private connectivity between ``myvpc`` and GCP managed services such as ``CloudSQL`` <br>
4. PSA is subject to VPC peering limitations eg non transitive connection <br>
### Identity and Access Management (IAM)
1. service identity service account was created for the RAG pipeline ``pipeline_sa`` <br>
2. ``pipeline_sa`` is made its own self user through ``roles/iam.serviceAccountUser`` <br>
3. ``pipeline_sa`` is granted the following roles and access levels under ``google_project_iam_member``<br>
    - ``roles/storage.objectAdmin``<br>
    - ``roles/aiplatform.user``<br>
    - ``roles/cloudsql.client``<br>
    - ``roles/cloudsql.instanceUser``<br>
    - ``roles/logging.logWriter``<br>
    - ``roles/monitoring.metricWriter``<br>
    - ``roles/documentai.apiUser`` <br>
    - ``roles/artifactregistry.writer`` <br>
    - ``roles/artifactregistry.reader`` <br>
    - ``roles/run.admin`` <br>
    - ``roles/clouddeploy.releaser`` <br>
4. ``pipeline_sa`` is granted cloudrun ``roles/run.invoker`` <br>
### Compute: Docker, Artefact Registry => Cloudrun, CloudrunJobs
1. Provisioned a Cloudrun server with ``pipeline_sa`` service account <br>
2. Provided the server access to ``myvpc`` using GCP access connector <br>
3. Set all required environment variables for the workload to successful functioning in the server once deployed (e.g DB credentials, storage bucket names, etc) <br>
4. CloudrunJobs are provisioned for data embedding (for vector storage and retreival) part of the RAG workflow. <br>
### Storage
1. This project uses ``rag-pipe-mcp-dev-terraform-state`` to store Terraform states <br>
2. ``rag-pipe-mcp-dev-ingestion`` is used to store the document corpus before vectorisaion <br> 
3. ``pipeline_sa`` is granted ``roles/storage.objectAdmin`` to enable document access to and from GCS (to CloudSQL) <br>
4. Artefact registry repository is defined for the docker image that contains the workflow before Cloudrun deployment
### Database
1. CloudSQL PostgreSQL 15 instance is used fro vector storage and retreival in this project <br>
2. It uses the service account ``pipeline_sa`` as its user and thus uses IAM authentication <br>
### Operations
#### Required GCP APIs
1. Compute ``compute.googleapis.com`` <br>
2. AI platform ``aiplatform.googleapis.com`` <br>
3. SQL Admin ``sqladmin.googleapis.com`` <br>
4. Storage ``storage.googleapis.com``<br>
5. Document AI ``documentai.googleapis.com`` <br>
6. Logging ``logging.googleapis.com`` <br>
7. Monitoring ``monitoring.googleapis.com`` <br>
8. IAM ``iam.googleapis.com`` <br>
9. Service Networking ``servicenetworking.googleapis.com`` <br>
10. Gcloud ``run`` ``run.googleapis.com`` <br>
11. VPC access ``vpcaccess.googleapis.com`` <br>
12. Artefact Registry ``artifactregistry.googleapis.com`` <br>
13. Cloudbuild ``cloudbuild.googleapis.com`` <br>

#### CI/CD: Cloudbuild
1. Automation for build, push and deployment of the docker container to the registry and to the cloudrun server are defined in ``cloudbuild.yaml`` <br>
2. Git triggered build are set against the project repository. <br>

#### GCP Observability: Monitoring, Logging
1. Cloud logging is enabled for the build, push and deployment to track the process in case of build and deployment errors. <br>

## Application Design
The RAG workflow with MCP interface endpoint is a backend operationalisation of the RAG tooling. Retreival Augmented Generation (RAG) is a document querying service that can provide access to document corpuses through vectorised storage and retreival. The core idea of a an RAG service is to combine the generative abilities of large language models (LLMs) with the external knowledge gotten from a separate datasource (usually documents corpuses). RAG takes user query inputs and uses a set of documents from a source as context, feeds both (user input and context) to an LLM which produces the final output. <br>
### Document vectorised storage and retreival
1. Create pgvector extension on PostgreSQL instance in CloudSQL and grant ``pipeline_sa`` schema privileges and run with a superuser role. <br>
2. Ingest -> Chunk -> Embed: <br>
    - ``Langchain document loaders``<br>
    - ``Langchain textsplitters``<br>
    - ``PgVector`` to embed and store document chunks in vectorstore using a text embedding model<br>
### R-A-G Pipeline
1. Cloud Logging is set up for the workflow <br>
2. ``RAGAS`` is set up with insufficient context markers <br>
3. **R-A-G**: <br> 
    - The retreiver takes in user input queries and outputs top-k relevant chunks from the vector store using pgvector similarity search. <br>
    - This chunk as well as the user question are the inputs of the augmentation step which returns a ``question + context`` formatted output`. This step uses langchain expression language (LCEL). <br>
    - This format is the input to the LLM which generates the answer. ``gemini-2.5-flash`` model is used in this project. <br>
### MCP Interface Definition
In this project we have wrapped the RAG pipeline with a model context protocol (MCP) Client Interface which allows the RAG pipeline the ability to be queried by external LLMs. <br>
### MCP Interface Q&A Request Example
The MCP interface wrapps arroud the user query tool for the RAG pipeline <br>
```python
@mcp.tool()
def query_rag_pipeline(question: str) -> dict:
    result = ask(question)
    return result
```
The RAG pipeline accepts user queries through the MCP interface. <br>
```python
import asyncio
from mcp import Client
async def main() -> None:
    async with Client(SERVER_URL) as client:
        for question in QUESTIONS:
            result = await client.call_tool("query_rag_pipeline", {"question": question})
            print(f"Q: {question}")
            print(result)
            print("---")
```

### MISTRAL AI MCP Interface Suite
This section of the project shows how an external model will call the RAG MCP service. <br>
### MCP API Authorisation/Authetication