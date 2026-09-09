# Production audit

## Completed in this hardening pass

- BigQuery remains the only operational and analytical database.
- GCS documents remain private and are accessed through the application.
- GST validation is pure and unit tested for GSTIN checksum, state tax split, rate slabs, HSN/SAC format, duplicate flags, invoice totals, and e-invoice gaps.
- Document review supports client scoping, viewer protection, audit events, and per-file deletion progress.
- Docker build contexts are reduced and Python dependencies are cached separately from application code.
- Cloud Build workers are explicitly configured for `E2_HIGHCPU_8`.
- Login no longer creates a hardcoded bootstrap password. The configured development bootstrap password must be supplied through Secret Manager/environment configuration.

## Gaps requiring deployment action

- Apply `migrations/001_production_hardening.sql` after reviewing the existing BigQuery schemas.
- Configure a Cloud Run service account and grant only the documented GCS, BigQuery, and Vertex AI roles.
- Cloud Tasks is still required for durable asynchronous scans; the current implementation uses FastAPI `BackgroundTasks` as a local/dev fallback and exposes scan-status polling.
- Add CSRF tokens, rate limiting, idle session expiry, and structured request logging before exposing browser routes publicly.
- Add maximum-bytes-billed to the BigQuery repository and partition/clustering verification for large tables.
- CI now includes Ruff substantive checks, mypy, pytest coverage, Docker builds, Trivy, pip-audit, and private-key detection; full style cleanup remains separate.
- Do not run Terraform apply from an unreviewed workstation. Review plan output first.
