-- LOCAL PREPARATION ONLY. Substitute reviewed PROJECT and V3_FINANCE placeholders.
-- Apply to the isolated V3 dataset before releasing the bounded repair worker.
-- Do not run against V2/production or delete repair history to reset budgets.
CREATE TABLE IF NOT EXISTS `PROJECT.V3_FINANCE.auth_mail_repairs` (
  mail_id STRING NOT NULL,
  attempt INT64 NOT NULL,
  state STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  queued_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY mail_id,state;
