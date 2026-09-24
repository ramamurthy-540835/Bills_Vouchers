-- v5 additive migration. Apply only to aidirac-503309.finance_analytics.
ALTER TABLE `aidirac-503309.finance_analytics.gst_client_profile`
 ADD COLUMN IF NOT EXISTS business_nature STRING,
 ADD COLUMN IF NOT EXISTS is_eco_9_5 BOOL,
 ADD COLUMN IF NOT EXISTS has_rcm_supplies BOOL,
 ADD COLUMN IF NOT EXISTS composition_flag BOOL,
 ADD COLUMN IF NOT EXISTS fy_turnover_band STRING,
 ADD COLUMN IF NOT EXISTS itc_rate_restricted BOOL;

CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.bronze_document` (
  doc_id STRING,
  client_id STRING,
  period STRING,
  gcs_uri STRING,
  content_hash STRING,
  mime_type STRING,
  byte_size INT64,
  original_filename STRING,
  source_channel STRING,
  uploaded_by STRING,
  uploaded_at TIMESTAMP,
  ingest_date DATE
) PARTITION BY ingest_date CLUSTER BY client_id, period;

CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.bronze_gstr2b_import` (
  import_id STRING,
  client_id STRING,
  period STRING,
  gcs_uri STRING,
  content_hash STRING,
  imported_by STRING,
  imported_at TIMESTAMP
) PARTITION BY DATE(imported_at) CLUSTER BY client_id, period;

CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.silver_invoice_header` (
  doc_id STRING,
  client_id STRING,
  period STRING,
  supplier_gstin STRING,
  supplier_name STRING,
  invoice_no STRING,
  invoice_date DATE,
  place_of_supply STRING,
  taxable_value NUMERIC,
  igst NUMERIC,
  cgst NUMERIC,
  sgst NUMERIC,
  cess NUMERIC,
  total NUMERIC,
  extraction_confidence NUMERIC,
  extraction_engine STRING,
  extracted_at TIMESTAMP,
  validation_status STRING,
  validation_errors ARRAY<STRING>,
  reviewed_by STRING,
  reviewed_at TIMESTAMP
) PARTITION BY DATE(extracted_at) CLUSTER BY client_id, period;

CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.silver_invoice_line` (
  doc_id STRING,
  client_id STRING,
  period STRING,
  line_no INT64,
  description STRING,
  hsn_sac STRING,
  qty NUMERIC,
  rate NUMERIC,
  tax_rate NUMERIC,
  taxable_value NUMERIC,
  igst NUMERIC,
  cgst NUMERIC,
  sgst NUMERIC,
  cess NUMERIC,
  itc_category STRING,
  seating_capacity INT64,
  unpaid_days INT64,
  blocked_clause STRING,
  common_credit BOOL,
  capital_goods BOOL,
  invoice_date DATE,
  extracted_at TIMESTAMP
) PARTITION BY DATE(extracted_at) CLUSTER BY client_id, period;

CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.silver_gstr2b_invoice` (
  client_id STRING,
  period STRING,
  import_id STRING,
  supplier_gstin STRING,
  invoice_no STRING,
  invoice_date DATE,
  taxable_value NUMERIC,
  igst NUMERIC,
  cgst NUMERIC,
  sgst NUMERIC,
  cess NUMERIC,
  imported_at TIMESTAMP
) PARTITION BY DATE(imported_at) CLUSTER BY client_id, period;

CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.silver_outward_invoice` (
  client_id STRING,
  period STRING,
  invoice_no STRING,
  invoice_date DATE,
  recipient_gstin STRING,
  place_of_supply STRING,
  sac STRING,
  eco_9_5 BOOL,
  taxable_value NUMERIC,
  igst NUMERIC,
  cgst NUMERIC,
  sgst NUMERIC,
  cess NUMERIC,
  created_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY client_id, period;

CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.gold_itc_ledger` (
  client_id STRING,
  period STRING,
  doc_id STRING,
  line_no INT64,
  run_id STRING,
  reason_code STRING,
  rule_ref STRING,
  invoice_no STRING,
  description STRING,
  eligible_igst NUMERIC,
  eligible_cgst NUMERIC,
  eligible_sgst NUMERIC,
  eligible_cess NUMERIC,
  blocked_igst NUMERIC,
  blocked_cgst NUMERIC,
  blocked_sgst NUMERIC,
  blocked_cess NUMERIC,
  deferred_igst NUMERIC,
  deferred_cgst NUMERIC,
  deferred_sgst NUMERIC,
  deferred_cess NUMERIC,
  reversal_igst NUMERIC,
  reversal_cgst NUMERIC,
  reversal_sgst NUMERIC,
  reversal_cess NUMERIC,
  non_gst NUMERIC,
  computed_at TIMESTAMP
) PARTITION BY DATE(computed_at) CLUSTER BY client_id, period;

CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.gold_gstr2b_match` (
  client_id STRING,
  period STRING,
  doc_id STRING,
  supplier_gstin STRING,
  invoice_no STRING,
  match_status STRING,
  delta NUMERIC,
  run_id STRING,
  computed_at TIMESTAMP
) PARTITION BY DATE(computed_at) CLUSTER BY client_id, period;

CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.gold_filing_summary` (
  client_id STRING,
  period STRING,
  run_id STRING,
  input_hash STRING,
  as_booked NUMERIC,
  restricted_2b NUMERIC,
  fully_compliant NUMERIC,
  if_late_file NUMERIC,
  output_by_head JSON,
  eligible_by_head JSON,
  input_by_head JSON,
  net_payable_by_head JSON,
  cash_by_head JSON,
  eco_by_head JSON,
  cash_required NUMERIC,
  non_gst NUMERIC,
  computed_at TIMESTAMP
) PARTITION BY DATE(computed_at) CLUSTER BY client_id, period;

CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.gst_filing_status` (
  client_id STRING,
  period STRING,
  state STRING,
  arn STRING,
  filed_at DATE,
  actor_email STRING,
  effective_from TIMESTAMP,
  effective_to TIMESTAMP,
  is_current BOOL
) PARTITION BY DATE(effective_from) CLUSTER BY client_id, period;

CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.gst_filing_audit` (
  audit_id STRING,
  client_id STRING,
  period STRING,
  from_state STRING,
  to_state STRING,
  actor_email STRING,
  artefact_uri STRING,
  content_hash STRING,
  created_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY client_id, period;
