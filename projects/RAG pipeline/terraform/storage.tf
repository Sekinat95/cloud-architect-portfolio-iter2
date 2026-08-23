resource "google_storage_bucket" "ingestion" {
  project                     = var.project_id
  name                        = var.ingestion_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.storage]
}

resource "google_storage_bucket_iam_member" "pipeline_sa_ingestion_access" {
  bucket = google_storage_bucket.ingestion.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.pipeline_sa.email}"
}