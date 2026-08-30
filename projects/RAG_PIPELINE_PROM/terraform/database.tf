# database now uses iam password (iam authentication), the database is not exposed to the internet
# its contained within my private vpc
# secret.tf is deleted entirely since we are now using iam authentication
resource "google_sql_database_instance" "rag_pg" {
  project             = var.project_id
  name                = "${var.project_id}-pg"
  region              = var.region
  database_version    = "POSTGRES_15"
  deletion_protection = false

  settings {
    tier = var.db_tier

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.myvpc.id
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }

  depends_on = [google_project_service.sqladmin,google_service_networking_connection.private_vpc_connection]
}

resource "google_sql_database" "rag_db" {
  project  = var.project_id
  name     = var.db_name
  instance = google_sql_database_instance.rag_pg.name
}

resource "google_sql_user" "rag_user" {
  project  = var.project_id
  name     = replace(google_service_account.pipeline_sa.email, ".gserviceaccount.com", "")
  instance = google_sql_database_instance.rag_pg.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}