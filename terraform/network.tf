locals {
  required_apis = toset([
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudtrace.googleapis.com",
    "compute.googleapis.com",
    "containerscanning.googleapis.com",
    "discoveryengine.googleapis.com",
    "dlp.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "modelarmor.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
  ])
}

resource "google_project_service" "apis" {
  for_each = local.required_apis

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_compute_network" "vpc" {
  name                            = "cymbal-health-vpc"
  project                         = var.project_id
  auto_create_subnetworks         = false
  routing_mode                    = "REGIONAL"
  delete_default_routes_on_create = false
  description                     = "Dedicated isolated VPC for Cymbal Health Direct VPC Egress and Cloud SQL Private IP"

  depends_on = [google_project_service.apis]
}

resource "google_compute_subnetwork" "subnet" {
  name                     = "cymbal-health-subnet-us-central1"
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.vpc.id
  ip_cidr_range            = var.vpc_subnet_cidr
  private_ip_google_access = true
  description              = "Primary regional subnet (10.28.0.0/24) for Cloud Run Direct VPC Egress"

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_global_address" "psa_range" {
  name          = "cymbal-health-psa-range"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  address       = var.psa_range_address
  prefix_length = var.psa_range_prefix_length
  network       = google_compute_network.vpc.id
  description   = "Reserved internal /20 range (10.28.16.0/20) for Cloud SQL Private Service Access"
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.psa_range.name]
  deletion_policy         = "ABANDON"

  depends_on = [google_project_service.apis]
}

resource "google_compute_firewall" "deny_all_ingress" {
  name          = "cymbal-health-fw-deny-all-ingress"
  project       = var.project_id
  network       = google_compute_network.vpc.name
  direction     = "INGRESS"
  priority      = 65534
  source_ranges = ["0.0.0.0/0"]
  description   = "Explicitly block unsolicited inbound VPC connections"

  deny {
    protocol = "all"
  }
}

resource "google_compute_firewall" "allow_egress_to_sql_psa" {
  name               = "cymbal-health-fw-allow-sql-psa"
  project            = var.project_id
  network            = google_compute_network.vpc.name
  direction          = "EGRESS"
  priority           = 1000
  destination_ranges = ["${var.psa_range_address}/${var.psa_range_prefix_length}"]
  description        = "Allow Cloud Run Direct VPC Egress to reach Cloud SQL PostgreSQL over Private Service Access"

  allow {
    protocol = "tcp"
    ports    = ["5432", "3307"]
  }
}
