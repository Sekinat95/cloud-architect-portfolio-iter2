resource "google_cloud_run_v2_job" "embed_job" {
  project  = var.project_id
  name     = "${var.project_id}-embed-job"
  location = var.region

  template {
    template {
      service_account = google_service_account.pipeline_sa.email

      vpc_access {
        connector = google_vpc_access_connector.connector.id
        egress    = "PRIVATE_RANGES_ONLY"
      }

      containers {
        #image   = "europe-west4-docker.pkg.dev/${var.project_id}/mcp-server-repo/mcp-server:latest"
        image = "europe-west4-docker.pkg.dev/rag-pipe-mcp-dev/mcp-server-repo/mcp-server:latest" 
        command = ["python"]
        args    = ["embed.py"]

        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "REGION"
          value = var.region
        }
        env {
          name  = "CLOUD_SQL_CONNECTION_NAME"
          value = google_sql_database_instance.rag_pg.connection_name
        }
        env {
          name  = "DB_NAME"
          value = var.db_name
        }
        env {
          name  = "DB_USER"
          value = google_service_account.pipeline_sa.email
        }
        env {
          name  = "INGESTION_BUCKET_NAME"
          value = google_storage_bucket.ingestion.name
        }
      }
    }
  }

  depends_on = [
    google_project_service.run,
    google_vpc_access_connector.connector
  ]
}