-- Additive SCD-2 client role mapping. Apply manually through the approved migration process.
CREATE TABLE IF NOT EXISTS `PROJECT_ID.finance_analytics.client_user_role` (
  email STRING NOT NULL,
  client_id STRING NOT NULL,
  role STRING NOT NULL,
  effective_from TIMESTAMP NOT NULL,
  effective_to TIMESTAMP,
  is_current BOOL NOT NULL
) PARTITION BY DATE(effective_from) CLUSTER BY client_id, email;

-- Existing memberships are seeded as client access only. No admin grants are created here.
INSERT INTO `PROJECT_ID.finance_analytics.client_user_role` (email, client_id, role, effective_from, effective_to, is_current)
SELECT LOWER(u.email), m.client_id, 'client', CURRENT_TIMESTAMP(), NULL, TRUE
FROM `PROJECT_ID.finance_analytics.users` u
JOIN `PROJECT_ID.finance_analytics.client_memberships` m ON m.user_id = u.id
WHERE m.is_active = TRUE
  AND NOT EXISTS (
    SELECT 1 FROM `PROJECT_ID.finance_analytics.client_user_role` r
    WHERE r.email = LOWER(u.email) AND r.client_id = m.client_id AND r.is_current = TRUE
  );
