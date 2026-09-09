# Production runbook

## Deploy

```bash
gcloud config set project aidirac-503309
gcloud builds submit --config cloudbuild.yaml --substitutions=_REGION=asia-south1
gcloud run deploy bills-voucher --image asia-south1-docker.pkg.dev/aidirac-503309/finance/bills-voucher:COMMIT_SHA --region asia-south1 --service-account bills-voucher-app@aidirac-503309.iam.gserviceaccount.com --memory 1Gi --cpu 1
```

Review `terraform plan` and apply `migrations/001_production_hardening.sql` in a controlled change window. Never place credentials in `.env` committed to Git.

## Roll back

```bash
gcloud run services update-traffic bills-voucher --region=asia-south1 --to-revisions=REVISION_NAME=100
```

## Health and common failures

- Liveness: `GET /health`.
- BigQuery permission failures: verify the Cloud Run service account has BigQuery Job User and Data Editor roles.
- GCS failures: verify the bucket name, region, and Storage Object Creator/Viewer access.
- Gemini failures: check Vertex AI access, model availability, upload size, and the document scan-status endpoint.
- Streaming-buffer errors: wait for BigQuery rows to leave the streaming buffer; retry the operation rather than issuing destructive cleanup.
- Failed scans: inspect `processing_error`, then resubmit the scan after correcting the underlying GCS or Vertex AI issue.

## Recovery

Use BigQuery time travel or table snapshots for approved recovery procedures. Document the incident and preserve audit rows. Permanent GCS deletion requires a separate retention approval.
