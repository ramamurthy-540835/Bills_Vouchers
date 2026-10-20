# Load test status

Local normalization tests executed with 10, 1,000 and 10,000 records for each
synthetic source. CPU timing is recorded in PERFORMANCE_BASELINE.md.

100,000-row imports are intentionally rejected by the current 10,000-row
contract. No cloud stress/soak test or concurrent 100,000-row acceptance has run.
RPS, remote p95/p99, CPU/memory, queue lag, OCR duration, BQ/AI/GCS cost and
error-rate targets are NOT_VERIFIED. Functional unit tests are not load tests.
