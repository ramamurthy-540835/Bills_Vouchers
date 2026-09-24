# v5 progress

Date: 2026-09-24. Local baseline: `6d85c59372d17cd5daa4805b152191f98133c181` (`main`).

## Phase 0 — FAIL: required bootstrap profile is missing

Read the supplied v5 prompt and inspected the local application and Google Cloud configuration. Cloud inspections were read-only. No secret values were printed, logged, or written to files.

Secret Manager `red-taxi-client-bootstrap:latest` parses as JSON with exactly these top-level keys: `email`, `password`, `client_name`, `role`. It has no `gstin` or nested client profile. The required Red Taxi GSTIN cannot be derived from those keys. The prompt requires bootstrapping the profile from this secret, deriving the state from GSTIN, and refusing a result that does not start with `33`. Inventing a GSTIN or using the Umesh fixture would violate those requirements.

**Blocker:** supply the verified Red Taxi GSTIN and profile in the bootstrap secret (including legal/trade names as applicable). Keep the existing login fields; do not send the password in conversation. Resume by rechecking the secret shape and validating the GSTIN without printing secret values.

Per the prompt's Mode instruction, stop when a hard constraint cannot be honoured and record the blocker here first. Implementation, migrations, and deployment have not begun.

### Discovery findings

- Local backend: FastAPI, Jinja templates, BigQuery repository, signed Starlette sessions. Frontend: Next.js with an API proxy to a separately deployed backend.
- Local identity chain: session `user_id` -> `users` -> `client_memberships` -> `clients`; selected `client_id` is in the session. The requested SCD-2 `client_user_role` identity chain is absent locally.
- Local `frontend/app/page.tsx` is a client component with the loading shell, duplicate upload controls, sidebar account block, and developer-facing metric text described in the prompt.
- `/gst/filing` and the Umesh fixture are absent in this checkout. The example GSTIN occurs only in `tests/test_gst_validation.py`. Therefore D1's fixture resolution cannot be located in this source; the deployed implementation differs from this checkout.
- Web image currently configured: `asia-south1-docker.pkg.dev/aidirac-503309/finance/bills-voucher-web:red-taxi-20260924`.
- Its backend is `https://api-preview---bills-voucher-foovqasysa-el.a.run.app`. The repository root Dockerfile builds FastAPI, whereas `frontend/Dockerfile` builds the web service. The prompt's root `--source .` web deployment command must be adapted to the actual architecture before deployment.
- Existing preview tag points to revision `bills-voucher-web-00026-dux`. Production traffic is 100% on `bills-voucher-web-00027-67p`, with latestRevision tracking enabled. No traffic changes were made.
- Existing preview URL (not a new v5 deployment): https://preview---bills-voucher-web-foovqasysa-el.a.run.app

### Cloud inventory

Datasets discovered in `aidirac-503309`: `arista_events`, `careeredge_jobs`, `finance_analytics`, `finance_analytics_staging`, `grocery_analytics`, `income_tax_ops`, `inventory_management`, `movies`, `prism`, `school_lunch`, `taxright_staging`, `tendermatch`. Both finance datasets are in `asia-south1`.

`finance_analytics` tables/views: `account_balances`, `accounts`, `audit_logs`, `biglake_powerbi_demo`, `client_gst_profiles`, `client_memberships`, `client_preferences`, `client_user_role`, `clients`, `document_corrections`, `document_embeddings`, `document_extractions`, `document_line_items`, `document_storage_manifest`, `documents`, `gst_audit_log`, `gst_blocked_credit_master`, `gst_client_profile`, `gst_itc_runs`, `gst_purchase_invoices`, `gst_reconciliation_matches`, `gst_returns`, `gst_state_master`, `gst_tasks`, `gst_validation_issues`, `gstr2b_invoices`, `gstr_return_json`, `itc_reversal_detail`, `journal_entries`, `journal_lines`, `pipeline_events`, `powerbi_finance_dashboard`, `storage_migrations`, `users`.

`finance_analytics_staging`: `gst_audit_log`, `gst_blocked_credit_master`, `gst_client_profile`, `gst_itc_runs`, `gst_state_master`, `gstr_return_json`, `itc_reversal_detail`.

