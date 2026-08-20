resource "google_bigquery_dataset" "predictions" {
  dataset_id                 = "mlops_predictions"
  friendly_name              = "MLOps Pipeline Predictions"
  description                = "Stores FinBERT batch inference results"
  location                   = var.region
  delete_contents_on_destroy = true

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_bigquery_table" "predictions" {
  dataset_id          = google_bigquery_dataset.predictions.dataset_id
  table_id            = "finbert_predictions"
  deletion_protection = false

  schema = jsonencode([
    { name = "text", type = "STRING", mode = "REQUIRED" }, #sentence
    { name = "predicted_label", type = "STRING", mode = "REQUIRED" },
    { name = "confidence", type = "FLOAT64", mode = "REQUIRED" },
    { name = "ground_truth_label", type = "STRING", mode = "REQUIRED" },
    { name = "correct", type = "BOOL", mode = "REQUIRED" },
    { name = "run_id", type = "STRING", mode = "REQUIRED" },
    { name = "run_timestamp", type = "TIMESTAMP", mode = "REQUIRED" }
  ])
}