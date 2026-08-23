output "sql_instance_connection_name" {
  value = google_sql_database_instance.rag_pg.connection_name
}

output "pipeline_sa_email" {
  value = google_service_account.pipeline_sa.email
}

output "ingestion_bucket_name" {
  value = google_storage_bucket.ingestion.name
}

output "mcp_server_url" {
  value = google_cloud_run_v2_service.mcp_server.uri
}