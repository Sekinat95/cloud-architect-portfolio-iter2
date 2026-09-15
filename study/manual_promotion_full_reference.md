# Project 07 (RAG+MCP) — Manual Promotion: Full Reference

---

## Part 1: Manual Dev→Prod Promotion — Steps

### 1. Fix the `allowed_hosts` design flaw first
`mcp_wrapper.py` originally hardcoded `allowed_hosts` per environment, forcing the shared "frozen" image to be rebuilt every time a new environment's hostname needed adding — defeating true promotion. Fixed by reading a single `ALLOWED_HOST` env var instead, injected per-environment via Terraform.

```python
allowed_host = os.environ["ALLOWED_HOST"]
security = TransportSecuritySettings(
    allowed_hosts=[allowed_host, f"{allowed_host}:*"],
    enable_dns_rebinding_protection=True,
)
```

```hcl
env {
  name  = "ALLOWED_HOST"
  value = "rag-pipe-mcp-dev-mcp-server-ncdlcaaczq-ez.a.run.app"
}
```

### 2. Fix `create_extension.py`'s hardcoded GRANT role
Same class of bug — the `GRANT ALL ON SCHEMA public TO "..."` statement had dev's SA email literally hardcoded, breaking prod (which has its own different SA). Fixed by deriving the role name from `DB_USER` env var, with `.gserviceaccount.com` stripped:
```python
db_user = os.environ["DB_USER"].replace(".gserviceaccount.com", "")
# use db_user in the GRANT statement
```

### 3. Rebuild + push the corrected image to dev's AR repo (once)
```bash
docker build -t europe-west4-docker.pkg.dev/rag-pipe-mcp-dev/mcp-server-repo/mcp-server:latest .
docker push europe-west4-docker.pkg.dev/rag-pipe-mcp-dev/mcp-server-repo/mcp-server:latest
```
This is now the final, environment-agnostic image — never needs rebuilding again for new environments.

### 4. Update dev's Cloud Run Service + Job to the new image, redeploy dev
```bash
gcloud run deploy rag-pipe-mcp-dev-mcp-server --image=europe-west4-docker.pkg.dev/rag-pipe-mcp-dev/mcp-server-repo/mcp-server:latest --region=europe-west4
gcloud run jobs update rag-pipe-mcp-dev-embed-job --image=europe-west4-docker.pkg.dev/rag-pipe-mcp-dev/mcp-server-repo/mcp-server:latest --region=europe-west4
```

### 5. Add missing IAM bindings to `iam.tf` for `pipeline_sa`
Discovered that AR writer/reader, `run.admin`, and `iam.serviceAccountUser` (self-grant) were never in Terraform — only added manually via `gcloud` in iter2. Added permanently to `iam.tf`:
```hcl
resource "google_project_iam_member" "sa_artifactregistry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}
resource "google_project_iam_member" "sa_artifactregistry_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}
resource "google_project_iam_member" "sa_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}
resource "google_service_account_iam_member" "sa_self_user" {
  service_account_id = google_service_account.pipeline_sa.name
  role                = "roles/iam.serviceAccountUser"
  member              = "serviceAccount:${google_service_account.pipeline_sa.email}"
}
```
```bash
terraform apply
```

### 6. Create prod GCP project + link billing (Console, manual)

### 7. Checkout prod git branch
```bash
git checkout -b prod
```

### 8. Create `prod.tfvars`
```hcl
project_id            = "rag-pipe-mcp-p"
region                = "europe-west4"
zone                  = "europe-west4-a"
ingestion_bucket_name = "rag-pipe-mcp-p-ingestion"
db_tier               = "db-f1-micro"
db_name               = "ragdb-p"
project_number        = "<prod project number>"
```

### 9. Point prod's `cloudrun.tf` / `cloudrunjob.tf` at dev's AR image
```hcl
image = "europe-west4-docker.pkg.dev/rag-pipe-mcp-dev/mcp-server-repo/mcp-server:latest"
```
Delete `artefactregistry.tf` content on prod's branch entirely — prod provisions no AR repo of its own.

