resource "google_bigquery_dataset" "xr_predictions" {
  dataset_id                 = "xr_predictions"
  friendly_name              = "XR Traffic Model Predictions"
  description                = "Stores batch inference results for LSTM and GP models"
  location                   = var.region
  delete_contents_on_destroy = true

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_bigquery_table" "lstm_predictions" {
  dataset_id          = google_bigquery_dataset.xr_predictions.dataset_id
  table_id            = "lstm_predictions"
  deletion_protection = false

  schema = jsonencode([
    { name = "sample_index",     type = "INT64",     mode = "REQUIRED" },
    { name = "time_t_minus_1",   type = "FLOAT64",   mode = "REQUIRED" },
    { name = "actual_time_t",    type = "FLOAT64",   mode = "REQUIRED" },
    { name = "predicted_time_t", type = "FLOAT64",   mode = "REQUIRED" },
    { name = "residual",         type = "FLOAT64",   mode = "REQUIRED" },
    { name = "squared_error",    type = "FLOAT64",   mode = "REQUIRED" },
    { name = "app",              type = "STRING",    mode = "REQUIRED" },
    { name = "run_id",           type = "STRING",    mode = "REQUIRED" },
    { name = "run_timestamp",    type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "model_version",    type = "STRING",    mode = "REQUIRED" }
  ])
}

resource "google_bigquery_table" "gp_predictions" {
  dataset_id          = google_bigquery_dataset.xr_predictions.dataset_id
  table_id            = "gp_predictions"
  deletion_protection = false

  schema = jsonencode([
    { name = "sample_index",     type = "INT64",     mode = "REQUIRED" },
    { name = "time_t_minus_1",   type = "FLOAT64",   mode = "REQUIRED" },
    { name = "actual_time_t",    type = "FLOAT64",   mode = "REQUIRED" },
    { name = "predicted_time_t", type = "FLOAT64",   mode = "REQUIRED" },
    { name = "residual",         type = "FLOAT64",   mode = "REQUIRED" },
    { name = "squared_error",    type = "FLOAT64",   mode = "REQUIRED" },
    { name = "app",              type = "STRING",    mode = "REQUIRED" },
    { name = "run_id",           type = "STRING",    mode = "REQUIRED" },
    { name = "run_timestamp",    type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "model_version",    type = "STRING",    mode = "REQUIRED" }
  ])
}