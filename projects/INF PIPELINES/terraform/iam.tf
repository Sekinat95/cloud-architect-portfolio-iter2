resource "google_service_account" "pipeline_sa" {
  account_id   = "mlops-pipeline-sa"
  display_name = "MLOps Pipeline Service Account"

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_project_iam_member" "pipeline_sa_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_project_iam_member" "pipeline_sa_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_project_iam_member" "pipeline_sa_bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_project_iam_member" "pipeline_sa_bq_jobs" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}
# Logging - required for Cloud Build to write logs
resource "google_project_iam_member" "pipeline_sa_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# Storage Admin — Cloud Build needs bucket-level access
resource "google_project_iam_member" "pipeline_sa_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# Allow Cloud Build SA to impersonate pipeline SA
resource "google_service_account_iam_member" "cloudbuild_sa_impersonate" {
  service_account_id = google_service_account.pipeline_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
}

# Cloud Build SA — Vertex AI and Storage access
resource "google_project_iam_member" "cloudbuild_sa_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
}

resource "google_project_iam_member" "cloudbuild_sa_storage" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
}
