-- Explicit operator-managed grants. Public registration never inserts here.
CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.platform_admin_grants` (
  user_id STRING NOT NULL,
  email STRING NOT NULL,
  is_active BOOL NOT NULL,
  created_at TIMESTAMP NOT NULL
);
