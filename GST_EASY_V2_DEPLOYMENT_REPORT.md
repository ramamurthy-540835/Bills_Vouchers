# GST Easy V2 deployment report

New target services: gst-easy-v2-api and gst-easy-v2-web, project aidirac-503309, region asia-south1. Actual URLs/build IDs/commit will be recorded only after successful execution.

Prepared resources: gst_easy_v2_finance_analytics, gst_easy_v2_gold, gst_easy_v2_silver, gst_easy_v2_ops; private aidirac-503309-gst-easy-v2-documents and aidirac-503309-gst-easy-v2-builds buckets; gst-easy-v2-bills queue (one concurrent dispatch); gst-easy-v2-api/web/build service accounts; gst-easy-v2 Artifact Registry; gst-easy-v2-session and empty gst-easy-v2-demo-password secrets.

Public access policy: only the new frontend login page is public; API requires Cloud Run IAM. Frontend gets run.invoker on the V2 API only and no data roles. Worker calls retain signed OIDC checks. API gets V2 data access, job submission and Vertex AI usage. Upload requires application session/membership; max two service instances, queue concurrency one. Public registration/recovery delivery is unavailable until a mail provider is configured.

Server authentication follows https://docs.cloud.google.com/run/docs/authenticating/service-to-service using metadata ID tokens in X-Serverless-Authorization, separate from app session cookies. No service-account key files.

Existing 29 Cloud Run services/configuration/traffic and IAM were captured before mutations. Deployment script compares the complete baseline and stops if any old service differs. No old service is a deployment target. No existing cloudbuild YAML changed.

Rollback: stop new V2 traffic by restricting only its new frontend, or roll back only V2 to a reviewed V2 digest. Do not modify old services. Retain demo evidence/audit. No destructive resource cleanup is automated.

Status: resources prepared; builds/deployment and real live URL verification pending. Account activation pending user-provided password secret. No existing financial data copied.