### 10. New Terraform backend for prod
```bash
gsutil mb -p rag-pipe-mcp-p -l europe-west4 gs://rag-pipe-mcp-p-terraform-state
terraform init -reconfigure
```

### 11. Enable `cloudresourcemanager` API manually in prod (chicken-and-egg)
```bash
gcloud services enable cloudresourcemanager.googleapis.com --project=rag-pipe-mcp-p
```

### 12. Apply Terraform for prod
```bash
terraform apply -var-file="prod.tfvars"
```

### 13. Grant cross-project AR access — TWO identities
```bash
# prod's pipeline SA
gcloud artifacts repositories add-iam-policy-binding mcp-server-repo \
  --project=rag-pipe-mcp-dev --location=europe-west4 \
  --member="serviceAccount:rag-pipe-mcp-p-pipeline@rag-pipe-mcp-p.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"

# prod's Cloud Run Service Agent (actual identity pulling the image at deploy time)
gcloud artifacts repositories add-iam-policy-binding mcp-server-repo \
  --project=rag-pipe-mcp-dev --location=europe-west4 \
  --member="serviceAccount:service-<prod-project-number>@serverless-robot-prod.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"
```

### 14. Re-apply Terraform — prod's Cloud Run Service + Job now succeed

### 15. Set `ALLOWED_HOST` for prod (two-pass, first-time-only per environment)
Get prod's real URL from the `terraform apply` output, add to prod's `cloudrun.tf`:
```hcl
env {
  name  = "ALLOWED_HOST"
  value = "rag-pipe-mcp-p-mcp-server-peiqbzghaq-ez.a.run.app"
}
```
```bash
terraform apply -var-file="prod.tfvars"
```
No rebuild needed — Terraform updates the env var on the existing service in place.

### 16. Set prod's own Cloud SQL superuser password
```bash
gcloud sql users set-password postgres --instance=rag-pipe-mcp-p-pg --password=<password>
```

### 17. Run `create_extension.py` via prod's Cloud Run Job
```bash
gcloud run jobs execute rag-pipe-mcp-p-embed-job --region=europe-west4 --project=rag-pipe-mcp-p --args=create_extension.py --update-env-vars=POSTGRES_PASSWORD=<password>
```

### 18. Upload PDFs to prod's own ingestion bucket
```bash
gsutil -m cp -r ./data/* gs://rag-pipe-mcp-p-ingestion/
```

### 19. Run `embed.py` via prod's Cloud Run Job
```bash
gcloud run jobs execute rag-pipe-mcp-p-embed-job --region=europe-west4 --project=rag-pipe-mcp-p
```

### 20. Test prod's deployed endpoint
```bash
python3 test_endpoint.py   # SERVER_URL pointed at prod's real hostname + /mcp
```

---

## Part 2: Errors Encountered + Fixing Commands

