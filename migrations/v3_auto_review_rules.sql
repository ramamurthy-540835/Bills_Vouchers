-- Additive template only; requires reviewed isolated V3 candidate dataset values.
-- No rules are seeded: unconfigured/expired rules always require manual review.
CREATE TABLE IF NOT EXISTS `PROJECT.V3_OPS.gst_auto_review_rules` (
 client_id STRING NOT NULL, enabled BOOL NOT NULL, policy JSON NOT NULL
) CLUSTER BY client_id;
-- Policy JSON: policy_id, review_status=approved, approved_by, official_source,
-- identity_evidence, supplier_gstin, recipient_gstin, hsn_sac, direction,
-- supply_type, place_of_supply, invoice_type, rate (decimal text),
-- effective_from/effective_to (ISO date), review_expires_at (UTC ISO timestamp).
-- Populate only after specialist approval. No browser endpoint writes these rules.
