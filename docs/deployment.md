# Production deployment

## Google Cloud setup

1. Create a GCP project and enable Cloud Run, Artifact Registry, Cloud SQL, Storage, BigQuery, Document AI, Eventarc, Secret Manager, and Cloud Logging APIs.
2. Create a private Cloud SQL PostgreSQL instance and store its SQLAlchemy URL in Secret Manager.
3. Copy `infra/terraform.tfvars.example`, complete it, then run `terraform init` and `terraform apply` from `infra`.
4. Create secrets for `APP_SECRET_KEY`, `DATABASE_URL`, Razorpay API/webhook secrets, and configure them as Cloud Run secret environment variables. Never add them to source control.
5. Build with `gcloud builds submit --config cloudbuild.yaml --substitutions=_REGION=asia-south1` and deploy the resulting Artifact Registry image to Cloud Run with service account `bills-voucher-app`.

## IAM

The Terraform service account receives only Storage Object Creator, BigQuery Data Editor, Document AI API User, and Secret Manager Secret Accessor. The document bucket has uniform bucket-level access and public-access prevention enforced.

## Razorpay

Set the Razorpay webhook URL to `https://SERVICE_URL/webhooks/razorpay`, configure `RAZORPAY_WEBHOOK_SECRET` from a Secret Manager secret, and subscribe to payment/refund events. The application rejects unverified events.

## Eventarc / Document AI

Configure an Eventarc trigger for Cloud Storage object-finalize events under `finance-documents/`, targeting a separate document worker service. The worker should call the configured Invoice/Expense/OCR processor and POST results through the internal processing API. This keeps camera upload latency low.
