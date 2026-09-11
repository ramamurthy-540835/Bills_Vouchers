-- Phase 2: separate GST purchase, 2B, validation, and matching workspaces.
CREATE TABLE IF NOT EXISTS `PROJECT_ID.finance_analytics.gst_purchase_invoices` (
  id STRING NOT NULL, client_id STRING NOT NULL, supplier_name STRING, supplier_gstin STRING,
  invoice_number STRING, invoice_date DATE, taxable_value NUMERIC, igst NUMERIC, cgst NUMERIC,
  sgst NUMERIC, cess NUMERIC, total_amount NUMERIC, hsn_sac STRING, itc_eligible BOOL,
  source STRING, created_at TIMESTAMP, updated_at TIMESTAMP
) PARTITION BY invoice_date CLUSTER BY client_id, supplier_gstin;
CREATE TABLE IF NOT EXISTS `PROJECT_ID.finance_analytics.gstr2b_invoices` (
  id STRING NOT NULL, client_id STRING NOT NULL, supplier_name STRING, supplier_gstin STRING,
  invoice_number STRING, invoice_date DATE, taxable_value NUMERIC, igst NUMERIC, cgst NUMERIC,
  sgst NUMERIC, cess NUMERIC, total_amount NUMERIC, itc_eligible BOOL, return_period DATE,
  source_file STRING, created_at TIMESTAMP
) PARTITION BY invoice_date CLUSTER BY client_id, supplier_gstin;
CREATE TABLE IF NOT EXISTS `PROJECT_ID.finance_analytics.gst_reconciliation_matches` (
  id STRING NOT NULL, client_id STRING NOT NULL, purchase_invoice_id STRING, gstr2b_invoice_id STRING,
  match_status STRING, match_confidence NUMERIC, mismatch_type STRING, mismatch_amount NUMERIC,
  recommended_action STRING, reviewed_by_id STRING, reviewed_at TIMESTAMP, created_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY client_id, match_status;
CREATE TABLE IF NOT EXISTS `PROJECT_ID.finance_analytics.gst_validation_issues` (
  id STRING NOT NULL, client_id STRING NOT NULL, document_id STRING, issue_code STRING,
  severity STRING, field STRING, problem STRING, reason STRING, recommended_fix STRING,
  status STRING, created_at TIMESTAMP, resolved_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY client_id, status;
