-- Explicit owner membership for future registrations is set by application code.
-- Review this narrowly-scoped backfill before applying: only the creator of a
-- SELF_REGISTRATION profile with an existing active membership becomes owner.
UPDATE `aidirac-503309.finance_analytics.client_memberships` m SET access_role='owner'
WHERE m.is_active=TRUE AND m.access_role='client' AND EXISTS (
  SELECT 1 FROM `aidirac-503309.finance_analytics.gst_client_profile` p
  WHERE p.client_id=m.client_id AND p.created_by=m.user_id AND p.source='SELF_REGISTRATION'
);
ALTER TABLE `aidirac-503309.finance_analytics.gst_client_profile` ADD COLUMN IF NOT EXISTS onboarding_completed BOOL;
CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.workspace_invitations` (
  id STRING NOT NULL, client_id STRING NOT NULL, email STRING NOT NULL,
  role STRING NOT NULL, token_hash STRING NOT NULL, inviter_id STRING NOT NULL,
  created_at TIMESTAMP NOT NULL, expires_at TIMESTAMP NOT NULL,
  accepted_by STRING, accepted_at TIMESTAMP, revoked_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY client_id, email;
CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.profile_audit` (
  id STRING NOT NULL, client_id STRING NOT NULL, actor_id STRING NOT NULL,
  action STRING NOT NULL, before_value JSON, after_value JSON, created_at TIMESTAMP NOT NULL
) PARTITION BY DATE(created_at) CLUSTER BY client_id;
