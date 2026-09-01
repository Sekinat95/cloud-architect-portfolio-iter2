terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "gcs" {
    bucket = "rag-pipe-mcp-p-terraform-state"
    prefix = "rag-mcp-prod"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}