| Error | Fix |
|---|---|
| `Backend configuration changed` on `terraform init`/`apply` | `terraform init -reconfigure` |
| `Connector ID must follow the pattern ^[a-z][-a-z0-9]{0,23}[a-z0-9]$` | Fixed connector `name` in `cloudrun.tf` to a valid lowercase string |
| Transient DNS blip: `dial tcp: lookup <api>.googleapis.com: no such host` | Retry `terraform apply` |
| `Image '...:latest' not found` (Cloud Run Service/Job creation) | Build + push the image first, then re-`terraform apply` |
| `google_sql_database_instance` still `PENDING_CREATE`, apply errored mid-create | Poll `gcloud sql instances describe ... --format="value(state)"` until `RUNNABLE`, then `terraform import` if state lost track, then `terraform plan`/`apply` |
| `instanceAlreadyExists` (409) on `terraform apply` | `terraform import google_sql_database_instance.rag_pg <PROJECT_ID>/<INSTANCE_NAME>` |
| Docker Desktop: `Virtualization support not detected` | Switched build/push to Cloud Shell instead of local machine |
| `docker: command not found` | Confirm Docker Desktop actually running + terminal reopened after install |
| `denied: Permission 'artifactregistry.repositories.uploadArtifacts' denied` (Cloud Build trigger push step) | Added `artifactregistry.writer` to `pipeline_sa` in `iam.tf`, `terraform apply` |
| `250 instance(s) is allowed per prediction. Actual: 1243` (embed.py) | Batch `vectorstore.add_documents()` calls, `batch_size=250` initially |
| `input token count is 59953 but the model supports up to 20000` | Reduced `batch_size` to 25 (count-based batching alone insufficient — token limit also applies) |
| `permission denied to create extension "vector" ... Must be superuser` | Reset `postgres` password, ran `create_extension.py` via Cloud Run Job as superuser |
| `permission denied for schema public` | Extended `create_extension.py` to also `GRANT ALL ON SCHEMA public TO "<stripped_sa_email>"` |
| `role "..." does not exist` on the GRANT step | `create_extension.py` had the wrong/stale/hardcoded SA email — fixed to use `os.environ["DB_USER"]` (stripped), rebuilt/pushed/updated job, re-ran |
| `password authentication failed for user "postgres"` | Superuser password was never actually reset before running `create_extension.py` — ran `gcloud sql users set-password` first |
| Cloud Run Job kept running an old image despite rebuild | `gcloud run jobs update --image=...` — jobs don't auto-pick-up `:latest` on `execute`, unlike Services |
| `Google Cloud Run Service Agent ... must have permission to read the image` (cross-project) | Grant `artifactregistry.reader` to `service-<project-number>@serverless-robot-prod.iam.gserviceaccount.com` on the source project's AR repo — separate identity from the app's own SA |
| `MCPError: Server returned an error response` / timeout on `initialize` | `allowed_hosts` rejecting the request — hostname missing or malformed (had `https://` prefix, which never matches the raw `Host` header) |
| Digest mismatch investigation between running revision and `:latest` | `docker buildx imagetools inspect ...:latest` — confirmed manifest-list vs. platform-manifest digest difference, not an actual stale deploy |
| `Unable to remove Service Networking Connection ... Producer services still using this connection` (terraform destroy) | Genuine GCP propagation delay after Cloud SQL deletion; resolved via full project deletion: `gcloud projects delete rag-pipe-mcp-prod` |
| `Backend initialization required` after branch switch | `terraform init -reconfigure` |
| Cloud Build trigger not found via `gcloud builds triggers describe` | Trigger was region-scoped (`europe-west4`), not global — checked via Console, or `--region=europe-west4` flag |
| Cloud Build push step `PERMISSION_DENIED` under trigger's own SA (`pipeline_sa`) | Added the same AR writer/reader roles to `iam.tf` (trigger runs as `pipeline_sa`, a user-managed SA per org policy) |
| Terminal command duplication/mangling on paste (`--include-tagsgcloud...`) | Retype/rerun the command cleanly |

---

## Part 3: Why Terraform + Cloud Deploy Manifest Together Is Ill-Advised

Terraform's `google_cloud_run_v2_service` resource and Cloud Deploy's manifest-based deployment (Skaffold + Cloud Run service YAML) are **two independent systems that each expect to be the sole owner of the deployed Cloud Run service's state**.

- Terraform tracks the service's config (image, env vars, SA, scaling) in its own state file and reconciles any drift back to what's declared in `.tf` files on every `apply`.
- Cloud Deploy's manifest is a separate declaration of largely the same thing (image, env vars, ports), applied directly to Cloud Run by Cloud Deploy's own release mechanism, with no awareness of Terraform's state at all.

If both are used: whichever one deploys most recently silently overwrites the other's configuration on the live service, while neither system's own state file reflects what is actually running. This produces exactly the kind of "why doesn't my fix work" debugging trap this project already hit multiple times with far simpler causes (stale `:latest` digests, commit/build mismatches) — except here the disagreement is structural, not transient, and won't resolve by retrying or waiting.

Additionally, provisioning Cloud Deploy pipelines themselves is not commonly done via Terraform at all (no clean, first-class resource in most setups) — it's normally managed via `clouddeploy.yaml` + `gcloud deploy apply`, which is itself a second, separate IaC-adjacent mechanism running alongside Terraform, rather than through it.

