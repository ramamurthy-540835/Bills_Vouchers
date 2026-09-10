# Production readiness

## Current status

The application is a BigQuery-only FastAPI/Next.js finance workspace with private GCS evidence storage, Gemini extraction, embeddings, and client-scoped workflows. The current local test suite passes (`15 passed`). This repository is not yet approved for unattended production deployment.

## Implemented

- GST validation module at `app/services/gst/validation.py`.
- GSTIN checksum and structure validation.
- Intra-state/inter-state CGST, SGST, and IGST checks.
- Configured GST rate-slab warnings.
- HSN/SAC format checks and invoice-number normalization.
- Duplicate and e-invoice-gap validation flags.
- Structured validation report persisted with extraction rows after the schema migration is applied.
- Current document status statistics and per-file deletion progress.
- Deletion cleanup for extraction, line items, embeddings, and document metadata.
- Client-scoped document access and viewer write protection.
- Scan requests return `202` and expose a scan-status endpoint with a local background fallback; failures use `scan_failed`.
- Versioned `/api/v1` health, document-list, and semantic-search compatibility endpoints are available.
- Approved-document GST register exports are available at `/api/reports/gstr` and `/reports/gstr.csv`.
- Review clients can request a five-minute signed GCS URL without exposing bucket paths.
- Human review edits are append-only correction rows merged at read time; original Gemini extraction rows remain unchanged.
- Session max-age/idle expiry, security headers, same-origin browser-write checks, and bounded login throttling are enabled.
- BigQuery queries enforce configurable maximum bytes billed and timeouts.
- Cloud Build worker sizing and smaller Docker contexts.
- Stephenraj login identity is configurable as `BOOTSTRAP_ADMIN_EMAIL`; no password is committed.

## Deliberate deviations

- Scanning uses Cloud Tasks when configured, with a local background fallback for development; production must configure authenticated Cloud Run ingress and the queue service account.
- The migration is a reviewed SQL artifact and is not applied automatically.
- GCS deletion remains metadata-controlled; permanent object deletion should be a separate retention-approved operation.
- Token-based CSRF protection, same-origin checks, and login throttling are enabled for browser writes; API clients must send `X-CSRF-Token`.
- Cloud Run Terraform resources are now represented, but the secret version and ingress/IAM policy still require an environment-specific review.

## Go-live blockers, ranked

1. Apply and verify the BigQuery schema migration in a non-production dataset.
2. Configure Cloud Run service accounts, Secret Manager values, and IAM using least privilege.
3. Move scanning to Cloud Tasks with bounded retries, idempotency, and scan-status polling.
4. Configure production HTTPS, CSRF token propagation for API clients, session expiry/invalidation, login throttling, and security headers.
5. Add maximum-bytes-billed, query labels, structured logs, readiness checks, and alerts.
6. Add CI quality/security gates and run a Terraform plan review.
7. Load-test upload, scan, review, delete, and vector-search flows with representative documents.

## Verification commands

```bash
.venv/bin/pytest -q
.venv/bin/python -m compileall -q app
docker build -t bills-voucher:local .
docker build -t bills-voucher-web:local frontend
```

Never commit `.env`, credentials, or the one-time Google authorization code pasted during setup.
