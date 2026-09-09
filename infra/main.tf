terraform {
  required_providers { google = { source = "hashicorp/google", version = "~> 6.0" } }
}
variable "project_id" { type=string }
variable "region" { type=string default="asia-south1" }
variable "bucket_name" { type=string }
provider "google" { project=var.project_id region=var.region }
resource "google_project_service" "apis" {
  for_each=toset(["run.googleapis.com","artifactregistry.googleapis.com","secretmanager.googleapis.com","storage.googleapis.com","bigquery.googleapis.com","logging.googleapis.com","aiplatform.googleapis.com"])
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
    users=[{name="id",type="STRING",mode="REQUIRED"},{name="email",type="STRING"},{name="password_hash",type="STRING"},{name="full_name",type="STRING"},{name="role",type="STRING"},{name="is_active",type="BOOL"},{name="created_at",type="TIMESTAMP"}],
    accounts=[{name="id",type="STRING",mode="REQUIRED"},{name="code",type="STRING"},{name="name",type="STRING"},{name="account_type",type="STRING"},{name="is_active",type="BOOL"},{name="created_at",type="TIMESTAMP"}],
    journal_entries=[{name="id",type="STRING",mode="REQUIRED"},{name="entry_date",type="DATE"},{name="reference",type="STRING"},{name="description",type="STRING"},{name="source",type="STRING"},{name="status",type="STRING"},{name="created_at",type="TIMESTAMP"}],
    journal_lines=[{name="id",type="STRING",mode="REQUIRED"},{name="journal_entry_id",type="STRING"},{name="account_id",type="STRING"},{name="debit",type="NUMERIC"},{name="credit",type="NUMERIC"}],
    documents=[{name="id",type="STRING",mode="REQUIRED"},{name="document_type",type="STRING"},{name="status",type="STRING"},{name="original_filename",type="STRING"},{name="mime_type",type="STRING"},{name="file_size",type="INT64"},{name="checksum_sha256",type="STRING"},{name="bucket_name",type="STRING"},{name="object_path",type="STRING"},{name="gcs_uri",type="STRING"},{name="uploaded_by_id",type="STRING"},{name="uploaded_at",type="TIMESTAMP"},{name="processing_error",type="STRING"}],
    document_extractions=[{name="id",type="STRING",mode="REQUIRED"},{name="document_id",type="STRING"},{name="vendor_name",type="STRING"},{name="vendor_address",type="STRING"},{name="invoice_number",type="STRING"},{name="invoice_date",type="DATE"},{name="due_date",type="DATE"},{name="gstin",type="STRING"},{name="subtotal",type="NUMERIC"},{name="tax_amount",type="NUMERIC"},{name="cgst",type="NUMERIC"},{name="sgst",type="NUMERIC"},{name="igst",type="NUMERIC"},{name="discount_amount",type="NUMERIC"},{name="total_amount",type="NUMERIC"},{name="currency",type="STRING"},{name="payment_method",type="STRING"},{name="ocr_text",type="STRING"},{name="ocr_confidence",type="NUMERIC"},{name="created_at",type="TIMESTAMP"}],
    document_line_items=[{name="id",type="STRING",mode="REQUIRED"},{name="extraction_id",type="STRING"},{name="line_number",type="INT64"},{name="item_name",type="STRING"},{name="description",type="STRING"},{name="quantity",type="NUMERIC"},{name="unit",type="STRING"},{name="unit_price",type="NUMERIC"},{name="tax",type="NUMERIC"},{name="discount",type="NUMERIC"},{name="total",type="NUMERIC"}],
    audit_logs=[{name="id",type="STRING",mode="REQUIRED"},{name="user_id",type="STRING"},{name="action",type="STRING"},{name="entity",type="STRING"},{name="entity_id",type="STRING"},{name="old_value",type="STRING"},{name="new_value",type="STRING"},{name="created_at",type="TIMESTAMP"}],
    document_embeddings=[{name="id",type="STRING",mode="REQUIRED"},{name="document_id",type="STRING"},{name="content",type="STRING"},{name="embedding",type="FLOAT64",mode="REPEATED"},{name="document_type",type="STRING"},{name="status",type="STRING"},{name="vendor_name",type="STRING"},{name="invoice_number",type="STRING"},{name="gstin",type="STRING"},{name="total_amount",type="NUMERIC"},{name="gcs_uri",type="STRING"},{name="created_at",type="TIMESTAMP"}]
  }
}
resource "google_bigquery_table" "app" {
  for_each=local.tables
  dataset_id=google_bigquery_dataset.finance.dataset_id
  table_id=each.key
  schema=jsonencode(each.value)
  deletion_protection=true
}
resource "google_project_iam_member" "storage_writer" { project=var.project_id role="roles/storage.objectCreator" member="serviceAccount:${google_service_account.app.email}" }
resource "google_project_iam_member" "bq_editor" { project=var.project_id role="roles/bigquery.dataEditor" member="serviceAccount:${google_service_account.app.email}" }
resource "google_project_iam_member" "bq_job_user" { project=var.project_id role="roles/bigquery.jobUser" member="serviceAccount:${google_service_account.app.email}" }
resource "google_project_iam_member" "vertex_ai" { project=var.project_id role="roles/aiplatform.user" member="serviceAccount:${google_service_account.app.email}" }
