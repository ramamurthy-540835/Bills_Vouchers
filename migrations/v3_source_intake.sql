-- Apply only after substituting reviewed PROJECT and V3_OPS placeholders.
-- Never run this against V2 or production datasets.
CREATE TABLE IF NOT EXISTS `PROJECT.V3_OPS.bulk_import_batches` (
 client_id STRING NOT NULL, batch_id STRING NOT NULL, actor_id STRING NOT NULL,
 payload JSON, created_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY client_id,batch_id;
CREATE TABLE IF NOT EXISTS `PROJECT.V3_OPS.integration_source_records` (
 client_id STRING NOT NULL, batch_id STRING NOT NULL, source_system STRING,
 source_record_id STRING, source_version INT64, source_hash STRING, payload JSON,
 status STRING, created_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY client_id,source_system,source_record_id;
