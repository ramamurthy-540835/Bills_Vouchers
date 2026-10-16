# GST Easy V2 deployment report

Deployed new services gst-easy-v2-api and gst-easy-v2-web in project aidirac-503309, region asia-south1.

- Frontend: https://gst-easy-v2-web-foovqasysa-el.a.run.app
- Private backend: https://gst-easy-v2-api-foovqasysa-el.a.run.app
- Built and pushed application commit: eaaabd8b7a21cff1d7d15e41fe9a1fe3cceb505e (GST-EASY-V2).
- API Cloud Build: e9b2b858-e456-4301-8dcf-a7cc379f948a, SUCCESS.
- Web Cloud Build: edca2598-afc2-4395-a337-5bb980dffdee, SUCCESS.
- API digest: sha256:3e79de12e5f4ec2b35c11be78dc2f19f202b5f6ab028932429268e2a27a9253a.
- Web digest: sha256:fca64ce5c7dc7bce80c7e76b2376700bc3ebf35d49183b21266d9827352d81d0.
- Configurations: cloudbuild-gst-easy-v2-api.yaml and cloudbuild-gst-easy-v2-web.yaml.
- Verified runtime revisions: gst-easy-v2-api-00003-649 and gst-easy-v2-web-00002-9sc.

The initial environment delimiter was consumed by Windows command processing. The new V2 services were corrected with structured JSON environment files. Both actual configurations were then verified, including the V2-only data paths and frontend/API audience. No application image change was required. Release-tooling/documentation commits after the image commit are not claimed as image sources.

Prepared resources: gst_easy_v2_finance_analytics, gst_easy_v2_gold, gst_easy_v2_silver, gst_easy_v2_ops; private aidirac-503309-gst-easy-v2-documents and aidirac-503309-gst-easy-v2-builds buckets; gst-easy-v2-bills queue (one concurrent dispatch); gst-easy-v2-api/web/build service accounts; gst-easy-v2 Artifact Registry; gst-easy-v2-session and gst-easy-v2-demo-password secrets (version 1).

Public access policy: only the new frontend login page is public; API requires Cloud Run IAM. Frontend gets run.invoker on the V2 API only and no data roles. Worker calls retain signed OIDC checks. API gets V2 data access, job submission and Vertex AI usage. Upload requires application session/membership; max two service instances, queue concurrency one. Public registration/recovery delivery is unavailable until a mail provider is configured.

Server authentication follows https://docs.cloud.google.com/run/docs/authenticating/service-to-service using metadata ID tokens in X-Serverless-Authorization, separate from app session cookies. No service-account key files.

Existing 29 Cloud Run services/configuration/traffic and IAM were captured before mutations. Deployment script compares the complete baseline and stops if any old service differs. No old service is a deployment target. No existing cloudbuild YAML changed.

Rollback: stop new V2 traffic by restricting only its new frontend, or roll back only V2 to a reviewed V2 digest. Do not modify old services. Retain demo evidence/audit. No destructive resource cleanup is automated.

Status: both services deployed by immutable digest. Login URL returns HTTP 200; direct unauthenticated backend access returns 403. Complete comparison of all 29 prior service objects and IAM policies passed after deployment. Operator-approved password stored in V2 Secret Manager version 1 through hidden input, never committed or logged. One client-role account and exactly three synthetic business profiles/logos provisioned. Verified canonical invoice and GSTR-2B tables contain zero rows. No existing financial data copied.
