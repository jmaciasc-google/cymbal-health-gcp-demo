variable "project_id" {
  description = "Target GCP project ID for Cymbal Health deployment."
  type        = string
  default     = "cymbal-health-prod"
}

variable "project_number" {
  description = "Target GCP project number used for globally unique bucket naming."
  type        = string
  default     = "123456789012"
}

variable "region" {
  description = "Primary GCP region for serverless compute, private data, and AI guardrails."
  type        = string
  default     = "us-central1"
}

variable "discovery_engine_location" {
  description = "Location for Vertex AI Search clinical protocols Data Store and Engine."
  type        = string
  default     = "global"
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "prod"
}

variable "portal_image" {
  description = "Optional override container image URI for Tier 1 cymbal-health-web-portal."
  type        = string
  default     = ""
}

variable "agent_image" {
  description = "Optional override container image URI for Tier 2 cymbal-health-clinical-agent."
  type        = string
  default     = ""
}

variable "mcp_image" {
  description = "Optional override container image URI for Tier 2 cymbal-health-backlog-mcp."
  type        = string
  default     = ""
}

variable "vpc_subnet_cidr" {
  description = "Primary IPv4 CIDR block for cymbal-health-subnet-us-central1."
  type        = string
  default     = "10.28.0.0/24"
}

variable "psa_range_address" {
  description = "Base internal IPv4 address reserved for Private Service Access peering to Cloud SQL."
  type        = string
  default     = "10.28.16.0"
}

variable "psa_range_prefix_length" {
  description = "Prefix length for Private Service Access peering range (/20 = 4096 private IPs)."
  type        = number
  default     = 20
}

variable "sql_tier" {
  description = "Machine tier for Cloud SQL PostgreSQL 15 instance."
  type        = string
  default     = "db-custom-2-7680"
}

variable "sql_availability_type" {
  description = "Availability configuration for Cloud SQL (REGIONAL for HA or ZONAL)."
  type        = string
  default     = "REGIONAL"
}

variable "sql_deletion_protection" {
  description = "Prevents accidental Cloud SQL instance deletion until explicitly disabled."
  type        = bool
  default     = true
}

variable "mcp_authorized_invokers" {
  description = "Explicit IAM members granted roles/run.invoker on cymbal-health-backlog-mcp."
  type        = list(string)
  default     = []
}

variable "enable_github_triggers" {
  description = "Enable 2nd Gen Cloud Build GitHub triggers once OAuth host connection is linked."
  type        = bool
  default     = false
}

variable "manage_project_audit_configs" {
  description = "Manage authoritative project-wide Data Access audit configs (enable on dedicated greenfield projects)."
  type        = bool
  default     = false
}

variable "github_repo_uri" {
  description = "2nd Gen Cloud Build repository resource ID (projects/.../locations/.../connections/.../repositories/...)."
  type        = string
  default     = ""
}

variable "common_labels" {
  description = "Standard governance labels applied to all Cymbal Health resources."
  type        = map(string)
  default = {
    system           = "cymbal-health"
    managed_by       = "terraform"
    security_posture = "least-privilege"
    release_track    = "v2-clinical-agent"
  }
}
