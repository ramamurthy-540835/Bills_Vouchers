# Nature Labs 1 V2 demonstration

Account: `naturelabs1@demo.com` (client role, one owner membership; no platform administration).

Live V2 URL: https://gst-easy-v2-web-foovqasysa-el.a.run.app

Business: **Nature Labs Synthetic Manufacturing Pvt Ltd**, trade **Nature Labs Industrial Manufacturing**. Chennai, Tamil Nadu, 600032. Website https://naturelabs-manufacturing.example.test. Complete stored profile and private logo; `is_test=true`, `gstin_verified=false`, profile source `SYNTHETIC_TEST_ONLY`.

Credentials: supplied password was received through hidden terminal input, stored in V2-only Secret Manager secret `gst-easy-v2-naturelabs1-password`, version 1, and hashed by the existing registration service. It is not included in this report or repository.

## Persisted documents

23 distinct invoice identities, each supplied as PDF, PNG and JPEG in `demo bills/naturelabs1/` (69 files). Exactly one representation per invoice was uploaded through `/api/gst/bills/upload`. Existing Cloud Tasks, Vertex AI extraction, private originals, review PATCH, confirmation and rejection routes were used. Authorized demo review corrected fields against generated originals; extraction provenance was retained. Twenty invoices confirmed (10 purchases and 10 sales including one credit note each), two left for review with an intentionally missing editable date, and one rejected with a recorded reason.

Original evidence and pending examples are preserved. No dashboard values were inserted. The earlier `naturelabs@demo.com` account was not populated or modified by this script.

Actual recorded extraction methods: `{"gemini": 23}`.

## Independent expected values versus live results

| KPI | Expected | Actual |
|---|---:|---:|
| eligible_credit | 5781.60 | 5781.60 |
| output_tax | 23960.16 | 23960.16 |
| cash_required | 18178.56 | 18178.56 |
| non_gst | 11038.00 | 11038.00 |
| confirmed_sales | 190918.16 | 190918.16 |
| confirmed_purchases | 93874.72 | 93874.72 |
| pending_reviews | 2 | 2 |
| reconciliation_mismatches | 3 | 3 |
| unmatched_invoices | 3 | 3 |


Expectations were calculated independently using Decimal in `generate_naturelabs1_demo.py`, then tested against the existing calculation engine and actual persisted live invoices. See `EXPECTED_RESULTS.xlsx` and `TEST_MANIFEST.json`.

## Deployment

Branch `GST-EASY-V2`; API source `fc3f26d96a2eb2fdb4f058bede96df1031c7728c`; Cloud Build `12994bf7-0556-4823-b133-da8972bd67d2`. API revision `gst-easy-v2-api-00013-jis`; immutable image `asia-south1-docker.pkg.dev/aidirac-503309/gst-easy-v2/api@sha256:cfd1d6236e5782e1214468bfc27fafb422ce568665de1ecb1593215a466dd9c1`. Existing V2 frontend retained. Original production/preview services and IAM compared against preserved baselines.

## Limitations

- Synthetic test rates and HSN assignments are assumptions, not certified tax advice. GSTIN-like identifiers are fictional fixtures, not government-verified registrations or proof of ownership.
- B2B-only statement parser: the purchase credit note is an unsupported reconciliation case, not a matched portal credit note. A duplicate-candidate statement is rejected, never persisted as a fake match.
- Existing synthetic-tenant restrictions block real return preparation, approvals, filing and financial exports. Read-only reports and calculations work; these restrictions were not bypassed.
- Email and mobile verification remain false. This explicit V2 operator-activated identity is not ownership/KYC verification.
- Local browser tests use designated synthetic fixtures; live evidence is recorded separately. Password changes, account deletion and production filing were not performed during live acceptance.
- AI is read-only and model-generated; cited evidence remains the authority. Search is bounded to the latest 500 canonical records per business/period.

## Rollback

For application rollback, route **only gst-easy-v2-api** to the prior revision recorded in `artifacts/gst_easy_v2/naturelabs1-r5-deployment.json`. Do not alter original production services. Synthetic data is retained with audit evidence; rollback does not delete invoice originals or unrelated tenants. Account access can be revoked through the existing authorized membership/identity management process.
