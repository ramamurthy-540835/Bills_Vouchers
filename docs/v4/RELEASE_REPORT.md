# GST Easy V4 release report

**Status: READY WITH LIMITATIONS**

**Report date:** 12 November 2026

**Repository:** `ramamurthy-540835/Bills_Vouchers`

**Branch:** `GSTv4`

**Application source commit deployed:** `ada1bd386d9347481431fe3cadb529031e497ce9`
**Source branch:** `GST_NEW_V3` at `5656ed8caaf76abc1b859effe5368893ee4fb637`

This report supersedes the pre-deployment verification states in `DEFECT_TRACEABILITY.md` and `LOCAL_TEST_RESULTS.md` where this report provides newer evidence. It records the actual V4 candidate deployment and distinguishes verified behavior from outstanding acceptance.

## Defect outcomes

| Finding | Work completed | Verification and remaining limit |
|---|---|---|
| F01 Login | Kept password, active-account, email-verification, role, session and version checks. Moved blocking identity/storage work off async request handlers and added malformed-body/email validation. | Live V4 demo sign-in returned HTTP 200; the workspace, `/api/auth/me`, and authenticated private bill context loaded. The email/password pictured in the workbook was not available as a V4 identity; that individual credential pair was not tested. |
| F02 Verification and password reset | Separated reset and verification instructions and responses; preserved token digest, expiry, one-use, rate-limit and session revocation behavior. Auth email dispatch is asynchronous. | V4 registration to the previously authorized test inbox returned 201. The V4 Cloud Task reached the mail worker (HTTP 200), and SMTP logged provider acceptance at `2026-11-12T08:10:18.484Z`, Message-ID `<179447101752.2.7501860562870717330@aidirac.com>`. Provider telemetry says inbox delivery is **not confirmed**. Owner confirmation and link consumption remain pending. Live reset-token consumption was not tested. |
| F03 Navigation and bill loading | Added a request-local authenticated workspace context for non-dashboard navigation, reused membership reads only within a GET request, and moved blocking worker preparation off the event loop. Sanitized timing metrics are opt-in. | Live V4 sign-in/workspace and bill-context requests succeeded. Warm public login-page GET: 136.57 ms (one sample). Local controlled concurrency comparison: batch P95 5,074.87 ms before vs 265.09 ms after; 94.98% batch-wall reduction for that synthetic ASGI workload. This is not a Cloud Run before/after latency claim. A matched live navigation benchmark remains outstanding. |
| F04 Upload and extraction | Preserved originals and separate processing exceptions, reduced redundant storage/job writes, and added content-free processing-stage timings. Existing deterministic validation and review gates remain active. | One synthetic PDF was uploaded via the V4 Bills UI and processed asynchronously. The upload endpoint returned 200; job completed and produced one `needs_review` invoice. Gemini extraction matched all 35 tested source-manifest fields; no `field_issue` flags or field/amount mismatches. `line_price_incomplete` correctly kept the invoice in manual review because the source did not establish whether unit prices were inclusive or exclusive. Worker elapsed time was 37.84 s; upload acknowledgement to terminal job polling was about 50 s. The workbook’s original real invoice/photo was not supplied; JPEG, PNG, spreadsheet, duplicate, unreadable-image and multi-page live cases remain untested. |

The synthetic upload’s final state is intentional: successful extraction is distinct from approval. Auto Review was OFF, and V4 did not silently confirm a bill whose pricing basis was ambiguous.

## V4 Cloud Run deployment

