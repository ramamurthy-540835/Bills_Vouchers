-- Explicitly isolated test tenants; existing clients remain non-test (NULL).
ALTER TABLE `aidirac-503309.finance_analytics.clients`
ADD COLUMN IF NOT EXISTS is_test BOOL;