Given the project's actual goal — a working, correctly-gated dev→prod promotion — manual `gcloud run deploy` (already fully Terraform-owned, no competing system) achieves the same practical outcome (a human-gated promotion step) without this ownership conflict.

---

## Part 4: If Cloud Run Were Provisioned via Cloud Deploy Manifest Instead of Terraform

This describes the alternative architecture — not what was implemented — for reference if a future iteration wants to commit fully to Cloud Deploy instead of Terraform for the Cloud Run layer specifically.

### 1. Remove Cloud Run resources from Terraform
Delete `google_cloud_run_v2_service.mcp_server` and `google_cloud_run_v2_job.embed_job` from `.tf` files (and their state, via `terraform state rm`). Terraform continues to own everything else (VPC, Cloud SQL, IAM, Artifact Registry, buckets).

### 2. Create a `skaffold.yaml`
Describes how to render/deploy the service, referencing the manifest file(s):
```yaml
apiVersion: skaffold/v4beta6
kind: Config
manifests:
  rawYaml:
    - service.yaml
deploy:
  cloudrun: {}
```

### 3. Create the Cloud Run service manifest (`service.yaml`)
Knative-style manifest defining image, env vars, SA, port — effectively re-declaring what `cloudrun.tf` used to define:
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: mcp-server
spec:
  template:
    spec:
      serviceAccountName: PLACEHOLDER_SA
      containers:
      - image: mcp-server
        ports:
        - containerPort: 8080
        env:
        - name: PROJECT_ID
          value: PLACEHOLDER_PROJECT_ID
        - name: ALLOWED_HOST
          value: PLACEHOLDER_ALLOWED_HOST
        # ... remaining env vars matching what cloudrun.tf declared
```

### 4. Register the delivery pipeline + targets (as already done)
```bash
gcloud deploy apply --file=clouddeploy.yaml --region=europe-west4 --project=rag-pipe-mcp-dev
```

### 5. Grant Cloud Deploy's service agent Cloud Run deploy permissions on both projects
```bash
gcloud projects add-iam-policy-binding rag-pipe-mcp-dev --member="serviceAccount:service-<dev-project-number>@gcp-sa-clouddeploy.iam.gserviceaccount.com" --role="roles/clouddeploy.jobRunner"
gcloud projects add-iam-policy-binding rag-pipe-mcp-p --member="serviceAccount:service-<dev-project-number>@gcp-sa-clouddeploy.iam.gserviceaccount.com" --role="roles/clouddeploy.jobRunner"
```

### 6. Grant `pipeline_sa` release-creation permission
```hcl
resource "google_project_iam_member" "sa_clouddeploy_releaser" {
  project = var.project_id
  role    = "roles/clouddeploy.releaser"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}
```

### 7. Update `cloudbuild.yaml` to create a release with an explicit `--source`
```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: gcloud
  args:
    - 'deploy'
    - 'releases'
    - 'create'
    - 'release-$SHORT_SHA'
    - '--delivery-pipeline=rag-pipe-mcp-pipeline'
    - '--region=europe-west4'
    - '--source=./projects/RAG_PIPELINE_PROM/deploy'
    - '--images=mcp-server=europe-west4-docker.pkg.dev/$PROJECT_ID/mcp-server-repo/mcp-server:latest'
```

### 8. Push to dev branch — Cloud Build creates the release, Cloud Deploy auto-deploys to dev target

### 9. Promote to prod once dev is validated
```bash
gcloud deploy releases promote --release=release-<sha> --delivery-pipeline=rag-pipe-mcp-pipeline --region=europe-west4 --to-target=prod
```

### Ongoing consideration
`ALLOWED_HOST` (and any other per-environment value) now has to be templated into the manifest per-target rather than injected via Terraform's per-branch tfvars — Cloud Deploy supports this via [render-time variable substitution or per-target manifest overrides], which would need to be set up as an additional piece of this configuration, not something carried over automatically from the Terraform-based approach.
