# 5-Ring Runtime AI Security Guardrails (Model Armor + Cloud DLP Ley 1581 Colombia)
# and Real-Time Cloud Audit Logs -> Pub/Sub Streaming Pipeline for CDR.

resource "google_model_armor_template" "clinical_guardrail" {
  project     = var.project_id
  location    = var.region
  template_id = "cymbal-health-model-armor"
  labels      = var.common_labels

  filter_config {
    pi_and_jailbreak_filter_settings {
      filter_enforcement = "ENABLED"
      confidence_level   = "LOW_AND_ABOVE"
    }

    malicious_uri_filter_settings {
      filter_enforcement = "ENABLED"
    }

    sdp_settings {
      basic_config {
        filter_enforcement = "ENABLED"
      }
    }

    rai_settings {
      rai_filters {
        filter_type      = "DANGEROUS"
        confidence_level = "MEDIUM_AND_ABOVE"
      }
      rai_filters {
        filter_type      = "HARASSMENT"
        confidence_level = "MEDIUM_AND_ABOVE"
      }
      rai_filters {
        filter_type      = "HATE_SPEECH"
        confidence_level = "MEDIUM_AND_ABOVE"
      }
    }
  }

  template_metadata {
    log_sanitize_operations = true
    log_template_operations = true

    multi_language_detection {
      enable_multi_language_detection = true
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_data_loss_prevention_inspect_template" "colombia_pii_inspect" {
  parent       = "projects/${var.project_id}/locations/${var.region}"
  template_id  = "cymbal-health-dlp-inspect"
  display_name = "Cymbal Health Ley 1581 Colombian Cedula & Clinical PII Inspector"
  description  = "Detects Colombian Cedula de Ciudadania (CC), credit cards, emails, and phone numbers"

  inspect_config {
    min_likelihood = "POSSIBLE"

    info_types {
      name = "COLOMBIA_CDC_NUMBER"
    }
    info_types {
      name = "CREDIT_CARD_NUMBER"
    }
    info_types {
      name = "EMAIL_ADDRESS"
    }
    info_types {
      name = "PHONE_NUMBER"
    }

    custom_info_types {
      info_type {
        name = "COLOMBIA_CEDULA_CIUDADANIA"
      }
      likelihood = "LIKELY"
      regex {
        pattern = "(?i)(?:\\b(?:cc|c\\.c\\.|cedula|documento)\\s*[:#-]?\\s*)\\d{6,10}\\b"
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_data_loss_prevention_deidentify_template" "colombia_pii_mask" {
  parent       = "projects/${var.project_id}/locations/${var.region}"
  template_id  = "cymbal-health-dlp-deidentify"
  display_name = "Cymbal Health Ley 1581 PII Redaction Template"
  description  = "Replaces Colombian Cedula and payment card identifiers before LLM invocation"

  deidentify_config {
    info_type_transformations {
      transformations {
        info_types {
          name = "COLOMBIA_CDC_NUMBER"
        }
        info_types {
          name = "COLOMBIA_CEDULA_CIUDADANIA"
        }
        primitive_transformation {
          replace_config {
            new_value {
              string_value = "[REDACTED_COLOMBIA_CC]"
            }
          }
        }
      }

      transformations {
        info_types {
          name = "CREDIT_CARD_NUMBER"
        }
        primitive_transformation {
          replace_config {
            new_value {
              string_value = "[REDACTED_PAYMENT_CARD]"
            }
          }
        }
      }

      transformations {
        info_types {
          name = "EMAIL_ADDRESS"
        }
        info_types {
          name = "PHONE_NUMBER"
        }
        primitive_transformation {
          character_mask_config {
            masking_character = "*"
            number_to_mask    = 6
            reverse_order     = true
          }
        }
      }
    }
  }

  depends_on = [google_project_service.apis]
}

locals {
  audited_services = toset([
    "aiplatform.googleapis.com",
    "discoveryengine.googleapis.com",
    "dlp.googleapis.com",
    "modelarmor.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
  ])
}

resource "google_project_iam_audit_config" "cymbal_data_access" {
  for_each = var.manage_project_audit_configs ? local.audited_services : toset([])

  project = var.project_id
  service = each.value

  audit_log_config {
    log_type = "ADMIN_READ"
  }
  audit_log_config {
    log_type = "DATA_READ"
  }
  audit_log_config {
    log_type = "DATA_WRITE"
  }
}

resource "google_pubsub_topic" "wiz_audit_topic" {
  name                       = "cymbal-health-wiz-audit-topic"
  project                    = var.project_id
  message_retention_duration = "86400s"
  labels                     = var.common_labels

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_subscription" "wiz_audit_sub" {
  name                 = "cymbal-health-wiz-audit-sub"
  project              = var.project_id
  topic                = google_pubsub_topic.wiz_audit_topic.id
  ack_deadline_seconds = 60
  labels               = var.common_labels

  expiration_policy {
    ttl = ""
  }
}

resource "google_logging_project_sink" "wiz_audit_sink" {
  name                   = "cymbal-health-wiz-audit-sink"
  project                = var.project_id
  destination            = "pubsub.googleapis.com/projects/${var.project_id}/topics/${google_pubsub_topic.wiz_audit_topic.name}"
  unique_writer_identity = true
  description            = "Streams Admin Activity and Data Access audit events to Pub/Sub for real-time CDR"

  filter = <<-EOT
    logName:(
      "projects/${var.project_id}/logs/cloudaudit.googleapis.com%2Factivity" OR
      "projects/${var.project_id}/logs/cloudaudit.googleapis.com%2Fdata_access" OR
      "projects/${var.project_id}/logs/cloudaudit.googleapis.com%2Fpolicy"
    )
  EOT

  depends_on = [google_project_service.apis]
}
