-- Review and apply only to the intended environment. No historical identities
-- are silently marked verified. NULL means legacy identity requiring migration policy.
ALTER TABLE `aidirac-503309.finance_analytics.users` ADD COLUMN IF NOT EXISTS email_verified BOOL;
CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.auth_guard` (
  id STRING NOT NULL, touched_at TIMESTAMP NOT NULL
);
INSERT INTO `aidirac-503309.finance_analytics.auth_guard` (id,touched_at)
SELECT 'identity',CURRENT_TIMESTAMP() FROM UNNEST([1])
WHERE NOT EXISTS (SELECT 1 FROM `aidirac-503309.finance_analytics.auth_guard` WHERE id='identity');
CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.auth_tokens` (
  token_hash STRING NOT NULL, user_id STRING NOT NULL, purpose STRING NOT NULL,
  created_at TIMESTAMP NOT NULL, expires_at TIMESTAMP NOT NULL, consumed_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY token_hash;
CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.auth_attempts` (
  key_hash STRING NOT NULL, created_at TIMESTAMP NOT NULL
) PARTITION BY DATE(created_at) CLUSTER BY key_hash;
CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.auth_events` (
  id STRING NOT NULL, user_id STRING, action STRING NOT NULL, created_at TIMESTAMP NOT NULL
) PARTITION BY DATE(created_at) CLUSTER BY user_id;
CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.auth_outbox` (
  id STRING NOT NULL, email STRING NOT NULL, purpose STRING NOT NULL,
  status STRING NOT NULL, created_at TIMESTAMP NOT NULL,
  lease_until TIMESTAMP, sent_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY status;
