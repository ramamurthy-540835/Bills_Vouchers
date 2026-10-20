# Load test status

Local normalization tests executed with 10, 1,000 and 10,000 records for each
synthetic source. CPU timing is recorded in PERFORMANCE_BASELINE.md.

100,000-row imports are intentionally rejected by the current 10,000-row
contract. No cloud stress/soak test or concurrent 100,000-row acceptance has run.
RPS, remote p95/p99, CPU/memory, queue lag, OCR duration, BQ/AI/GCS cost and
error-rate targets are NOT_VERIFIED. Functional unit tests are not load tests.

Live connectivity sample after deployment: 20 sequential IAM-authenticated
requests to the private V3 /health endpoint all returned 200. Operator-to-service
round-trip timings (including network and first request): p50 43.79 ms,
p95 86.32 ms, p99 206.12 ms. Concurrency was one. This is not a stress test,
server-only benchmark, sustained SLO or before/after optimization comparison.

One real synthetic Gemini 3.8 Flash global connectivity request returned 200
with the expected response in 3.246 seconds. It used the operator identity,
not the runtime service account, and is not an OCR throughput benchmark.
