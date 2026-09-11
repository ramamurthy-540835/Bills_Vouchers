terraform {
  required_providers { google = { source = "hashicorp/google", version = "~> 6.0" } }
}
variable "project_id" { type=string }
variable "region" { type=string default="asia-south1" }
variable "bucket_name" { type=string }
variable "cloud_run_service" { type=string default="bills-voucher" }
variable "frontend_service" { type=string default="bills-voucher-web" }
variable "backend_image" { type=string }
variable "frontend_image" { type=string }
variable "app_secret_name" { type=string default="bills-voucher-app-secret" }
variable "cloud_tasks_queue" { type=string default="scan" }
provider "google" { project=var.project_id region=var.region }
resource "google_project_service" "apis" {
  for_each=toset(["run.googleapis.com","artifactregistry.googleapis.com","secretmanager.googleapis.com","storage.googleapis.com","bigquery.googleapis.com","logging.googleapis.com","aiplatform.googleapis.com","cloudtasks.googleapis.com"])
  service=each.value
  disable_on_destroy=false
}
resource "google_service_account" "app" { account_id="bills-voucher-app" display_name="Bills Voucher BigQuery App" }
resource "google_storage_bucket" "documents" { name=var.bucket_name location=var.region uniform_bucket_level_access=true public_access_prevention="enforced" force_destroy=false }
resource "google_bigquery_dataset" "finance" { dataset_id="finance_analytics" location=var.region }
locals {
  tables={
    clients=[{name="id",type="STRING",mode="REQUIRED"},{name="code",type="STRING"},{name="name",type="STRING"},{name="gstin",type="STRING"},{name="address",type="STRING"},{name="is_active",type="BOOL"},{name="created_at",type="TIMESTAMP"}],
    client_memberships=[{name="id",type="STRING",mode="REQUIRED"},{name="client_id",type="STRING"},{name="user_id",type="STRING"},{name="access_role",type="STRING"},{name="is_active",type="BOOL"},{name="created_at",type="TIMESTAMP"}],
    users=[{name="id",type="STRING",mode="REQUIRED"},{name="email",type="STRING"},{name="password_hash",type="STRING"},{name="must_change_password",type="BOOL"},{name="session_version",type="INT64"},{name="full_name",type="STRING"},{name="role",type="STRING"},{name="is_active",type="BOOL"},{name="created_at",type="TIMESTAMP"}],
    accounts=[{name="id",type="STRING",mode="REQUIRED"},{name="client_id",type="STRING"},{name="code",type="STRING"},{name="name",type="STRING"},{name="account_type",type="STRING"},{name="is_active",type="BOOL"},{name="created_at",type="TIMESTAMP"}],
    journal_entries=[{name="id",type="STRING",mode="REQUIRED"},{name="client_id",type="STRING"},{name="entry_date",type="DATE"},{name="reference",type="STRING"},{name="description",type="STRING"},{name="source",type="STRING"},{name="status",type="STRING"},{name="created_at",type="TIMESTAMP"}],
    journal_lines=[{name="id",type="STRING",mode="REQUIRED"},{name="journal_entry_id",type="STRING"},{name="account_id",type="STRING"},{name="debit",type="NUMERIC"},{name="credit",type="NUMERIC"}],
    documents=[{name="id",type="STRING",mode="REQUIRED"},{name="client_id",type="STRING"},{name="document_type",type="STRING"},{name="status",type="STRING"},{name="validation_status",type="STRING"},{name="original_filename",type="STRING"},{name="client_filename",type="STRING"},{name="mime_type",type="STRING"},{name="file_size",type="INT64"},{name="checksum_sha256",type="STRING"},{name="bucket_name",type="STRING"},{name="object_path",type="STRING"},{name="gcs_uri",type="STRING"},{name="uploaded_by_id",type="STRING"},{name="uploaded_at",type="TIMESTAMP"},{name="processing_error",type="STRING"}],
    document_extractions=[{name="id",type="STRING",mode="REQUIRED"},{name="document_id",type="STRING"},{name="vendor_name",type="STRING"},{name="vendor_address",type="STRING"},{name="invoice_number",type="STRING"},{name="invoice_date",type="DATE"},{name="due_date",type="DATE"},{name="gstin",type="STRING"},{name="supplier_gstin",type="STRING"},{name="recipient_gstin",type="STRING"},{name="supplier_state_code",type="STRING"},{name="place_of_supply",type="STRING"},{name="b2b",type="BOOL"},{name="classification",type="STRING"},{name="reverse_charge",type="BOOL"},{name="irn",type="STRING"},{name="acknowledgement_number",type="STRING"},{name="acknowledgement_date",type="DATE"},{name="signed_qr_detected",type="BOOL"},{name="subtotal",type="NUMERIC"},{name="tax_amount",type="NUMERIC"},{name="cgst",type="NUMERIC"},{name="sgst",type="NUMERIC"},{name="igst",type="NUMERIC"},{name="discount_amount",type="NUMERIC"},{name="total_amount",type="NUMERIC"},{name="currency",type="STRING"},{name="payment_method",type="STRING"},{name="ocr_text",type="STRING"},{name="ocr_confidence",type="NUMERIC"},{name="validation_report",type="STRING"},{name="field_confidence",type="STRING"},{name="created_at",type="TIMESTAMP"}],
    document_line_items=[{name="id",type="STRING",mode="REQUIRED"},{name="extraction_id",type="STRING"},{name="line_number",type="INT64"},{name="item_name",type="STRING"},{name="description",type="STRING"},{name="hsn",type="STRING"},{name="sac",type="STRING"},{name="quantity",type="NUMERIC"},{name="unit",type="STRING"},{name="unit_price",type="NUMERIC"},{name="taxable_value",type="NUMERIC"},{name="rate",type="NUMERIC"},{name="tax",type="NUMERIC"},{name="discount",type="NUMERIC"},{name="total",type="NUMERIC"}],
    document_corrections=[{name="id",type="STRING",mode="REQUIRED"},{name="document_id",type="STRING"},{name="extraction_id",type="STRING"},{name="client_id",type="STRING"},{name="user_id",type="STRING"},{name="field_name",type="STRING"},{name="old_value",type="STRING"},{name="new_value",type="STRING"},{name="source",type="STRING"},{name="created_at",type="TIMESTAMP"}],
    audit_logs=[{name="id",type="STRING",mode="REQUIRED"},{name="client_id",type="STRING"},{name="user_id",type="STRING"},{name="action",type="STRING"},{name="entity",type="STRING"},{name="entity_id",type="STRING"},{name="old_value",type="STRING"},{name="new_value",type="STRING"},{name="created_at",type="TIMESTAMP"}],
    document_embeddings=[{name="id",type="STRING",mode="REQUIRED"},{name="document_id",type="STRING"},{name="client_id",type="STRING"},{name="content",type="STRING"},{name="embedding",type="FLOAT64",mode="REPEATED"},{name="document_type",type="STRING"},{name="status",type="STRING"},{name="vendor_name",type="STRING"},{name="invoice_number",type="STRING"},{name="gstin",type="STRING"},{name="total_amount",type="NUMERIC"},{name="gcs_uri",type="STRING"},{name="created_at",type="TIMESTAMP"}]
  }
}
locals {
  partition_fields = {
    documents = "uploaded_at"
    document_extractions = "created_at"
    document_corrections = "created_at"
    audit_logs = "created_at"
    document_embeddings = "created_at"
    journal_entries = "created_at"
  }
  cluster_fields = {
    documents = ["client_id", "status"]
    document_extractions = ["document_id"]
    document_corrections = ["client_id", "document_id"]
    audit_logs = ["client_id", "entity"]
    document_embeddings = ["document_type", "status"]
    journal_entries = ["client_id", "entry_date"]
  }
  unpartitioned_tables = { for name, schema in local.tables : name => schema if !contains(keys(local.partition_fields), name) }
  partitioned_tables = { for name, schema in local.tables : name => schema if contains(keys(local.partition_fields), name) }
}
resource "google_bigquery_table" "app" {
  for_each=local.unpartitioned_tables
  dataset_id=google_bigquery_dataset.finance.dataset_id
  table_id=each.key
  schema=jsonencode(each.value)
  deletion_protection=true
}
resource "google_bigquery_table" "partitioned" {
  for_each = local.partitioned_tables
  dataset_id = google_bigquery_dataset.finance.dataset_id
  table_id = each.key
  schema = jsonencode(each.value)
  deletion_protection = true
  time_partitioning {
    type = "DAY"
    field = local.partition_fields[each.key]
  }
  clustering = local.cluster_fields[each.key]
}
resource "google_project_iam_member" "storage_writer" { project=var.project_id role="roles/storage.objectCreator" member="serviceAccount:${google_service_account.app.email}" }
resource "google_storage_bucket_iam_member" "storage_reader" { bucket=google_storage_bucket.documents.name role="roles/storage.objectViewer" member="serviceAccount:${google_service_account.app.email}" }
resource "google_project_iam_member" "bq_editor" { project=var.project_id role="roles/bigquery.dataEditor" member="serviceAccount:${google_service_account.app.email}" }
resource "google_project_iam_member" "bq_job_user" { project=var.project_id role="roles/bigquery.jobUser" member="serviceAccount:${google_service_account.app.email}" }
resource "google_project_iam_member" "vertex_ai" { project=var.project_id role="roles/aiplatform.user" member="serviceAccount:${google_service_account.app.email}" }
resource "google_cloud_tasks_queue" "scan" {
  name = var.cloud_tasks_queue
  location = var.region
  retry_config { max_attempts = 5 max_retry_duration = "3600s" max_backoff = "300s" }
}
resource "google_project_iam_member" "tasks_enqueuer" { project=var.project_id role="roles/cloudtasks.enqueuer" member="serviceAccount:${google_service_account.app.email}" }
resource "google_cloud_run_service_iam_member" "tasks_invoker" {
  project=var.project_id
  location=var.region
  service=var.cloud_run_service
  role="roles/run.invoker"
  member="serviceAccount:${google_service_account.app.email}"
}
resource "google_secret_manager_secret" "app_secret" {
  secret_id = var.app_secret_name
  replication { auto {} }
}
resource "google_secret_manager_secret_iam_member" "app_secret_access" {
  secret_id = google_secret_manager_secret.app_secret.secret_id
  role = "roles/secretmanager.secretAccessor"
  member = "serviceAccount:${google_service_account.app.email}"
}
resource "google_cloud_run_v2_service" "backend" {
  name = var.cloud_run_service
  location = var.region
  deletion_protection = true
  template {
    service_account = google_service_account.app.email
    max_instance_request_concurrency = 40
    scaling { max_instance_count = 10 }
    containers {
      image = var.backend_image
      resources { limits = { cpu = "1", memory = "1Gi" } }
      env { name = "APP_ENV" value = "production" }
      env { name = "GCP_PROJECT_ID" value = var.project_id }
      env { name = "GCP_REGION" value = "global" }
      env { name = "GCS_BUCKET_NAME" value = var.bucket_name }
      env { name = "BIGQUERY_DATASET" value = "finance_analytics" }
      env { name = "CLOUD_TASKS_QUEUE" value = "projects/${var.project_id}/locations/${var.region}/queues/${var.cloud_tasks_queue}" }
      env { name = "CLOUD_TASKS_SERVICE_URL" value = google_cloud_run_v2_service.backend.uri }
      env { name = "CLOUD_TASKS_SERVICE_ACCOUNT" value = google_service_account.app.email }
      env { name = "APP_SECRET_KEY" value_source { secret_key_ref { secret = google_secret_manager_secret.app_secret.secret_id version = "latest" } } }
    }
  }
}
resource "google_cloud_run_v2_service" "frontend" {
  name = var.frontend_service
  location = var.region
  deletion_protection = true
  template {
    service_account = google_service_account.app.email
    max_instance_request_concurrency = 80
    scaling { max_instance_count = 10 }
    containers {
      image = var.frontend_image
      resources { limits = { cpu = "1", memory = "512Mi" } }
      env { name = "BACKEND_URL" value = google_cloud_run_v2_service.backend.uri }
    }
  }
}
