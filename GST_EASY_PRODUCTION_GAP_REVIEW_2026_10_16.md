# Production gap review — 16 October 2026

Release decision: suitable for continued isolated preview evaluation, not certified for production financial use. Passing automated tests is not accountant or customer acceptance. The requested 80% readiness is not independently established.

## Changes and evidence

Business profile and onboarding now accept a validated public company website. The account response separates GSTIN format/checksum validation from government registration verification and website ownership. Users can open the official GST search portal; this does not mark a company verified. Backend validation rejects unsafe URL schemes, credentials and local/IP-style hosts without fetching supplied URLs.

The canonical profile writer retains versioned updates and audit history. A legacy profile writer could bypass this transaction and accept a supplied verification flag; it is now blocked in canonical GST Easy mode, and legacy profile preparation cannot set verification true from client input.

Changed source: app/services/gst/{account,profiles,routes}.py; frontend/app/settings/{account-form,onboarding-form,company-checks}.tsx. Regression evidence: tests/test_company_profile.py, tests/frontend/copy.spec.ts and tests/gst/browser_backend.py. Integration/migration helpers: scripts/check_company_profile_integration.py and scripts/apply_company_website.py.

Validation: 332 backend tests passed; Ruff passed; mypy passed across 74 files; frontend production build passed; all 17 local browser scenarios passed. Actual BigQuery integration verified a website update, one current version, preserved previous version, audit, stale conflict, cross-client denial and ignored forged verification flag. It used an isolated synthetic dataset with 24-hour table expiry, not customer records or authenticated preview UAT.

Migration 016 added nullable STRING website_url to finance_analytics.gst_client_profile. Applied job df99cdd6-1249-48e3-a0f2-2a0f01f7f51a at 2026-10-16T02:00:38Z; SHA256 3bc6dd710cad3d5a6eff67d3ef713b1ea344f6aec4453fd6751828008afc4d86. Existing customer rows were not updated. Local artifacts/gst_easy contains migration and synthetic integration evidence.

## Company verification provider

ClearTax is a candidate for review, not a configured or purchased service. Its documented taxpayer-information API returns legal name, registration status and address; it requires provider onboarding, an authentication token and taxable entity ID. Verify contract, permitted use, retention, support and response provenance before integration. Store credentials in Secret Manager. Record provider, lookup timestamp and evidence; invalidate verification when GSTIN changes. A response must not silently authorize tenant membership or substitute for customer consent.

Sources: [GSTN empanelled GSP list](https://www.gstn.org.in/empanelled-gsps), [ClearTax taxpayer API](https://docs.cleartax.in/cleartax-docs/gst-api-1/gst-api-reference/taxpayer-information), [official GST search](https://services.gst.gov.in/services/searchtp). No live taxpayer was verified in this work. Company legal name, genuine GSTIN and website remain to be supplied/confirmed for provisioning.

## Customer storage and GCP

Existing bucket: gs://aidirac-503309-bills-voucher-documents, ASIA-SOUTH1. Read-only cloud audit confirmed public access prevention enforced, uniform bucket-level access enabled and seven-day soft deletion. Customer objects use client-scoped paths and backend membership authorization. These controls do not establish production disaster recovery, retention approval or a tested RPO/RTO.

No new customer bucket or customer IAM principal was created. A business profile belongs in the application's tenant-scoped database. Separate buckets per customer require an explicit storage choice plus tenant-to-bucket mapping across invoice, logo and background-job paths; creating an unused bucket alone would not deliver this functionality. Existing private storage is the default recommended starting point. No genuine company profile was invented or marked verified.

## Ordered production blockers

| Priority | Gap | Required acceptance |
|---|---|---|
| Critical | ITC opening/utilization/reversal/reclaim/carry-forward ledger and line-level eligibility remain incomplete | Implement evidence-backed movements and obtain independent accountant examples and approval |
| Critical | Official GSTR-1/GSTR-3B export adapters and validators incomplete | Verify current official schemas, deterministic output and accountant acceptance; no real filing |
| High | Government GST registration verification not connected | Select/onboard provider, securely configure credentials and test genuine authorized evidence and failures |
| High | Shared API identity has excessive permissions | Dedicated API identity, reviewed resource-scoped grants and tested queue/storage/AI/secret access before switching |
| High | Real email delivery and SMS verification unaccepted | Verify delivery/recovery across mailbox providers; select SMS provider and test expiry/replay and actual confirmation |
| High | Broader GSTR-2B sections, amendments and notes incomplete | Verified specifications, genuine fixtures and reconciled accountant expectations |
| High | Production recovery, retention and operational acceptance incomplete | Scheduled backup coverage, restore exercise, agreed RPO/RTO, alert delivery and incident runbooks |
| High | Live queue/AI failure recovery and realistic load not fully demonstrated | Inject failures around upload/enqueue/extraction/write; measure latency, cost and duplicate safety |
| High | Genuine client, accountant and security UAT incomplete | Authorized customer journeys, independent calculations, tenant/object permission review and signed acceptance |
| Medium | Complete action/accessibility/notification and assistant evidence pending | Audit remaining journeys and live scoped retrieval/prompt-injection behavior |

API identity audit: shared compute account retains aiplatform.user, artifactregistry.reader/writer, bigquery.dataEditor/dataViewer/jobUser, cloudbuild.builds.builder, cloudtasks.enqueuer, datastore.user, run.admin, secretmanager.secretAccessor and storage.objectAdmin. No project IAM grant was removed because other services may share this identity. Preview frontend already uses a separate identity with no direct project roles.

## Deployment and rollback

Target only the existing gst-easy Cloud Run preview tags. Preserve production traffic and other preview mappings. Build immutable images from the committed source; record successful build IDs, digests, revisions and smoke results separately after deployment.

Previous preview API revision: bills-voucher-00122-fof. Previous preview web revision: bills-voucher-web-00059-cij. Roll back only gst-easy tag mappings to these compatible revisions if necessary; do not change production percentages. Retain nullable website column, profile versions and audit evidence. Reverting the application also removes the new legacy-writer hardening, so assess that security consequence before rollback.

Customer-facing preview: https://gst-easy---bills-voucher-web-foovqasysa-el.a.run.app . Production promotion requires explicit owner approval after the blockers in the supported release scope are resolved.
