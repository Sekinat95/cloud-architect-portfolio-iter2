resource "google_vpc_access_connector" "connector" {
  project       = var.project_id
  name          = "${var.project_id}-conn"
  region        = var.region
  network       = google_compute_network.myvpc.name
  ip_cidr_range = "10.8.0.0/28"

  depends_on = [google_project_service.vpcaccess]
}

resource "google_cloud_run_v2_service" "mcp_server" {
  project  = var.project_id
  name     = "${var.project_id}-mcp-server"
  location = var.region

  template {
    service_account = google_service_account.pipeline_sa.email

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "europe-west4-docker.pkg.dev/${var.project_id}/mcp-server-repo/mcp-server:latest" #"gcr.io/${var.project_id}/mcp-server:latest" # placeholder until image is built/pushed

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

  depends_on = [
    google_project_service.run,
    google_vpc_access_connector.connector
  ]
}