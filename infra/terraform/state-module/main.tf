# Per-state data plane (architecture.md §5.4, project.md §9): one Google
# Cloud project per participating state, so raw facility-level rows never
# leave the state's own boundary. Federation only ever moves DP-noised
# model updates out of this project (ml/federated/dp.py).
#
# `terraform validate` passes (Terraform 1.16, google provider 5.45). `plan`
# and `apply` need a real GCP project and have not been run.

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

variable "backend_url" {
  description = "Cloud Run URL of the backend (known after the first deploy). Empty = no push subscription yet."
  type        = string
  default     = ""
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
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "identitytoolkit.googleapis.com",
    "secretmanager.googleapis.com",
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

# Names must match backend/providers/queue_google.py: topic = the code's topic
# string, subscription = "<topic>-sub".
locals {
  # Mirrors backend/domain/{stock,census,checkin}.py; nested fields are JSON strings.
  history_tables = {
    stock_records = [
      ["record_id", "STRING", "REQUIRED"], ["facility_id", "STRING", "REQUIRED"], ["drug_id", "STRING", "REQUIRED"],
      ["reported_at", "TIMESTAMP", "REQUIRED"], ["as_of_date", "DATE", "REQUIRED"], ["on_hand", "INT64", "REQUIRED"],
      ["received", "INT64", "NULLABLE"], ["dispensed", "INT64", "NULLABLE"], ["unusable", "INT64", "NULLABLE"],
      ["batch_no", "STRING", "NULLABLE"], ["expiry", "DATE", "NULLABLE"], ["status", "STRING", "REQUIRED"],
      ["confidence", "STRING", "REQUIRED"], ["reporter_phone_hash", "STRING", "REQUIRED"], ["raw_message_id", "STRING", "REQUIRED"],
    ]
    bed_census = [
      ["record_id", "STRING", "REQUIRED"], ["facility_id", "STRING", "REQUIRED"], ["as_of_date", "DATE", "REQUIRED"],
      ["beds_total", "INT64", "REQUIRED"], ["beds_occupied", "INT64", "REQUIRED"], ["admissions", "INT64", "NULLABLE"],
      ["discharges", "INT64", "NULLABLE"], ["status", "STRING", "REQUIRED"], ["confidence", "STRING", "REQUIRED"],
      ["raw_message_id", "STRING", "REQUIRED"],
    ]
    checkins = [
      ["record_id", "STRING", "REQUIRED"], ["facility_id", "STRING", "REQUIRED"], ["staff_id_hash", "STRING", "REQUIRED"],
      ["role", "STRING", "REQUIRED"], ["at", "TIMESTAMP", "REQUIRED"], ["lat", "FLOAT64", "REQUIRED"], ["lon", "FLOAT64", "REQUIRED"],
      ["distance_m", "FLOAT64", "REQUIRED"], ["geofence_ok", "BOOL", "REQUIRED"], ["status", "STRING", "REQUIRED"],
      ["raw_message_id", "STRING", "REQUIRED"],
    ]
  }
}

resource "google_bigquery_table" "history" {
  for_each            = local.history_tables
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.history.dataset_id
  table_id            = each.key
  deletion_protection = true
  schema              = jsonencode([for c in each.value : { name = c[0], type = c[1], mode = c[2] }])
}

resource "google_pubsub_topic" "raw_messages" {
  project    = var.project_id
  name       = "ingest.raw_message"
  depends_on = [google_project_service.required]
}

# Cloud Run has CPU only during requests, so the worker is fed by push, not a pull loop.
# The backend verifies the OIDC token (backend/api/pubsub_push.py).
resource "google_pubsub_subscription" "raw_messages_worker" {
  project              = var.project_id
  name                 = "ingest.raw_message-sub"
  topic                = google_pubsub_topic.raw_messages.id
  ack_deadline_seconds = 60

  dynamic "push_config" {
    for_each = var.backend_url == "" ? [] : [1]
    content {
      push_endpoint = "${var.backend_url}/internal/pubsub/ingest"
      oidc_token {
        service_account_email = google_service_account.pubsub_push.email
        audience              = "${var.backend_url}/internal/pubsub/ingest"
      }
    }
  }
}

resource "google_service_account" "pubsub_push" {
  project      = var.project_id
  account_id   = "pubsub-push"
  display_name = "Signs Pub/Sub push requests to the backend"
}

resource "google_service_account" "backend" {
  project      = var.project_id
  account_id   = "aushadhinet-backend"
  display_name = "AushadhiNet backend runtime"
}

resource "google_project_iam_member" "backend_roles" {
  for_each = toset([
    "roles/datastore.user",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/pubsub.publisher",
    "roles/aiplatform.user",
    "roles/speech.client",
    "roles/cloudtranslate.user",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_kms_crypto_key_iam_member" "backend_signs_orders" {
  crypto_key_id = google_kms_crypto_key.order_signing_key.id
  role          = "roles/cloudkms.signerVerifier"
  member        = "serviceAccount:${google_service_account.backend.email}"
}

# Secret containers only; add values with `gcloud secrets versions add` (never in Terraform state).
resource "google_secret_manager_secret" "app" {
  for_each  = toset(["twilio-auth-token", "gemini-api-key"])
  project   = var.project_id
  secret_id = each.key
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_iam_member" "backend_reads_secrets" {
  for_each  = google_secret_manager_secret.app
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "aushadhinet"
  format        = "DOCKER"
  depends_on    = [google_project_service.required]
}

resource "google_kms_key_ring" "order_signing" {
  project    = var.project_id
  name       = "aushadhinet-order-signing"
  location   = var.region
  depends_on = [google_project_service.required]
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

# SIGNING_KEY in .env: an asymmetric key's first version is created with the key.
output "signing_key_version" {
  value = "${google_kms_crypto_key.order_signing_key.id}/cryptoKeyVersions/1"
}

output "raw_message_topic" {
  value = google_pubsub_topic.raw_messages.name
}

output "artifact_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "backend_service_account" {
  value = google_service_account.backend.email
}

output "pubsub_push_service_account" {
  value = google_service_account.pubsub_push.email
}
