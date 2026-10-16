-- Additive only: no customer row update or historical migration replay.
ALTER TABLE `aidirac-503309.finance_analytics.gst_client_profile`
ADD COLUMN IF NOT EXISTS website_url STRING;
