-- Apply manually after review; never run automatically at application startup.
ALTER TABLE `PROJECT_ID.finance_analytics.documents` ADD COLUMN IF NOT EXISTS validation_status STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.documents` ADD COLUMN IF NOT EXISTS client_filename STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS validation_report STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.audit_logs` ADD COLUMN IF NOT EXISTS client_id STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.accounts` ADD COLUMN IF NOT EXISTS client_id STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.journal_entries` ADD COLUMN IF NOT EXISTS client_id STRING;

ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS supplier_gstin STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS recipient_gstin STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS supplier_state_code STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS place_of_supply STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS b2b BOOL;
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS classification STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS reverse_charge BOOL;
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS irn STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS acknowledgement_number STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS acknowledgement_date DATE;
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions` ADD COLUMN IF NOT EXISTS signed_qr_detected BOOL;

CREATE TABLE IF NOT EXISTS `PROJECT_ID.finance_analytics.document_corrections` (
  id STRING NOT NULL,
  document_id STRING,
  extraction_id STRING,
  client_id STRING,
  user_id STRING,
  field_name STRING,
  old_value STRING,
  new_value STRING,
  source STRING,
  created_at TIMESTAMP
)
PARTITION BY DATE(created_at)
CLUSTER BY client_id, document_id;
