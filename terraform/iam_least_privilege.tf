# Strict Least Privilege IAM Architecture for Cymbal Health (v2.0 Agent + Data Store)
# Enforces 1 Component = 1 Dedicated Service Account, zero primitive roles,
# zero default compute identities, zero static JSON keys, and granular
# resource-level IAM bindings wherever supported by Google Cloud.

resource "google_service_account" "portal_sa" {
  account_id   = "cymbal-health-portal-sa"
  project      = var.project_id
  display_name = "Cymbal Health Web Portal Tier 1 Service Account"
  description  = "Least-privilege identity for cymbal-health-web-portal (Cloud SQL IAM, Soportes RW, Agent OIDC Invoker)"

  depends_on = [google_project_service.apis]
}

resource "google_service_account" "agent_sa" {
  account_id   = "cymbal-health-agent-sa"
  project      = var.project_id
  display_name = "Cymbal Health Clinical ADK Agent Tier 2 Service Account"
  description  = "Least-privilege identity for cymbal-health-clinical-agent (Vertex AI, Discovery Engine Viewer, Model Armor, DLP, Read-Only SQL/GCS)"

  depends_on = [google_project_service.apis]
}

resource "google_service_account" "mcp_sa" {
  account_id   = "cymbal-health-mcp-sa"
  project      = var.project_id
  display_name = "Cymbal Health GitHub Backlog MCP Service Account"
  description  = "Least-privilege identity for cymbal-health-backlog-mcp (scoped strictly to cymbal-health-github-pat)"

  depends_on = [google_project_service.apis]
}

resource "google_service_account" "cicd_sa" {
  account_id   = "cymbal-health-cicd-sa"
  project      = var.project_id
  display_name = "Cymbal Health Cloud Build Custom CI/CD Service Account"
  description  = "Least-privilege Cloud Build identity scoped to cymbal-health-repo, Wiz secrets, and Cymbal runtime SAs"

  depends_on = [google_project_service.apis]
}

locals {
  portal_project_roles = toset([
    "roles/cloudsql.client",
    "roles/cloudsql.instanceUser",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
  ])

  agent_project_roles = toset([
    "roles/aiplatform.user",
    "roles/discoveryengine.viewer",
    "roles/modelarmor.user",
    "roles/dlp.user",
    "roles/cloudsql.client",
    "roles/cloudsql.instanceUser",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
  ])

  mcp_project_roles = toset([
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
  ])

  cicd_project_roles = toset([
    "roles/run.developer",
    "roles/aiplatform.user",
    "roles/logging.logWriter",
  ])
}

resource "google_project_iam_member" "portal_project_scoped" {
  for_each = local.portal_project_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.portal_sa.email}"
}

resource "google_project_iam_member" "agent_project_scoped" {
  for_each = local.agent_project_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "mcp_project_scoped" {
  for_each = local.mcp_project_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.mcp_sa.email}"
}

resource "google_project_iam_member" "cicd_project_scoped" {
  for_each = local.cicd_project_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cicd_sa.email}"
}

# Portal SA: objectViewer + objectCreator ONLY on cymbal-health-soportes bucket
resource "google_storage_bucket_iam_member" "portal_soportes_viewer" {
  bucket = google_storage_bucket.soportes.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.portal_sa.email}"
}

resource "google_storage_bucket_iam_member" "portal_soportes_creator" {
  bucket = google_storage_bucket.soportes.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.portal_sa.email}"
}

# Agent SA: objectViewer ONLY on supports bucket AND clinical protocols bucket (0 write permissions)
resource "google_storage_bucket_iam_member" "agent_soportes_viewer_only" {
  bucket = google_storage_bucket.soportes.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_storage_bucket_iam_member" "agent_protocols_viewer_only" {
  bucket = google_storage_bucket.protocols.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.agent_sa.email}"
}

# Portal SA: OIDC run.invoker ONLY on Tier 2 cymbal-health-clinical-agent
resource "google_cloud_run_v2_service_iam_member" "portal_invokes_clinical_agent" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.clinical_agent.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.portal_sa.email}"
}

# Authorized Invokers ONLY on Tier 2 cymbal-health-backlog-mcp
resource "google_cloud_run_v2_service_iam_member" "authorized_invokes_backlog_mcp" {
  for_each = toset(var.mcp_authorized_invokers)

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backlog_mcp.name
  role     = "roles/run.invoker"
  member   = each.value
}

# MCP SA: secretAccessor ONLY on cymbal-health-github-pat
resource "google_secret_manager_secret_iam_member" "mcp_github_pat_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.github_pat.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.mcp_sa.email}"
}

# CI/CD SA: artifactregistry.writer ONLY on cymbal-health-repo
resource "google_artifact_registry_repository_iam_member" "cicd_repo_writer" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.repo.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.cicd_sa.email}"
}

# CI/CD SA: iam.serviceAccountUser ONLY on the 3 Cymbal runtime SAs (never project-wide)
resource "google_service_account_iam_member" "cicd_act_as_runtime_sas" {
  for_each = {
    portal = google_service_account.portal_sa.name
    agent  = google_service_account.agent_sa.name
    mcp    = google_service_account.mcp_sa.name
  }

  service_account_id = each.value
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cicd_sa.email}"
}

# CI/CD SA: secretAccessor ONLY on Wiz CLI credentials for Cloud Build scans
resource "google_secret_manager_secret_iam_member" "cicd_wiz_client_id_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.wiz_client_id.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cicd_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "cicd_wiz_client_secret_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.wiz_client_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cicd_sa.email}"
}

# CI/CD SA: storage.objectAdmin ONLY on dedicated Cloud Build logs bucket
resource "google_storage_bucket_iam_member" "cicd_cb_logs_admin" {
  bucket = google_storage_bucket.cb_logs.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cicd_sa.email}"
}

# Audit Log Sink Writer Identity: pubsub.publisher ONLY on cymbal-health-wiz-audit-topic
resource "google_pubsub_topic_iam_member" "audit_sink_topic_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.wiz_audit_topic.name
  role    = "roles/pubsub.publisher"
  member  = google_logging_project_sink.wiz_audit_sink.writer_identity
}
