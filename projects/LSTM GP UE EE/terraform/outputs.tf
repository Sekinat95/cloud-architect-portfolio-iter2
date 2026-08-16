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
  value = google_bigquery_dataset.xr_predictions.dataset_id
}

output "bigquery_table_lstm" {
  value = google_bigquery_table.lstm_predictions.table_id
}

output "bigquery_table_gp" {
  value = google_bigquery_table.gp_predictions.table_id
}

output "processed_data_bucket" {
  value = google_storage_bucket.processed_data.name
}