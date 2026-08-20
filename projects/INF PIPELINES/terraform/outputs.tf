output "raw_data_bucket" {
  value = google_storage_bucket.raw_data.name
}

output "model_artefacts_bucket" {
  value = google_storage_bucket.model_artefacts.name
}

output "pipeline_root_bucket" {
  value = google_storage_bucket.pipeline_root.name
}

output "pipeline_sa_email" {
  value = google_service_account.pipeline_sa.email
}

output "bigquery_dataset" {
  value = google_bigquery_dataset.predictions.dataset_id
}

output "bigquery_table" {
  value = google_bigquery_table.predictions.table_id
}