-- Append-only review evidence; decisions never replace source invoices or ITC rules.
CREATE TABLE IF NOT EXISTS `aidirac-503309.ops.gst_reconciliation_review` (
  client_id STRING NOT NULL,
  period STRING NOT NULL,
  case_id STRING NOT NULL,
  version INT64 NOT NULL,
  source_hash STRING NOT NULL,
  decision STRING NOT NULL,
  reason STRING NOT NULL,
  actor_id STRING NOT NULL,
  evidence JSON,
  created_at TIMESTAMP NOT NULL
)
CLUSTER BY client_id, period, case_id;
