terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.18"
    }
  }

  backend "gcs" {
    prefix = "terraform/state/cymbal-health"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