No requested `bronze_*`, `silver_*`, or `gold_*` tables exist in either finance dataset. Proposed additive mapping: documents/storage manifest -> bronze; extractions/line items/GSTR-2B rows -> silver; ITC runs/reversal detail/return artefacts -> gold. Schema compatibility and bucket inventory remain unverified; no data was migrated.

### Project-reference audit

Before creating this report, a repository-wide search including hidden files (excluding `.git`) found zero occurrences of either forbidden legacy project reference from the prompt. Replacements: **0**. Cloud output identifies the numeric project number from the prompt as the number used by `aidirac-503309` itself; do not blindly substitute runtime service-account identities with a textual project ID.

## Phase 1 — FAIL / BLOCKED

Required GSTIN is missing from the bootstrap source. No profile or role mutation performed.

## Phases 2–5 — NOT RUN

Stopped at the explicit hard-constraint blocker. No application implementation claims.

## Phase 6 — NOT RUN

Tests executed: 0. Cross-client, pipeline, Decimal, UI, filing-state, sample-data, and deployment gates remain unverified.

## Phase 7 — NOT RUN

No build, deployment, traffic update, commit, or push. Existing preview URL above must not be represented as a completed v5 deployment.

---

## Resumed execution — user-authorised GSTIN deferral

The user subsequently instructed: “the redtaxi gstin will be added later so work on the other parts”. This supersedes the initial stop above. The entries below are the current execution record; the initial discovery remains as history.

### Phase 0 — PASS

Recovered the more complete preview source from Cloud Build `f70ce346-7cda-4642-8b8c-c6b2ca829795`, locally, without pushing or committing it. The later production source was older in functionality. Located the literal fixture identity in the recovered Overview and filing components. Generated `docs/v5-route-audit.md` covering 101 backend registrations and the frontend routes. The route inventory distinguishes static inspection from runtime test coverage.

### Phase 1 — PASS with explicit GSTIN deferral

Bootstrap now versions the Red Taxi principal as `client`, sources profile identity from `gst_client_profile`, rejects a supplied invalid/non-Tamil-Nadu GSTIN, and permits an incomplete registration while it is deferred. No GSTIN was invented. Existing verified registration can be preserved; mismatched fixture registration is not reused. Real-cloud bootstrap was executed twice and passed idempotency/profile/current-role checks. Existing account passwords are preserved.

The bootstrap secret password does **not** match the current account password. Account is active and does not require a password change. Password login using the stale bootstrap secret returned 401; this is not reported as a successful login test. Read-only authenticated integration checks use an owner-authorised temporary signed session held in process memory. No credentials, secret values or cookies were printed or persisted.

### Phase 2 — PASS for implemented pipeline

Applied `007_v5_medallion.sql` additively to finance and staging datasets. The initial per-column ALTER sequence hit a BigQuery update-rate limit; batching additions in one ALTER succeeded. All specified bronze/silver/gold tables and filing audit/status tables exist, plus outward invoice rows for output liability. The existing bucket has uniform access and enforced public-access prevention in ASIA-SOUTH1.

Created `bv-doc-landed` and authenticated push subscription `bv-doc-landed-preview`, targeting the isolated `v5-api` tag with dedicated identity `bv-pipeline-preview@aidirac-503309.iam.gserviceaccount.com`. Only required topic publishing / identity-token / application-secret access was granted.

Real staging checks passed: two inaccessible synthetic tenants with overlapping invoice numbers, GCS bronze objects, silver headers/lines, gold entries, duplicate upload reuse, idempotent recompute, transaction audit and locked-period isolation. An actual valid PDF was extracted using the configured Gemini 2.5 Flash path; it reached needs-review, was reviewed against the known test PDF, and reached gold. Test artefacts are under isolated staging tenant IDs with no memberships. The optional Document AI processor is not configured; the tested worker is the existing Gemini path.

### Phase 3 — PASS for current-period rule evaluation

Decimal arithmetic, passenger-transport vehicle/insurance exceptions, fuel exclusion, 2B deferral, section 16(4), R37, current-period common-credit R42/R43 and head-wise set-off are implemented. ECO 9(5) cash liability remains separate. Missing turnover attribution defers common credit and blocks validation. Automatic multi-year capital-asset scheduling is not part of this preview; the period's relevant capital inputs must be maintained by a reviewer.

