output "project_id" {
  description = "Target GCP project ID."
  value       = var.project_id
}

output "vpc_name" {
  description = "Dedicated VPC network name."
  value       = google_compute_network.vpc.name
}

output "subnet_name_and_cidr" {
  description = "Primary regional subnet name and CIDR range."
  value       = "${google_compute_subnetwork.subnet.name} (${google_compute_subnetwork.subnet.ip_cidr_range})"
}

output "psa_sql_range" {
  description = "Private Service Access IPv4 range reserved for Cloud SQL."
  value       = "${google_compute_global_address.psa_range.address}/${google_compute_global_address.psa_range.prefix_length}"
}

output "global_load_balancer_ip" {
  description = "External Anycast IPv4 address of the Global Application Load Balancer."
  value       = google_compute_global_address.lb_ip.address
}

output "portal_public_https_url" {
  description = "Public HTTPS URL protected by Cloud Armor WAF and Managed SSL."
  value       = "https://${local.portal_nip_domain}"
}

output "cloud_armor_policy_name" {
  description = "Attached Cloud Armor WAF security policy name."
  value       = google_compute_security_policy.waf_policy.name
}

output "web_portal_internal_uri" {
  description = "Cloud Run portal internal URI (reachable exclusively via External Load Balancer)."
  value       = google_cloud_run_v2_service.web_portal.uri
}

output "cloudsql_instance_connection_name" {
  description = "Cloud SQL PostgreSQL 15 connection name."
  value       = google_sql_database_instance.pg_main.connection_name
}

output "cloudsql_private_ip" {
  description = "Cloud SQL PostgreSQL 15 private VPC IP address."
  value       = google_sql_database_instance.pg_main.private_ip_address
}

output "soportes_bucket_name" {
  description = "Private Cloud Storage bucket for PDF clinical supports."
  value       = google_storage_bucket.soportes.name
}

output "artifact_registry_repo" {
  description = "Artifact Registry Docker repository path."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}"
}

output "service_accounts" {
  description = "Dedicated least-privilege Service Accounts."
  value = {
    portal = google_service_account.portal_sa.email
    cicd   = google_service_account.cicd_sa.email
  }
}

output "wiz_audit_pubsub_topic" {
  description = "Pub/Sub topic receiving real-time Cloud Audit Logs."
  value       = google_pubsub_topic.wiz_audit_topic.id
}
