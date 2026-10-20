-- Additive V3-only audit snapshots. Never changes invoice or return totals.
CREATE TABLE IF NOT EXISTS `PROJECT.V3_OPS.external_transaction_links` (
 client_id STRING NOT NULL, batch_id STRING NOT NULL, period STRING NOT NULL,
 run_id STRING NOT NULL, actor_id STRING NOT NULL, payload JSON,
 created_at TIMESTAMP NOT NULL
) PARTITION BY DATE(created_at) CLUSTER BY client_id,period,batch_id;