The real OCR test exposed percent/currency text. Added normalization with an explicit review error for ambiguous monetary strings, plus a regression test. Import JSON numeric tokens are decoded as Decimal in Python, and the browser forwards import text without reserialising through JavaScript floating point.

### Phase 4 — PASS for the new web workspace

Shared forest-green shell, token CSS, consistent navigation component, header account menu, period selector, one upload action, pipeline strip, stage chips, viewer gating, and recoverable SSR empty/error states are implemented. Unauthenticated page requests redirect before render. The standalone password-security flow remains separate. Legacy authenticated templates also use a common shell and gated write forms.

Browser checks passed on Overview, Documents, Filing and Search for client A, viewer A, client B and explicit sample mode, at desktop and 390px mobile widths. No fixture identity appears in live/empty page text; no viewer upload/filing controls; every sidebar navigation link has the common class. Screenshots were inspected locally. PDF evidence proxy allows framing only by the same origin.

### Phase 5 — PASS for workbench/workflow; upload-ready exports NOT COMPLETE

Workbench reads gold with four cash comparisons, tax-head set-off, reconciliation, paginated ledger, and state controls. Empty periods have no fixture fallback unless `DEMO_FALLBACK=true`. Sample persistence and generation are blocked at function boundaries. Transitions are transactional and audited; illegal transitions, invalid ARN and locked writes are rejected. Source changes are frozen after validation to avoid stale export artefacts.

JSON generation is explicitly a **preparer draft** with schema ID `bv-draft-2026-09`; it is not certified as current GST portal-upload format. Config mismatch fails. The official developer schema portal could not be accessed during verification. GSTIN is deferred and export validation remains blocked for Red Taxi. Upload-ready GSTR-1/3B schema conformance is therefore not claimed as delivered. This restriction is labelled in the UI and architecture documentation.

### Phase 6 — PASS for executed gates

- Backend: **43 tests passed**, Ruff passed, mypy passed (33 modules).
- Next.js production builds passed, with protected pages rendered dynamically.
- Browser matrix: 4 identities/modes × 4 pages plus mobile checks passed.
- Cloud staging: actual BQ/GCS pipeline, tenant overlap isolation, dedupe, idempotence, transaction/lock checks passed.
- Actual Gemini extraction and human-review-to-gold gate passed.
- Real Red Taxi bootstrap run twice passed; stale bootstrap-password login is separately recorded above.
- SQL interpolation lint and Decimal rejection checks are build-failing tests in Cloud Build.

No claim is made that every legacy API business path received a new end-to-end test. Existing tests remain green and the route audit records the scope.

### Phase 7 — PASS for preview deployment

Build `9654636e-6dcd-4926-ba3f-642944d59e95` passed, but first backend revision failed startup on BigQuery INSERT SELECT syntax. Corrected with an explicit FROM; real bootstrap verification passed. Build `89039911-8dd9-45bc-9714-0494e131dca7` passed and revision `bills-voucher-00088-suw` served zero production traffic on `v5-api`.

Final backend build `34125890-9cf6-4871-85d6-1adab790ff42` passed. Revision `bills-voucher-00089-rex` is on `v5-api`, zero production traffic, with the existing `bills-voucher-app-secret` explicitly bound (the previous preview had an empty session-key environment entry). Final web build `134e43a6-77d2-4603-a3e8-c901af5556d5` includes same-origin PDF evidence viewing. Web deployment and final traffic checks follow.

Repository project-reference replacements remain **0**: no forbidden legacy reference was found in deploy scripts/configuration/docs. No commit or GitHub push has been performed.

Final deployment verified on 2026-09-24:

