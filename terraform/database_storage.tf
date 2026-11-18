# Private Data Plane: Cloud SQL PostgreSQL 15 (Private IP + IAM DB Auth),
# Private Cloud Storage Bucket for Diagnostic Medical Order PDFs, and Secret Manager Containers.

resource "google_sql_database_instance" "pg_main" {
  name                = "cymbal-health-pg-main"
  project             = var.project_id
  region              = var.region
  database_version    = "POSTGRES_15"
  deletion_protection = var.sql_deletion_protection

  settings {
    tier              = var.sql_tier
    availability_type = var.sql_availability_type
    disk_type         = "PD_SSD"
    disk_size         = 20
    disk_autoresize   = true
    user_labels       = var.common_labels

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.vpc.id
      ssl_mode                                      = "ENCRYPTED_ONLY"
      enable_private_path_for_google_cloud_services = true
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "04:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
  }

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_sql_database" "cymbal_db" {
  name     = "cymbal_health_db"
  project  = var.project_id
  instance = google_sql_database_instance.pg_main.name
}

resource "google_sql_user" "portal_iam_user" {
  name     = trimsuffix(google_service_account.portal_sa.email, ".gserviceaccount.com")
  project  = var.project_id
  instance = google_sql_database_instance.pg_main.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}

resource "google_sql_user" "agent_iam_user" {
  name     = trimsuffix(google_service_account.agent_sa.email, ".gserviceaccount.com")
  project  = var.project_id
  instance = google_sql_database_instance.pg_main.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}

resource "google_storage_bucket" "soportes" {
  name                        = "cymbal-health-soportes-${var.project_number}"
  project                     = var.project_id
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = var.common_labels

  versioning {
    enabled = true
  }

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "github_pat" {
  secret_id = "cymbal-health-github-pat"
  project   = var.project_id
  labels    = var.common_labels

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "wiz_client_id" {
  secret_id = "cymbal-health-wiz-client-id"
  project   = var.project_id
  labels    = var.common_labels

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "wiz_client_secret" {
  secret_id = "cymbal-health-wiz-client-secret"
  project   = var.project_id
  labels    = var.common_labels

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.apis]
}
