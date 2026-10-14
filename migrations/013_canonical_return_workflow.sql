-- Additive canonical return preparation. No portal submission or payment.
CREATE TABLE IF NOT EXISTS `aidirac-503309.ops.gst_return_current` (
 client_id STRING NOT NULL, period STRING NOT NULL, state STRING NOT NULL,
 version INT64 NOT NULL, snapshot_id STRING, source_hash STRING,
 maker_id STRING, reviewer_id STRING, updated_at TIMESTAMP NOT NULL
) CLUSTER BY client_id, period;
CREATE TABLE IF NOT EXISTS `aidirac-503309.ops.gst_return_snapshot` (
 client_id STRING NOT NULL, period STRING NOT NULL, snapshot_id STRING NOT NULL,
 source_hash STRING NOT NULL, payload JSON NOT NULL, maker_id STRING NOT NULL,
 created_at TIMESTAMP NOT NULL
) PARTITION BY DATE(created_at) CLUSTER BY client_id, period;
CREATE TABLE IF NOT EXISTS `aidirac-503309.ops.gst_return_audit` (
 client_id STRING NOT NULL, period STRING NOT NULL, snapshot_id STRING,
 actor_id STRING NOT NULL, action STRING NOT NULL, reason STRING NOT NULL,
 previous_state STRING, next_state STRING NOT NULL, created_at TIMESTAMP NOT NULL
) PARTITION BY DATE(created_at) CLUSTER BY client_id, period;
