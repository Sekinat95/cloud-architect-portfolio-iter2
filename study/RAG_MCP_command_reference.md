# Project 07: RAG + MCP — Complete Command Reference

Every `gcloud`, `gsutil`, `terraform`, `psql`, `git`, and related terminal command used across this project, in roughly chronological order, grouped by purpose.

---

## 1. Terraform — Init, Plan, Apply, State Management

```bash
terraform init
terraform plan
terraform apply
terraform plan -target="google_artifact_registry_repository.mcp_server_repo"
terraform apply -target="google_artifact_registry_repository.mcp_server_repo"
```

### State recovery (after a mid-apply network drop)
```bash
terraform state push errored.tfstate
terraform force-unlock <LOCK_ID>
terraform import google_sql_database_instance.rag_pg rag-pipe-mcp/rag-pipe-mcp-pg
```

### Cloud Shell terraform install (fresh session)
```bash
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

### Shell cache issue fix (terraform binary conflict)
```bash
which terraform
dpkg -L terraform | grep bin
echo $PATH
type -a terraform
hash -r
```

---

## 2. GCP API Enablement

```bash
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services list --enabled --filter="name:cloudresourcemanager.googleapis.com"
```

---

## 3. IAM — Role Bindings (Project-Level)

```bash
gcloud projects add-iam-policy-binding rag-pipe-mcp --member="serviceAccount:514728048358-compute@developer.gserviceaccount.com" --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding rag-pipe-mcp --member="serviceAccount:514728048358-compute@developer.gserviceaccount.com" --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding rag-pipe-mcp --member="serviceAccount:514728048358-compute@developer.gserviceaccount.com" --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding rag-pipe-mcp --member="serviceAccount:rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com" --role="roles/run.admin"

gcloud projects add-iam-policy-binding rag-pipe-mcp --member="serviceAccount:rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com" --role="roles/artifactregistry.reader"

gcloud projects add-iam-policy-binding rag-pipe-mcp --member="serviceAccount:rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com" --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding rag-pipe-mcp --member="serviceAccount:514728048358@cloudbuild.gserviceaccount.com" --role="roles/run.admin"
```

### Check current bindings for an identity
```bash
gcloud projects get-iam-policy rag-pipe-mcp --flatten="bindings[].members" --filter="bindings.members:514728048358@cloudbuild.gserviceaccount.com"

gcloud projects get-iam-policy rag-pipe-mcp --flatten="bindings[].members" --filter="bindings.members:rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com"
```

---

## 4. IAM — Service Account-Level Bindings (Impersonation & Cross-SA Acting)

```bash
gcloud iam service-accounts add-iam-policy-binding rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com --member="serviceAccount:rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com" --role="roles/iam.serviceAccountUser"

gcloud iam service-accounts add-iam-policy-binding rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com --member="user:yahya.sekinat@gmail.com" --role="roles/iam.serviceAccountTokenCreator"

