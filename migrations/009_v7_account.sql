-- Additive account fields; existing identities and memberships are preserved.
ALTER TABLE `aidirac-503309.finance_analytics.users` ADD COLUMN IF NOT EXISTS mobile_number STRING;
ALTER TABLE `aidirac-503309.finance_analytics.users` ADD COLUMN IF NOT EXISTS mobile_verified BOOL;
ALTER TABLE `aidirac-503309.finance_analytics.users` ADD COLUMN IF NOT EXISTS last_sign_in TIMESTAMP;
ALTER TABLE `aidirac-503309.finance_analytics.gst_client_profile` ADD COLUMN IF NOT EXISTS contact_phone STRING;
ALTER TABLE `aidirac-503309.finance_analytics.gst_client_profile` ADD COLUMN IF NOT EXISTS contact_person STRING;
ALTER TABLE `aidirac-503309.finance_analytics.gst_client_profile` ADD COLUMN IF NOT EXISTS gstin_verified BOOL;
