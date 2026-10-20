
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
### Storage

### Operations
#### CI/CD: Cloudbuild

#### GCP Observability: Monitoring, Logging

## Application Design
### Document vectorised storage and retreival
### R-A-G Pipeline
### MCP Interface Definition
### MCP Interface Q&A Request Example
### MISTRAL AI MCP Interface Suite
### MCP API Authorisation/Authetication