# Performance work and remaining measurements

Invoice extraction already uses the durable Cloud Tasks path. Keep acknowledgement
separate from OCR completion and preserve durable status/retry. Source intake has
explicit file/row/expanded-workbook bounds; connector responses are bounded and
timeouts/redirect policy are explicit.

V3 starts with capped instances and queue concurrency to bound preview cost.
Do not raise minimum instances, queue dispatch or load-test scale without
measuring the cost/latency tradeoff. BigQuery serialization and transaction
round trips remain a likely latency constraint, not a measured root cause yet.

Planned measurements: cold/warm health and authenticated reads, upload
acknowledgement excluding transfer, extraction duration, queue lag, BQ billed
bytes, per-query latency, dashboard freshness and error rate under concurrency.
No OLTP replacement is included in this change.
