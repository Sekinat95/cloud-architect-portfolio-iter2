variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "rag-pipe-mcp-p"
}

variable "region" {
  description = "Default region for regional resources"
  type        = string
  default     = "europe-west4"
}

variable "zone" {
  description = "Default zone for zonal resources"
  type        = string
  default     = "europe-west4-a"
}

variable "project_number" {
  description = "GCP project number"
  type        = string
  default     = "616436024863"
}


variable "ingestion_bucket_name" {
  description = "Name of the bucket that holds raw source documents (separate from the Terraform state bucket)"
  type        = string
  default     = "rag-pipe-mcp-p-ingestion"
}

variable "db_tier" {
  description = "Cloud SQL machine tier. db-f1-micro is the cheapest shared-core option, fine for a POC."
  type        = string
  default     = "db-f1-micro"
}

variable "db_name" {
  description = "Name of the Postgres database created on the instance"
  type        = string
  default     = "ragdb-p"
}