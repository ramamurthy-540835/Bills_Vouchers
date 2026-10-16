-- Review and apply separately. No customer updates, historical seeds or verified-flag backfill.
CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.gst_taxpayer_verification` (
 attempt_id STRING NOT NULL, client_id STRING NOT NULL, profile_hash STRING NOT NULL,
 actor_id STRING NOT NULL, provider STRING NOT NULL, terminal BOOL NOT NULL,
 created_at TIMESTAMP NOT NULL, result STRING NOT NULL
) PARTITION BY DATE(created_at) CLUSTER BY client_id
OPTIONS(require_partition_filter=TRUE);
CREATE TABLE IF NOT EXISTS `aidirac-503309.finance_analytics.gst_verification_guard` (
 id STRING NOT NULL, touched_at TIMESTAMP
);
MERGE `aidirac-503309.finance_analytics.gst_verification_guard` target
USING (SELECT 'lookup' AS id) source ON target.id=source.id
WHEN NOT MATCHED THEN INSERT (id,touched_at) VALUES ('lookup',CURRENT_TIMESTAMP());
