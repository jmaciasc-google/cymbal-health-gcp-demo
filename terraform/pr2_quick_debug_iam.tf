resource "google_project_iam_member" "debug_overprivileged" {
  project = var.project_id
  role    = "roles/editor"
  member  = "serviceAccount:123456789-compute@developer.gserviceaccount.com"
}
