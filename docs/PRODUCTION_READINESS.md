# Production readiness

## Current status

The application is a BigQuery-only FastAPI/Next.js finance workspace with private GCS evidence storage, Gemini extraction, embeddings, and client-scoped workflows. The current local test suite passes (`25 passed`, 86% coverage). This repository is not yet approved for unattended production deployment.

## Implemented

- GST validation module at `app/services/gst/validation.py`.
- GSTIN checksum and structure validation.
- Intra-state/inter-state CGST, SGST, and IGST checks.
- Configured GST rate-slab warnings and a configurable per-field extraction-confidence threshold.
- HSN/SAC format checks and invoice-number normalization.
- Duplicate and e-invoice-gap validation flags.
- Structured validation report persisted with extraction rows after the schema migration is applied.
- Current document status statistics and per-file deletion progress.
- Deletion cleanup for extraction, line items, embeddings, and document metadata.
- Client-scoped document access and viewer write protection.
- Scan requests return `202` and expose a scan-status endpoint; Cloud Tasks is required in production and the local background fallback is development-only. Failures use `scan_failed`.
- Versioned `/api/v1` health, document-list, and client-scoped semantic-search endpoints are available; VECTOR_SEARCH is configured to use the IVF index when present.
- Approved-document GST register exports are available at `/api/reports/gstr` and `/reports/gstr.csv`.
- Review clients can request a five-minute signed GCS URL without exposing bucket paths.
- Human review edits are append-only correction rows merged at read time; original Gemini extraction rows remain unchanged. Corrections re-run GST validation, and approval is blocked unless `validation_status=passed`. JSON review queue, detail, correction, approval, rejection, and signed-evidence endpoints are available.
- Session max-age/idle expiry, BigQuery-backed session-version invalidation on password change, security headers, same-origin browser-write checks, and bounded login throttling are enabled.
- BigQuery queries enforce configurable maximum bytes billed and timeouts.
- Cloud Build worker sizing and smaller Docker contexts via `.dockerignore`.
- Cloud Tasks callbacks verify the Google-signed OIDC token and configured service account; forged queue headers are rejected.
- Local verification: Ruff, mypy, 25 pytest tests, and the configured 70% coverage gate pass (86% measured coverage).
- Stephenraj login identity is configurable as `BOOTSTRAP_ADMIN_EMAIL`; no password is committed.

## Deliberate deviations

- Scanning uses Cloud Tasks when configured, with a local background fallback for development; production must configure authenticated Cloud Run ingress and the queue service account.
- The migration is a reviewed SQL artifact and is not applied automatically.
- GCS deletion remains metadata-controlled; permanent object deletion should be a separate retention-approved operation.
- Token-based CSRF protection, same-origin checks, and login throttling are enabled for browser writes; API clients must send `X-CSRF-Token`.
- Cloud Run Terraform resources are now represented, but the secret version and ingress/IAM policy still require an environment-specific review.

## Latest artifact verification (2026-09-11)

- Cloud Build `2af574dc-13d5-441f-a1e1-27096e6d12e9` succeeded for commit `cc94731` in project `aidirac-503309`.
- Backend image: `asia-south1-docker.pkg.dev/aidirac-503309/finance/bills-voucher@sha256:c334b07046709166c6943ef37d3d057d1ac99aecd6057d5d3104f15dcf6a7261`.
- Frontend image was published with the same commit tag. The Cloud Run service was not changed by this build.

## Live GCP verification (2026-09-10)

- Project `aidirac-503309` contains the `finance_analytics` dataset, all core finance tables, and the partitioned/clustered `document_corrections` table.
- Bucket `gs://aidirac-503309-bills-voucher-documents` has uniform bucket-level access and public-access prevention enabled.
- Cloud Tasks API is enabled and queue `asia-south1/scan` is RUNNING with five attempts and a one-hour retry window.
- The deployed `bills-voucher-00043-mf7` revision is not the new image: it still has 512Mi memory, `GEMINI_MODEL=gemini-2.5-flash`, and no Cloud Tasks callback environment variables. It must be updated in an approved deployment window.
- The scan worker requires Storage Object Viewer to read private documents; Terraform scopes this permission to the document bucket, while the currently deployed service account has a broader project-level grant that should be narrowed during deployment.
- Live `documents`, `document_extractions`, `audit_logs`, `document_embeddings`, and journal tables are currently unpartitioned/unclustered; live embeddings also require the pending `client_id` schema migration for client-scoped vector search; Terraform now declares future partitioning/clustering, but a reviewed table migration is still required before high-volume production use.
- Live `/healthz` is not yet available because the old revision is active; `/api/v1/health` currently responds successfully.

## Go-live blockers, ranked

1. Deploy a new Cloud Run revision with the queue URL, queue service account, production Gemini model, and 1Gi backend memory; the live revision remains old.
2. Configure Cloud Run service accounts, Secret Manager values, ingress, and IAM using least privilege; review the extra live Storage Object Viewer grant.
3. Build and verify the BigQuery vector index and run a Terraform plan review; do not apply from this workspace.
4. Configure production HTTPS, CSRF token propagation for API clients, session expiry/invalidation, login throttling, and security headers.
5. Configure Cloud Monitoring alerts for scan failures, review queue depth, latency, and BigQuery cost.
6. Load-test upload, scan, review, delete, and vector-search flows with representative documents.

## Verification commands

```bash
.venv/bin/pytest -q
.venv/bin/python -m compileall -q app
docker build -t bills-voucher:local .
docker build -t bills-voucher-web:local frontend
```

Never commit `.env`, credentials, or the one-time Google authorization code pasted during setup.
