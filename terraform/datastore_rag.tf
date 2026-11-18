# Vertex AI Search (Discovery Engine) Clinical Protocols Data Store & Private Corpus Bucket
# Grounding store for cymbal-clinical-agent (v2.0):
# - Private GCS corpus bucket: cymbal-health-protocols-<project_number>
# - Unstructured Data Store:   cymbal-health-clinical-protocols-ds
# - Enterprise Search Engine:  cymbal-health-clinical-protocols-engine
# Access restricted strictly to cymbal-health-agent-sa (roles/discoveryengine.viewer
# + bucket-level roles/storage.objectViewer ONLY).

resource "google_storage_bucket" "protocols" {
  name                        = "cymbal-health-protocols-${var.project_number}"
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

resource "google_discovery_engine_data_store" "clinical_protocols" {
  project                     = var.project_id
  location                    = var.discovery_engine_location
  data_store_id               = "cymbal-health-clinical-protocols-ds"
  display_name                = "Cymbal Health Clinical Authorization Protocols & CUPS"
  industry_vertical           = "GENERIC"
  content_config              = "CONTENT_REQUIRED"
  solution_types              = ["SOLUTION_TYPE_SEARCH"]
  create_advanced_site_search = false

  document_processing_config {
    default_parsing_config {
      digital_parsing_config {}
    }
    parsing_config_overrides {
      file_type = "pdf"
      ocr_parsing_config {
        use_native_text = true
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_discovery_engine_search_engine" "clinical_protocols_engine" {
  project           = var.project_id
  engine_id         = "cymbal-health-clinical-protocols-engine"
  collection_id     = "default_collection"
  location          = google_discovery_engine_data_store.clinical_protocols.location
  display_name      = "Cymbal Health Clinical Protocols RAG Engine"
  data_store_ids    = [google_discovery_engine_data_store.clinical_protocols.data_store_id]
  industry_vertical = google_discovery_engine_data_store.clinical_protocols.industry_vertical

  common_config {
    company_name = "Cymbal Health IPS"
  }

  search_engine_config {
    search_tier    = "SEARCH_TIER_ENTERPRISE"
    search_add_ons = ["SEARCH_ADD_ON_LLM"]
  }
}
