-- Align older production extraction tables with the current Gemini extraction payload.
ALTER TABLE `PROJECT_ID.finance_analytics.document_extractions`
  ADD COLUMN IF NOT EXISTS supplier_gstin STRING,
  ADD COLUMN IF NOT EXISTS recipient_gstin STRING,
  ADD COLUMN IF NOT EXISTS supplier_state_code STRING,
  ADD COLUMN IF NOT EXISTS place_of_supply STRING,
  ADD COLUMN IF NOT EXISTS b2b BOOL,
  ADD COLUMN IF NOT EXISTS classification STRING,
  ADD COLUMN IF NOT EXISTS reverse_charge BOOL,
  ADD COLUMN IF NOT EXISTS irn STRING,
  ADD COLUMN IF NOT EXISTS acknowledgement_number STRING,
  ADD COLUMN IF NOT EXISTS acknowledgement_date DATE,
  ADD COLUMN IF NOT EXISTS signed_qr_detected BOOL,
  ADD COLUMN IF NOT EXISTS validation_report STRING;
