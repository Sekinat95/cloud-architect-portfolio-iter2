resource "google_storage_bucket" "raw_data" {
  name                        = "${var.project_id}-raw-data"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_storage_bucket" "model_artefacts" {
  name                        = "${var.project_id}-model-artefacts"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_storage_bucket" "pipeline_root" {
  name                        = "${var.project_id}-pipeline-root"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [time_sleep.wait_for_apis]
}