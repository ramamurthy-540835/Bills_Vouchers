-- Additive medallion metadata. Existing source files remain untouched.
ALTER TABLE `PROJECT_ID.finance_analytics.documents`
  ADD COLUMN IF NOT EXISTS storage_layer STRING;
ALTER TABLE `PROJECT_ID.finance_analytics.documents`
  ADD COLUMN IF NOT EXISTS curated_filename STRING;

-- Bronze: immutable GCS source at bronze/customer_id=<id>/...
-- Silver: document_extractions and document_line_items (cleaned fields).
-- Gold: GST return/ITC reporting tables (curated client facts).
-- Historical rows are deliberately not moved or rewritten.
