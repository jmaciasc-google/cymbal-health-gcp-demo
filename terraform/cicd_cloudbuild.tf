# Cloud Build 2nd Gen CI/CD Governance:
# Uses dedicated least-privilege service account (cymbal-health-cicd-sa)
# and isolated logs bucket (cymbal-health-cb-logs-<project_number>).

resource "google_storage_bucket" "cb_logs" {
  name                        = "cymbal-health-cb-logs-${var.project_number}"
  project                     = var.project_id
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true
  labels                      = var.common_labels

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloudbuild_trigger" "pr_security_gate" {
  count = var.enable_github_triggers ? 1 : 0

  name            = "cymbal-health-pr-security-gate"
  project         = var.project_id
  location        = var.region
  description     = "Shift-left PR gate running pytest, Artifact Registry CVE scan, WizCLI v1, and CodeMender"
  service_account = google_service_account.cicd_sa.id
  filename        = "cloudbuild.yaml"

  repository_event_config {
    repository = var.github_repo_uri
    pull_request {
      branch          = "^main$"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  substitutions = {
    _DEPLOY_ON_GREEN = "false"
  }
}

resource "google_cloudbuild_trigger" "main_zero_downtime_deploy" {
  count = var.enable_github_triggers ? 1 : 0

  name            = "cymbal-health-main-deploy"
  project         = var.project_id
  location        = var.region
  description     = "Verified main-branch pipeline deploying zero-downtime revisions to Cloud Run"
  service_account = google_service_account.cicd_sa.id
  filename        = "cloudbuild.yaml"

  repository_event_config {
    repository = var.github_repo_uri
    push {
      branch = "^main$"
    }
  }

  substitutions = {
    _DEPLOY_ON_GREEN = "true"
  }
}
