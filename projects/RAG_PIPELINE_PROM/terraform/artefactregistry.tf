resource "google_artifact_registry_repository" "mcp_server_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "mcp-server-repo"
  format        = "DOCKER"

  depends_on = [google_project_service.artifactregistry]
}