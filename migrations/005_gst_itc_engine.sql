-- Additive GST filing and ITC engine schema. Replace PROJECT_ID/DATASET at execution time.
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET.gst_client_profile` (
  profile_id STRING NOT NULL, client_id STRING NOT NULL, gstin STRING NOT NULL, pan STRING,
  state_code STRING, entity_code STRING, legal_name STRING NOT NULL, trade_name STRING,
  constitution STRING, registration_type STRING, registration_date DATE, cancellation_date DATE,
  status STRING, filing_frequency STRING, qrmp_payment_method STRING, composition_scheme BOOL,
  composition_rate_pct NUMERIC, einvoice_applicable BOOL, einvoice_threshold_fy STRING,
  ewaybill_applicable BOOL, aato_prev_fy NUMERIC, hsn_digit_requirement INT64,
  principal_address STRING, principal_pincode STRING,
  additional_places JSON, jurisdiction_centre STRING, jurisdiction_state STRING,
  authorized_signatory JSON, bank_accounts JSON, itc_rule_flags JSON,
  contact_email STRING, contact_mobile STRING, portal_username STRING,
  effective_from TIMESTAMP NOT NULL, effective_to TIMESTAMP, is_current BOOL NOT NULL,
  source STRING, created_by STRING, created_at TIMESTAMP NOT NULL
) PARTITION BY DATE(created_at) CLUSTER BY client_id, gstin;

CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET.gst_state_master` (
  state_code STRING NOT NULL, state_name STRING NOT NULL, is_active BOOL NOT NULL, created_at TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET.gst_blocked_credit_master` (
  clause STRING NOT NULL, description STRING NOT NULL, exception_conditions STRING, is_active BOOL NOT NULL, created_at TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET.gst_itc_runs` (
  run_id STRING NOT NULL, client_id STRING NOT NULL, gstin STRING NOT NULL, ret_period STRING NOT NULL,
  scenario_name STRING NOT NULL, input_sha256 STRING NOT NULL, result JSON NOT NULL, created_by STRING, created_at TIMESTAMP NOT NULL
) PARTITION BY DATE(created_at) CLUSTER BY client_id, ret_period;
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET.itc_reversal_detail` (
  reversal_id STRING NOT NULL, run_id STRING NOT NULL, client_id STRING NOT NULL, invoice_ref STRING,
  reversal_type STRING NOT NULL, tax_head STRING NOT NULL, amount NUMERIC NOT NULL, reclaim_eligible_from DATE,
  created_at TIMESTAMP NOT NULL
) PARTITION BY DATE(created_at) CLUSTER BY client_id, reversal_type;
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET.gstr_return_json` (
  return_id STRING NOT NULL, client_id STRING NOT NULL, gstin STRING NOT NULL, return_type STRING NOT NULL,
  ret_period STRING NOT NULL, schema_version STRING, schema_unverified BOOL NOT NULL, payload JSON NOT NULL,
  payload_sha256 STRING NOT NULL, itc_run_id STRING, validation_errors JSON, status STRING NOT NULL,
  version_no INT64 NOT NULL, generated_by STRING, generated_at TIMESTAMP NOT NULL, filed_arn STRING, filed_at TIMESTAMP
) PARTITION BY DATE(generated_at) CLUSTER BY client_id, return_type, ret_period;
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET.gst_audit_log` (
  audit_id STRING NOT NULL, client_id STRING NOT NULL, user_id STRING, action STRING NOT NULL,
  entity_type STRING NOT NULL, entity_id STRING, details JSON, created_at TIMESTAMP NOT NULL
) PARTITION BY DATE(created_at) CLUSTER BY client_id, action;
