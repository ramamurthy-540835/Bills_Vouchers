# V3 test evidence — 20 October 2026

| Gate | Executed result |
|---|---|
| Full pytest | Latest 507 passed, 7 warnings, 28.21 seconds |
| Ruff app/tests | Passed |
| mypy app | Passed, 87 source files |
| TypeScript noEmit | Passed |
| Next.js production build | Passed, 29 generated pages |
| Full local Playwright | Latest 79 passed, 3.5 minutes; focused correction/source-review subset 5 passed |
| Local synthetic REST/MCP + intake subset | 25 passed before final route test addition |
| CPU benchmark | Executed; see PERFORMANCE_BASELINE.md |
| Live V3 public pages | Desktop/mobile login and registration 200; no overflow |
| Actual inbox | Separate authorized Gmail recipient confirmed receipt; earlier self-address messages not received |
| Authenticated live V3 / GSP | Owner confirmed verified sign-in and dashboard; GSP disabled |
| Live V3 auth boundary | 6 passed after follow-up deployment |
| Live Gemini connectivity | One synthetic operator-identity request returned 200 and expected text; not invoice workflow acceptance |
| Live private health sample | 20/20 returned 200; p50 43.79 ms, p95 86.32 ms, p99 206.12 ms; not load acceptance |

The initial browser run had 71 passes and three failures. Separate labels fixed
the rejection accessibility defect. Upload readiness was guarded before file
selection, and the recovery test now waits for initialization. Website test
teardown waits for outstanding intercepted requests. The subsequent full run
passed all 76 tests.

New correction tests verify request/edit/resubmit, retained evidence and continued
confirmation blocking when GST facts are incomplete. Resubmission returns to
review, not automatic approval. Backend tests cover permissions and versions.

Warnings concern dependency deprecations and pytest's existing cache directory;
they are not hidden test failures. Browser tests use the local synthetic backend,
not real provider or government acceptance. Screenshots are under
artifacts/gst_new_v3; intake mobile was visually inspected.

Formal GST review for all 50 scenarios remains pending. No certified filing
schema, production load SLO or customer database connectivity is claimed.

The first model-isolation regression run found two test settings that depended
on ambient global configuration or omitted a region. Explicit regional test
settings corrected these fixtures without relaxing the global allowlist.
The subsequent full run passed 478 tests. A further mail timeout/redaction test
was added; the final focused mail/model/extraction/assistant run passed 36 tests.
Ruff and mypy passed. The 76 browser tests and frontend build apply to the initial
frontend release; follow-up changes are backend and release tooling only.

Final regression also includes both verification/reset callback generation tests.
All 481 backend tests passed after those additions. Actual mailbox delivery
failed three observations (initial verification, plain diagnostic, fresh
verification); it is not counted as a pass.

## Source mapping and reconciliation increment

The latest backend gate includes exact canonical identity, source versions,
ambiguous references, Decimal discrepancies, snapshot replay, concurrent-change
conflicts, tenant-scoped access and private original downloads. Ruff, mypy,
TypeScript and the production build passed. The full local browser suite passed
78 tests; after the last download-link change, the four focused review tests
passed with no skipped, unexpected or flaky outcomes (13.09 seconds).

Real isolated V3 BigQuery/private GCS integration passed using operator-authorized
service calls: batch replay and reconciliation replay were idempotent; original
bytes matched, foreign source paths were denied, and canonical invoice counts
remained zero before and after. The invoice source was correctly source-only;
the driver event remained ambiguous without a fully matched canonical invoice.
This is storage integration evidence, not authenticated live browser acceptance.
The initial storage attempt exposed a BigQuery conditional SELECT missing FROM;
the query was corrected and rerun successfully.

Sanitized desktop/mobile screenshots are available locally under
artifacts/gst_new_v3/source-reconciliation-1440.png and
artifacts/gst_new_v3/source-reconciliation-390.png. Both were visually inspected.

The owner separately confirmed verified V3 sign-in and dashboard access.
Full financial workflows, recovery delivery, certified filing, professional GST
review and live customer connector acceptance remain incomplete.

Post-release live boundary checks: 8 passed on the deployed 6f7c45f images.
The initial smoke test expected 401 for an anonymous write; the actual 403
csrf_token response correctly enforced CSRF before authentication. The test
expectation was corrected and rerun, with no application security changes.

## Correction queue increment

Seven backend tests cover bounded results, legacy rejected payloads, tenant and
period query parameters, read permissions, invalid filters and access denial.
Full pytest passed 507 tests; Ruff passed. Incremental mypy initially reported
inconsistent PIL attributes after sandbox DLL-denial errors; a fresh
`mypy --no-incremental app` passed all 87 files. No application typing workaround
or security relaxation was introduced.

TypeScript and the Next production build passed. Five focused browser tests
passed, including rejection/correction/resubmission through the queue, state
filters, real API-error display and retry without a false empty state.
Desktop and 390px mobile screenshots were inspected at
`artifacts/gst_new_v3/correction-queue-1440.png` and
`artifacts/gst_new_v3/correction-queue-390.png`.

Actual isolated V3 BigQuery queries ran for all six queue states, returning the
correct empty result for the synthetic acceptance business. Additional read-only
SQL fixtures exercised active/approved/requested filters, legacy rejection and
foreign-tenant/wrong-period exclusion. No records were written. These SQL fixtures
and local browser tests are not a live authenticated customer workflow test.

The subsequent full browser suite passed all 79 tests in 3.5 minutes, including
all nine reports, business switching, uploads, returns, settings and the new queue.

After deployment of 899114f, nine live public/access-boundary checks passed.
The new correction queue requires authentication (anonymous request returned
401). All 31 pre-existing service configuration/IAM fingerprints still match.
This does not substitute for live authenticated financial workflow acceptance.
