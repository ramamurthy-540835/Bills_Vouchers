CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.mobile_challenges` (
  id STRING NOT NULL, user_id STRING NOT NULL, mobile_number STRING NOT NULL,
  provider_sid STRING NOT NULL, created_at TIMESTAMP NOT NULL,
  expires_at TIMESTAMP NOT NULL, consumed_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY user_id;