| Component | Value |
|---|---|
| Project / region | `aidirac-503309` / `asia-south1` |
| Build | `3b9b664e-9724-44a8-8604-08b52d681a04` — SUCCESS |
| Build source | Exact pushed `GSTv4` application commit `ada1bd386d9347481431fe3cadb529031e497ce9` |
| API service / revision | `gst-easy-v4-api` / `gst-easy-v4-api-00002-97d` |
| API image | `asia-south1-docker.pkg.dev/aidirac-503309/gst-easy-v4/api@sha256:193e8fa958a1e02b4addb16135c0b3a35e973832d62d09e271d94ed07cb3d6b3` |
| API URL | `https://gst-easy-v4-api-foovqasysa-el.a.run.app` |
| Web service / revision | `gst-easy-v4-web` / `gst-easy-v4-web-00001-4pj` |
| Web image | `asia-south1-docker.pkg.dev/aidirac-503309/gst-easy-v4/web@sha256:409d3055bf741d3b37ef6a2d172efdd3504cff353ff88529b94c7d2569f39687` |
| Web URL | `https://gst-easy-v4-web-foovqasysa-el.a.run.app` |

Cloud Run `status.url` was queried for both services. The web login route returned HTTP 200. The browser authenticated through the web proxy to the private API. The V4 API service IAM has only the V4 API and web service accounts as invokers; no project-wide `allUsers`/`allAuthenticatedUsers` Run Invoker grant was found. Only the V4 web service received public invoker access for the login surface.

The frontend is paired with the V4 API URL/audience. The API is configured with the V4 dataset prefix, V4 BigQuery datasets, V4 private document bucket and V4 task queues. Four V4 datasets contain copied table schemas only; no V2/V3 user, customer or financial rows were copied. Two synthetic V4 demo identities and four synthetic business profiles were provisioned. A third pending diagnostic identity was created only in V4 for authorized mail delivery testing. One synthetic purchase invoice now exists in the first demo business. Demo passwords are held only in V4 Secret Manager and are deliberately excluded from this report.

## Local quality gates

The exact deployed application commit passed before the build:

- pytest: **1,014 passed, 27 skipped**, 12 warnings.
- Ruff: passed (`app tests`).
- mypy: passed (98 source files).
- TypeScript: passed.
- Next.js production build: passed.
- Production-mode Playwright: **103 passed, 0 failed, 0 skipped, 0 flaky**.

The 27 skipped specialist tests remain skipped. The earlier V3 compliance matrix also has scenarios that are only partially specified or skipped; this V4 release does not claim legal approval or complete scenario coverage. Evidence is retained in local ignored `artifacts/v4-audit/` files. Initial development test failures were fixed before the final production-mode run; those intermediate failures are not counted as passes.

## Isolation evidence

Post-deployment comparison passed for all checks:

- `bills-voucher`, `bills-voucher-web`
- `gst-easy-v2-api`, `gst-easy-v2-web`
- `gst-easy-v3-api`, `gst-easy-v3-web`
- Existing V2/V3 Git branch SHAs
- Existing project IAM bindings, excluding only newly added V4 identities

Each protected service’s spec, traffic and service IAM matched the pre-change snapshot. No old URL, revision, environment, traffic allocation, dataset or customer record was intentionally changed. Machine-readable evidence: ignored `artifacts/v4-audit/preservation.json`.

## Outstanding acceptance

1. The owner must confirm whether the V4 verification email actually arrived at `ai@aidirac.com` (inbox or spam) and consume its V4 link. SMTP acceptance alone is not delivery proof. The provider’s organization-level delivery disposition requires mail-admin logs if the message is still missing.
2. The workbook’s pictured real invoice was not supplied. Test authorized real documents only with an explicitly approved sample; synthetic tests do not prove extraction quality for all real bills.
3. Live PNG/JPEG/XLSX/CSV, low-quality image, duplicate/retry, multi-page PDF, cross-business switch, invalid/unverified/disabled sign-in and password-reset completion need additional live acceptance.
4. Full GST legal/rate review, the outstanding specialist/skipped scenarios, approved automatic-confirmation policy and government/GSP filing are not part of this deployment. Filing remains unavailable/disabled unless independently authorized and verified.
5. Live Cloud Run p50/p95 navigation and invoice processing benchmarks require a larger matched workload. The single synthetic PDF timing is one observation, not an SLA.

The application is deployed and usable at the V4 web URL above, but the evidence supports **READY WITH LIMITATIONS**, not production GST-compliance certification.
