# Performance results
Pure deterministic validation, 1,000 local iterations: p50 0.0811 ms, p95 0.1453 ms, p99 0.1685 ms. This excludes network, storage, OCR, legal lookup and persistence. Evidence: intelligence-validation-benchmark.json.

Implemented: bounded duplicate lookup instead of loading all invoices for each decision; no idle intelligence polling; active-job polling and upload recovery backoff; dispatch files before waiting for OCR; bounded assistant input. Tenant authorization is retained.

Live before/after login improvement, p95 navigation, upload acknowledgement, queue lag, OCR throughput and cost under load are not yet verified. Do not claim microsecond end-to-end processing or achieved production SLOs.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.

Workspace SSR now loads independent financial and account snapshots in parallel, with the existing identity equality and permission checks retained. TypeScript, production build and 32 navigation/report/intelligence browser regressions passed. Candidate latency measurement pending.
