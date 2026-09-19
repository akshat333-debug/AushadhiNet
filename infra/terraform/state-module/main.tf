# Per-state data plane (architecture.md §5.4, project.md §9): one Google
# Cloud project per participating state, so raw facility-level rows never
# leave the state's own boundary. Federation only ever moves DP-noised
# model updates out of this project (ml/federated/dp.py).
#
# HONEST NOTE: `terraform validate` has not been run against this module
# in this session -- the Terraform CLI is not installed in this sandbox
# (Homebrew's `terraform` formula was removed for licensing reasons; a
# `hashicorp/tap` install was judged not worth the time given AC11 itself
# is explicitly deferred until GCP credits arrive). Validate this for
# real as the first step once a GCP project and credits exist.

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP project ID for this state's data plane (one per state, per project.md §9)"
  type        = string
}

variable "state_code" {
  description = "Two-letter state code (MH, HR, AS, ML) -- used to name and tag resources"
  type        = string
}

variable "region" {
  description = "GCP region for this state's resources"
  type        = string
  default     = "asia-south1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "required" {
  for_each = toset([
    "run.googleapis.com",
    "firestore.googleapis.com",
    "bigquery.googleapis.com",
    "pubsub.googleapis.com",
    "aiplatform.googleapis.com",
    "speech.googleapis.com",
    "translate.googleapis.com",
    "texttospeech.googleapis.com",
    "cloudkms.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

resource "google_firestore_database" "live_state" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.required]
}

resource "google_bigquery_dataset" "history" {
  project    = var.project_id
  dataset_id = "aushadhinet_${lower(var.state_code)}"
  location   = var.region
  depends_on = [google_project_service.required]
}

resource "google_pubsub_topic" "raw_messages" {
  project = var.project_id
  name    = "ingest-raw-message"
}

resource "google_kms_key_ring" "order_signing" {
  project  = var.project_id
  name     = "aushadhinet-order-signing"
  location = var.region
}

resource "google_kms_crypto_key" "order_signing_key" {
  name     = "transfer-order-signer"
  key_ring = google_kms_key_ring.order_signing.id
  purpose  = "ASYMMETRIC_SIGN"
  version_template {
    algorithm = "EC_SIGN_P256_SHA256"
  }
}

# VPC Service Controls perimeter (architecture.md §6): the boundary that
# actually enforces "raw rows never leave" beyond application-level
# discipline. Deliberately left as a placeholder resource block --
# perimeter membership across multiple state projects requires an
# organization-level policy that only exists once real state projects are
# provisioned; wiring it now against a project that doesn't exist yet
# would be untestable HCL.
# resource "google_access_context_manager_service_perimeter" "state_boundary" { ... }

output "firestore_database" {
  value = google_firestore_database.live_state.name
}

output "bigquery_dataset" {
  value = google_bigquery_dataset.history.dataset_id
}