gcloud iam service-accounts add-iam-policy-binding rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com --member="serviceAccount:514728048358@cloudbuild.gserviceaccount.com" --role="roles/iam.serviceAccountUser"
```

### Check bindings on the SA itself
```bash
gcloud iam service-accounts get-iam-policy rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com
```

### Local impersonation (ADC)
```bash
gcloud auth application-default login --impersonate-service-account=rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com
gcloud auth list
```

---

## 5. Cloud SQL

```bash
gcloud sql instances list
gcloud sql instances describe rag-pipe-mcp-pg --format="value(state)"
gcloud sql users set-password postgres --instance=rag-pipe-mcp-pg --password=hgfdsqetyi
gcloud sql connect rag-pipe-mcp-pg --user=postgres --database=ragdb
```

### Cloud SQL Auth Proxy (manual, background process)
```bash
cloud-sql-proxy rag-pipe-mcp:europe-west4:rag-pipe-mcp-pg --port 9470 &
cloud-sql-proxy rag-pipe-mcp:europe-west4:rag-pipe-mcp-pg --port 9470 --private-ip &
```

### psql direct connection (through the proxy)
```bash
psql "host=127.0.0.1 port=9470 dbname=ragdb user=postgres sslmode=disable"
```

### Process/port diagnostics (proxy troubleshooting)
```bash
jobs
ss -tlnp | grep 9470
kill -9 <PID>
kill -9 %1
```

---

## 6. GCS / gsutil

```bash
gsutil cp your-file.pdf gs://rag-pipe-mcp-ingestion/
gsutil cp data/*.pdf gs://rag-pipe-mcp-ingestion/
gsutil -m cp -r data/* gs://rag-pipe-mcp-ingestion/
```

---

## 7. Artifact Registry

```bash
gcloud artifacts docker images list europe-west4-docker.pkg.dev/rag-pipe-mcp/mcp-server-repo/mcp-server --include-tags
```

---

## 8. Cloud Build

```bash
gcloud builds submit --config cloudbuild.yaml .
gcloud builds list --limit=5 --format="table(id,status,substitutions.COMMIT_SHA)"
```

---

## 9. Cloud Run — Service (MCP Server)

```bash
gcloud run deploy rag-pipe-mcp-mcp-server --image=europe-west4-docker.pkg.dev/rag-pipe-mcp/mcp-server-repo/mcp-server:latest --region=europe-west4

gcloud run services describe rag-pipe-mcp-mcp-server --region=europe-west4 --format="value(status.traffic[0].revisionName)"

gcloud run services describe rag-pipe-mcp-mcp-server --region=europe-west4 --format="value(status.latestReadyRevisionName)"

gcloud run services describe rag-pipe-mcp-mcp-server --region=europe-west4 --format="value(spec.template.spec.containers[0].image)"

gcloud run revisions describe rag-pipe-mcp-mcp-server-00006-fwd --region=europe-west4 --format="value(spec.containers[0].image)"

gcloud run services get-iam-policy rag-pipe-mcp-mcp-server --region=europe-west4

gcloud run services logs read rag-pipe-mcp-mcp-server --region=europe-west4 --limit=50
```

---

## 10. Cloud Run — Jobs (Embed / Create Extension)

```bash
gcloud run jobs execute rag-pipe-mcp-embed-job --region=europe-west4

gcloud sql users set-password postgres --instance=rag-pipe-mcp-dev-pg --password=hgfdsqetyi
gcloud run jobs execute rag-pipe-mcp-embed-job --region=europe-west4 --args=create_extension.py --update-env-vars=POSTGRES_PASSWORD=hgfdsqetyi

gcloud run jobs executions list --job=rag-pipe-mcp-embed-job --region=europe-west4

gcloud run jobs executions describe rag-pipe-mcp-embed-job-wn574
```

---

## 11. Logging — Reading Container/Revision-Specific Logs

```bash
gcloud logging read 'resource.type="cloudsql_database" AND resource.labels.database_id="rag-pipe-mcp:rag-pipe-mcp-pg"' --limit=20 --format="value(textPayload)"

gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="rag-pipe-mcp-embed-job"' --limit=30 --format="value(textPayload)"

gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="rag-pipe-mcp-mcp-server" AND resource.labels.revision_name="rag-pipe-mcp-mcp-server-00014-dlp"' --limit=50 --format="value(textPayload)"
```

---

## 12. Testing the Deployed Endpoint

```bash
curl -i https://rag-pipe-mcp-mcp-server-514728048358.europe-west4.run.app/mcp

curl -i -X POST https://rag-pipe-mcp-mcp-server-514728048358.europe-west4.run.app/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

curl -v -X POST https://rag-pipe-mcp-mcp-server-514728048358.europe-west4.run.app/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' 2>&1 | grep -i "^> Host"
```

### MCP Inspector
```bash
npx @modelcontextprotocol/inspector
```

---

## 13. Git — Diagnostics for Commit/Build Mismatches

```bash
git log --oneline -5
git show HEAD:"projects/RAG pipeline/pipeline/components/mcp_wrapper.py"
git show HEAD:"projects/RAG pipeline/pipeline/components/mcp_wrapper.py" | Select-String "middleware"
git branch --show-current
git status
git add "projects/RAG pipeline/pipeline/components/create_extension.py"
git commit -m "add pgvector extension setup script"
git push
```

---

## 14. Python Environment / Package Install

```bash
pip install pypdf
pip install anthropic
pip install mistralai
python3 embed.py
python .\embed.py
python3 test_endpoint.py
python3 test_endpoint_by_model.py
```

---

## 15. Environment Variables (PowerShell / bash session setup)

### PowerShell
```powershell
$env:PROJECT_ID = "rag-pipe-mcp"
$env:REGION = "europe-west4"
$env:CLOUD_SQL_CONNECTION_NAME = "rag-pipe-mcp:europe-west4:rag-pipe-mcp-pg"
$env:DB_NAME = "ragdb"
$env:DB_USER = "rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com"
$env:INGESTION_BUCKET_NAME = "rag-pipe-mcp-ingestion"
$env:ANTHROPIC_API_KEY = "your-actual-api-key-here"
$env:MISTRALAI_API_KEY = "your-actual-key"
```

### bash (Cloud Shell)
```bash
export PROJECT_ID="rag-pipe-mcp"
export REGION="europe-west4"
export CLOUD_SQL_CONNECTION_NAME="rag-pipe-mcp:europe-west4:rag-pipe-mcp-pg"
export DB_NAME="ragdb"
export DB_USER="rag-pipe-mcp-pipeline@rag-pipe-mcp.iam.gserviceaccount.com"
export INGESTION_BUCKET_NAME="rag-pipe-mcp-ingestion"
export BUCKET_NAME="${PROJECT_ID}-terraform-state"
```

---

## 16. Diagnostic / Network Checks

```bash
ping storage.googleapis.com
nslookup storage.googleapis.com
lsof -i :9470
```
