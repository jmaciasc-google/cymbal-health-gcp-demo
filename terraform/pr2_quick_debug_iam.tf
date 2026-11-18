# ==============================================================================
# INTENTIONALLY VULNERABLE CHANGE IN PR #2 (demo/pr2-vulnerable-change)
# Simulates a hurried developer debugging change on top of v2.0 that introduces:
#   1. Primitive role roles/editor at project scope
#   2. Default Compute Engine Service Account (<project_number>-compute@...)
#   3. Public internet exposure (INGRESS_TRAFFIC_ALL + invoker_iam_disabled=true)
#      on Tier 2 cymbal-health-clinical-agent
#   4. Static GEMINI_API_KEY environment variable
# Blocked automatically in <75s by WizCLI v1 ('wizcli scan dir .') & Cloud Build.
# ==============================================================================

resource "google_project_iam_member" "pr2_debug_overprivileged_editor" {
  project = var.project_id
  role    = "roles/editor"
  member  = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

resource "google_cloud_run_v2_service" "pr2_debug_public_clinical_agent" {
  name                 = "cymbal-health-clinical-agent-debug"
  project              = var.project_id
  location             = var.region
  ingress              = "INGRESS_TRAFFIC_ALL"
  invoker_iam_disabled = true

  template {
    service_account = "${var.project_number}-compute@developer.gserviceaccount.com"

    containers {
      name  = "clinical-agent-debug"
      image = local.resolved_agent_image

      env {
        name  = "GEMINI_API_KEY"
        value = "EXAMPLE_STATIC_DEV_KEY_DO_NOT_USE_IN_PROD"
      }
    }
  }
}
