# Production deployment

## Google Cloud setup

1. Create a GCP project and enable Cloud Run, Artifact Registry, BigQuery, Cloud Storage, Vertex AI, Secret Manager and Cloud Logging APIs.
2. Copy `infra/terraform.tfvars.example`, complete it, then run `terraform init` and `terraform apply` from `infra`.
3. Replace `PROJECT_ID` in `infra/vector_search.sql` and run it in BigQuery to create the IVF vector index.
4. Configure `GCP_PROJECT_ID`, `GCP_REGION=global`, `GCS_BUCKET_NAME`, `BIGQUERY_DATASET=finance_analytics`, `GEMINI_MODEL=gemini-3.8-flash`, and `EMBEDDING_MODEL=gemini-embedding-001` as Cloud Run environment variables.
5. Store only `APP_SECRET_KEY` and any optional `GEMINI_API_KEY` in Secret Manager. Cloud Run should use the Terraform service account with Application Default Credentials.
6. Build with `gcloud builds submit --config cloudbuild.yaml --substitutions=_REGION=asia-south1` and deploy the image to Cloud Run with service account `bills-voucher-app`.

## IAM and controls

The app service account receives Storage Object Creator, BigQuery Data Editor, BigQuery Job User and Vertex AI User. The document bucket enforces uniform bucket-level access and public-access prevention. The MCP server exposes only bounded read operations; it has no write tools.

## Runtime flow

The API writes document metadata to BigQuery and originals to GCS. `POST /documents/{document_id}/scan` sends the document to Gemini, persists structured GST fields, creates a `gemini-embedding-001` vector, and indexes it in BigQuery. `GET /documents/search?q=...` uses `VECTOR_SEARCH`; brute force remains available until the IVF index is built.