- Web build `134e43a6-77d2-4603-a3e8-c901af5556d5` succeeded; preview revision `bills-voucher-web-00029-fov`.
- Backend revision `bills-voucher-00090-zun` uses the tested r3 image and the service URL as the Pub/Sub OIDC audience. Subscription configuration matches; the push endpoint remains the isolated `v5-api` tag. This follows [Cloud Run service authentication guidance](https://docs.cloud.google.com/run/docs/authenticating/service-to-service).
- Preview: https://preview---bills-voucher-web-foovqasysa-el.a.run.app
- Authenticated remote checks passed for tenant/profile isolation, effective client role, missing-GSTIN generation rejection, and server-rendered Overview, Documents, Filing and Search. Workspace response was 5.7 seconds. Tests used an owner-authorised temporary signed session in memory; current-password login is not claimed tested and no password was changed.
- Production remains 100% on web `bills-voucher-web-00027-67p` and backend `bills-voucher-00084-5gr`. Original backend `api-preview` remains `bills-voucher-00084-cig`. New revisions receive zero production traffic.
- `git diff --check` passed. All implementation changes remain local and uncommitted; nothing was pushed.

Deferred/incomplete items remain as recorded above: Red Taxi GSTIN, current official portal JSON schema conformance, and automatic multi-year capital-asset scheduling. The deployed preview must not be represented as a completed portal-filing integration.

### Sign-in loop correction — 2026-09-24

After the user-authorised password reset, an actual Chrome sign-in reproduced a redirect back to login despite successful API authentication. SSR forwarded `cookies().toString()`, which percent-encoded base64 padding in the signed session cookie and invalidated its signature. Workspace and document-detail SSR now forward the original incoming Cookie header unchanged. The API-only and temporary-session checks above did not catch this browser flow.

Added padded-session authentication coverage to the local browser matrix; all four modes passed. Production build passed. Cloud Build `7a4ae774-4308-446d-b27f-39d875b8d066` deployed image r5 to preview revision `bills-voucher-web-00030-zil`. Actual Chrome password login, dashboard reload, Documents, Filing and Search all passed against the deployed preview. Production web traffic remains 100% on `bills-voucher-web-00027-67p`. No code was committed or pushed; no password is stored in this report or source files.

### Expired-session sign-in correction — 2026-09-24

Following the authorised push of the preceding changes to `stephenv5` (`2b5d037`), the user reported another login loop. A fresh browser succeeded. Regression tests then reproduced a distinct failure: successful login retained an old session's expired `last_seen`, causing the next authenticated request to return 401. Both HTML and API login now clear the previous session and initialise a fresh idle timestamp after verifying credentials.

Both regression cases failed before the fix; all 45 tests, Ruff and mypy passed after it. Cloud Build `673a0240-3eed-4f1c-9307-1512c62f69b3` succeeded. Backend image r6 deployed to `bills-voucher-00091-law` on `v5-api`. Actual Chrome password login and dashboard reload passed with both a deliberately expired signed test session and a fresh session. Test credentials stayed in memory. Production remains 100% on backend `bills-voucher-00084-5gr`; old `api-preview` is unchanged. This follow-up fix is deployed but not yet committed or pushed.

### Gold-only customer Overview — 2026-09-24

At the user's request, Overview is now a financial dashboard. Python service `app/services/gst/dashboard.py` queries only Gold summary/current-run ledger tables for financial figures. Identity and filing state use their existing metadata tables. Overview shows eligible credit, output tax (including ECO), cash required, input tax and credit adjustments; it excludes the upload control, filenames, raw extracted totals and document pipeline. Documents retains the pipeline and review queue. No sample fallback is permitted on Overview.

Backend gates: 47 tests, Ruff and mypy passed. Tests prove no Bronze/Silver financial reads, no cross-tenant data, current-run selection and Decimal totals. Browser matrix includes empty, viewer, second tenant, sample and populated Gold states on desktop/mobile. A populated mobile table overflow was corrected and the five-state matrix passed. Live verification caught the existing `/api/dashboard` route shadowing the newly registered route; the existing route now delegates to the Gold service, with integrated-router test coverage and a single route registration.

Builds: backend r7 `98588404-6dc7-4946-bc9b-18a90c59ef22`; final web r8 `90e6fa4a-0371-49ce-b85a-12bc61f5ed24`; corrected backend r9 `3babbb21-b3e6-4244-9844-747691d45a04`. Web revision `bills-voucher-web-00031-qoq` serves the preview tag; final backend deployment verification is pending. The user's additional Python-code sentence was truncated; clarification is still pending. These follow-up changes have not been committed or pushed.

Final verification passed: backend `bills-voucher-00093-pez` on `v5-api`, zero production traffic. Actual Chrome login and Overview show the correct tenant and Gold-only financial payload (0 validated invoices for this period), without any FreshKart invoice details, source filenames, review counters or pipeline. Mobile layout passed. Documents still contains the original FreshKart invoice and review queue. Web production remains on `bills-voucher-web-00027-67p`; the preview URL is unchanged.

### Python mock generator, search and conversational assistant — 2026-09-24

Delivered `scripts/generate_mock_data.py` and reusable `app/services/gst/mock_data.py`, producing 15 deterministic synthetic scenarios and portable JSON without cloud writes. Generated all scenarios into ignored `artifacts/mock-data.json`. `/demo` exposes the same generator through Dashboard, Documents, Filing, Search and Assistant tabs, with explicit synthetic labels, no write/filing controls, invoice detail views and pagination. JSON downloads exclude signed-in account metadata. Live Overview remains Gold-only.

Enhanced live and demo search with text terms, review status, decimal amount ranges and pagination. Live search states its latest-500-document bound. `/assistant` provides read-only Gemini answers for the selected customer/period. Demo chat uses only its generated scenario. Both use Gold financial totals, bounded source evidence, bounded conversation history, server-allowlisted citations, input limits, CSRF/authentication and a process-local throttle. No agent write tools or SQL execution exist. Fixed stale CSRF cookie synchronization after session reset and added regression coverage.

Validation: **67 tests passed**, Ruff and mypy passed (38 modules); frontend production build passed. Local browser checks passed for all 15 scenarios, navigation links, read-only controls, pagination, search/no-results, invoice details, cited conversation/follow-ups (stubbed model), and mobile. A separate real Gemini test answered from synthetic Gold facts with a valid source citation.

Cloud Build `807e55ed-3884-4ebe-a4a0-d223627a65c5` (backend r10) and `532238a9-6d96-4e72-a0e4-22ad9bd92d81` (web r11) succeeded. Preview revisions: backend `bills-voucher-00094-zoj`, web `bills-voucher-web-00032-fav`. Actual deployed Chrome checks passed for synthetic-only JSON downloads, mock search, Gemini conversation and citations, separate real-customer assistant context, and unchanged customer document IDs/totals. Production remains 100% on original backend `bills-voucher-00084-5gr` and web `bills-voucher-web-00027-67p`; original API preview tag is unchanged.

Usage and limitations: `docs/mock-data-and-assistant.md`. These follow-up changes remain uncommitted/unpushed on local `stephenv5`.

### Actual-client GST Workspace — 2026-09-25

Replaced the main Demo workspace navigation item with authenticated `/gst/workspace`. Actual-client monthly, quarter and April–March financial-year reports show purchase corrections, ITC decisions and tax-head calculations, reconciliation, sales, GSTR-2B, client configuration and readiness checks. Searches and source-review links operate on the selected customer's records. Gold remains the sole source of financial totals. Consolidated cash adds stored monthly estimates rather than retrospectively offsetting credit across months.

Added scoped report and working-paper ZIP endpoints. Downloads include CSV registers, JSON snapshot, readiness checks, README and SHA-256 manifest, with spreadsheet-formula escaping. Unverified portal JSON, missing registration/frequency, source-review gaps, absent imports and incomplete periods stay explicit. See `docs/gst-workspace.md` for usage and remaining filing boundaries.

Corrected stale Gold after re-review: an accepted invoice that subsequently fails validation now triggers recomputation. Added invoice-total versus taxable-plus-tax validation with rounding tolerance.

Validation: **73 tests passed**, Ruff and mypy passed (40 modules), frontend production build passed. Browser checks passed for monthly/quarterly/year views, every workspace section, searches, correction links, ZIP downloads, mobile layout and existing role-specific pages. Live preview checks passed for password sign-in, actual Red Taxi records, client query-parameter isolation, all three report/download scopes and ZIP integrity. Customer document IDs and amounts were unchanged.

Successful builds: combined r12 `02d23a4d-2c0b-4aeb-a5e2-d23e5f5f4a12`; final backend r13 `f510f4c5-ea08-4251-b6d6-98d2081267ce`. Preview revisions: backend `bills-voucher-00095-pun` (`v5-api`), frontend `bills-voucher-web-00033-haw` (`preview`). Production traffic remains entirely on original backend `bills-voucher-00084-5gr` and web `bills-voucher-web-00027-67p`; old `api-preview` is unchanged. These changes remain uncommitted/unpushed.
