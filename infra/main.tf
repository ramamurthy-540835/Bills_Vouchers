terraform {
  required_providers { google = { source = "hashicorp/google", version = "~> 6.0" } }
}
variable "project_id" { type = string }
variable "region" {
  type = string
  default = "asia-south1"
}
variable "bucket_name" { type = string }
variable "cloud_run_service" {
  type = string
  default = "bills-voucher"
}
provider "google" {
  project = var.project_id
  region = var.region
}

resource "google_project_service" "apis" {
  for_each = toset(["run.googleapis.com","artifactregistry.googleapis.com","secretmanager.googleapis.com","storage.googleapis.com","bigquery.googleapis.com","documentai.googleapis.com","eventarc.googleapis.com","logging.googleapis.com","sqladmin.googleapis.com"])
  service = each.value
  disable_on_destroy = false
}
resource "google_service_account" "app" { account_id="bills-voucher-app" display_name="Bills Voucher Cloud Run" }
resource "google_storage_bucket" "documents" { name=var.bucket_name location=var.region uniform_bucket_level_access=true public_access_prevention="enforced" force_destroy=false }
resource "google_bigquery_dataset" "finance" { dataset_id="finance_analytics" location=var.region }
resource "google_bigquery_table" "documents" {
  dataset_id=google_bigquery_dataset.finance.dataset_id
  table_id="document_extractions"
  schema=jsonencode([{name="document_id",type="STRING",mode="REQUIRED"},{name="document_type",type="STRING"},{name="vendor_name",type="STRING"},{name="invoice_number",type="STRING"},{name="invoice_date",type="DATE"},{name="subtotal",type="NUMERIC"},{name="cgst",type="NUMERIC"},{name="sgst",type="NUMERIC"},{name="igst",type="NUMERIC"},{name="total_amount",type="NUMERIC"},{name="currency",type="STRING"},{name="payment_method",type="STRING"},{name="gcs_uri",type="STRING"},{name="ocr_text",type="STRING"},{name="status",type="STRING"},{name="uploaded_at",type="TIMESTAMP"}])
  time_partitioning { type="DAY" field="uploaded_at" }
  clustering=["document_type","status"]
}
resource "google_project_iam_member" "storage_writer" { project=var.project_id role="roles/storage.objectCreator" member="serviceAccount:${google_service_account.app.email}" }
resource "google_project_iam_member" "bq_writer" { project=var.project_id role="roles/bigquery.dataEditor" member="serviceAccount:${google_service_account.app.email}" }
resource "google_project_iam_member" "document_ai" { project=var.project_id role="roles/documentai.apiUser" member="serviceAccount:${google_service_account.app.email}" }
resource "google_project_iam_member" "secret_accessor" { project=var.project_id role="roles/secretmanager.secretAccessor" member="serviceAccount:${google_service_account.app.email}" }
