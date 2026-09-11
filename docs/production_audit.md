# Production audit

## Completed in this hardening pass

- BigQuery remains the only operational and analytical database.
- GCS documents remain private and are accessed through the application.
- GST validation is pure and unit tested for GSTIN checksum, state tax split, rate slabs, HSN/SAC format, duplicate flags, invoice totals, and e-invoice gaps.
- Document review supports client scoping, viewer protection, audit events, append-only corrections, GST revalidation before approval, and per-file deletion progress.
- Docker build contexts are reduced and Python dependencies are cached separately from application code.
- Cloud Build workers are explicitly configured for `E2_HIGHCPU_8`.
- Login no longer creates a hardcoded bootstrap password; BigQuery session-version invalidation now revokes older sessions after password changes. The configured development bootstrap password must be supplied through Secret Manager/environment configuration.

## Gaps requiring deployment action

- Apply `migrations/001_production_hardening.sql` after reviewing the existing BigQuery schemas.
- Configure a Cloud Run service account and grant only the documented GCS, BigQuery, and Vertex AI roles.
- Cloud Tasks API and the `scan` queue are now present in `aidirac-503309`; the deployed service still needs its queue URL/service-account environment variables and a new revision.
- CSRF tokens, bounded login throttling, idle session expiry, request IDs, and structured request logging are implemented; verify production HTTPS and alert routing during deployment.
- Maximum-bytes-billed, request labels, and query timeouts are implemented; verify partition/clustering and budget thresholds in the target dataset.
- CI includes Ruff, mypy, pytest coverage, Docker builds, Trivy, pip-audit, and Gitleaks secret scanning.
- Do not run Terraform apply from an unreviewed workstation. Review plan output first.
