-- Additive. Substitute PROJECT_ID and DATASET with the approved V3 target only.
-- Review before execution. No changes to V2. Application never runs DDL on requests.
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET.assistant_history` (
  turn_id STRING NOT NULL,
  user_id STRING NOT NULL,
  client_id STRING NOT NULL,
  period STRING NOT NULL,
  conversation_id STRING NOT NULL,
  question STRING NOT NULL,
  response_json STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY user_id, client_id, period, conversation_id
OPTIONS (partition_expiration_days=90, description='Private user/business assistant turns; 90-day retention');
