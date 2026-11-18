# Well-Architected Serverless Runtime & Perimeter Edge Defense (v1.0 Baseline):
# - Artifact Registry with Automated Container Vulnerability Scanning
# - Cloud Run Web Portal (INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER, DRS compliant)
# - Cloud Armor WAF Policy + Global External Application Load Balancer + Managed SSL

locals {
  portal_nip_domain     = "cymbal-health.${google_compute_global_address.lb_ip.address}.nip.io"
  resolved_portal_image = var.portal_image != "" ? var.portal_image : "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/cymbal-health-web-portal:v1.0"
}

resource "google_artifact_registry_repository" "repo" {
  repository_id = "cymbal-health-repo"
  project       = var.project_id
  location      = var.region
  format        = "DOCKER"
  mode          = "STANDARD_REPOSITORY"
  description   = "Cymbal Health container repository with automated CVE vulnerability scanning"
  labels        = var.common_labels

  vulnerability_scanning_config {
    enablement_config = "INHERITED"
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service" "web_portal" {
  name                 = "cymbal-health-web-portal"
  project              = var.project_id
  location             = var.region
  ingress              = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  invoker_iam_disabled = true
  deletion_protection  = false
  labels               = var.common_labels

  template {
    service_account = google_service_account.portal_sa.email
    timeout         = "60s"

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"
      network_interfaces {
        network    = google_compute_network.vpc.name
        subnetwork = google_compute_subnetwork.subnet.name
      }
    }

    containers {
      name  = "web-portal"
      image = local.resolved_portal_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle = true
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "DB_INSTANCE_CONNECTION_NAME"
        value = google_sql_database_instance.pg_main.connection_name
      }
      env {
        name  = "DB_PRIVATE_IP"
        value = google_sql_database_instance.pg_main.private_ip_address
      }
      env {
        name  = "DB_NAME"
        value = google_sql_database.cymbal_db.name
      }
      env {
        name  = "DB_IAM_USER"
        value = google_sql_user.portal_iam_user.name
      }
      env {
        name  = "SOPORTES_BUCKET"
        value = google_storage_bucket.soportes.name
      }
      env {
        name  = "ENABLE_LIVE_GCP_STORAGE"
        value = "true"
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_service_account_iam_member.cicd_act_as_runtime_sas,
  ]
}

resource "google_compute_security_policy" "waf_policy" {
  name        = "cymbal-health-waf-policy"
  project     = var.project_id
  description = "Cloud Armor edge WAF blocking SQLi, XSS, RCE, LFI, and volumetric abuse"

  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = true
    }
  }

  rule {
    action      = "deny(403)"
    priority    = 1000
    description = "Block OWASP SQL Injection attacks at edge (CRS sqli-v33-stable sensitivity 1)"
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('sqli-v33-stable', {'sensitivity': 1})"
      }
    }
  }

  rule {
    action      = "deny(403)"
    priority    = 1010
    description = "Block OWASP Cross-Site Scripting attacks at edge (CRS xss-v33-stable sensitivity 1)"
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('xss-v33-stable', {'sensitivity': 1})"
      }
    }
  }

  rule {
    action      = "deny(403)"
    priority    = 1020
    description = "Block OWASP Remote Code Execution payloads at edge (CRS rce-v33-stable sensitivity 1)"
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('rce-v33-stable', {'sensitivity': 1})"
      }
    }
  }

  rule {
    action      = "deny(403)"
    priority    = 1030
    description = "Block OWASP Local File Inclusion traversal at edge (CRS lfi-v33-stable sensitivity 1)"
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('lfi-v33-stable', {'sensitivity': 1})"
      }
    }
  }

  rule {
    action      = "throttle"
    priority    = 2000
    description = "Per-client IP rate limit (120 requests per 60s)"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 120
        interval_sec = 60
      }
    }
  }

  rule {
    action      = "allow"
    priority    = 2147483647
    description = "Default allow traffic passing OWASP WAF and rate-limit checks"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_compute_global_address" "lb_ip" {
  name         = "cymbal-health-lb-ip"
  project      = var.project_id
  address_type = "EXTERNAL"
  ip_version   = "IPV4"
  description  = "Dedicated global anycast IPv4 for Cymbal Health External Application Load Balancer"

  depends_on = [google_project_service.apis]
}

resource "google_compute_managed_ssl_certificate" "lb_cert" {
  name        = "cymbal-health-ssl-cert"
  project     = var.project_id
  description = "Google-managed TLS certificate over nip.io wildcard DNS for Cymbal Health"

  managed {
    domains = [local.portal_nip_domain]
  }
}

resource "google_compute_region_network_endpoint_group" "portal_neg" {
  name                  = "cymbal-health-portal-neg"
  project               = var.project_id
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.web_portal.name
  }
}

resource "google_compute_backend_service" "portal_backend" {
  name                  = "cymbal-health-portal-backend"
  project               = var.project_id
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  security_policy       = google_compute_security_policy.waf_policy.id
  enable_cdn            = false

  backend {
    group = google_compute_region_network_endpoint_group.portal_neg.id
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_url_map" "https_url_map" {
  name            = "cymbal-health-https-urlmap"
  project         = var.project_id
  default_service = google_compute_backend_service.portal_backend.id
}

resource "google_compute_url_map" "http_redirect_url_map" {
  name    = "cymbal-health-http-redirect-urlmap"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_https_proxy" "https_proxy" {
  name             = "cymbal-health-https-proxy"
  project          = var.project_id
  url_map          = google_compute_url_map.https_url_map.id
  ssl_certificates = [google_compute_managed_ssl_certificate.lb_cert.id]
}

resource "google_compute_target_http_proxy" "http_proxy" {
  name    = "cymbal-health-http-proxy"
  project = var.project_id
  url_map = google_compute_url_map.http_redirect_url_map.id
}

resource "google_compute_global_forwarding_rule" "https_fwd" {
  name                  = "cymbal-health-https-fwd-rule"
  project               = var.project_id
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_protocol           = "TCP"
  port_range            = "443"
  ip_address            = google_compute_global_address.lb_ip.id
  target                = google_compute_target_https_proxy.https_proxy.id
}

resource "google_compute_global_forwarding_rule" "http_fwd" {
  name                  = "cymbal-health-http-fwd-rule"
  project               = var.project_id
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_protocol           = "TCP"
  port_range            = "80"
  ip_address            = google_compute_global_address.lb_ip.id
  target                = google_compute_target_http_proxy.http_proxy.id
}
