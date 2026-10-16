# GST Easy V2 test results

Backend full pytest: 426 passed after V2 isolation/identity/report additions. Ruff app/tests: passed. mypy app: 80 files passed. TypeScript and Next.js production build: passed.

First full Playwright run: 66 passed, 1 failed (website success notification lost because profile version changed the parent component key). Root cause fixed; full rerun: 67 passed in 1.5 minutes.

Synthetic documents: every one of 28 normal invoices passes existing structural/tax arithmetic validation; expected totals independently recomputed from Decimal unit prices/quantities. All three B2B statements pass the existing parser. GSTIN-like identifiers have valid structure/checksum, not verified government registrations. Edge-case expectations are in TEST_MANIFEST.json; they are not claims of live AI extraction success.

Native Python dependencies required execution outside the sandbox. Existing FastAPI/httpx/Google typing deprecation and pytest cache warnings were non-fatal. Initial V2 guard SQL was rejected by BigQuery because SELECT lacked FROM; corrected to SELECT FROM a singleton. No financial rows were created.

Local tests use isolated synthetic repositories and response mocks where noted by existing tests. They are separate from live V2 acceptance.

Live V2 API checks passed: normal client identity with three memberships, platform administrator endpoint denied (403), unauthorized business switch denied with original context preserved, synthetic financial export denied (403), and dashboard confirmed invoice count zero. Direct unauthenticated private API access returns 403; frontend login page returns 200.

Actual runtime settings verified after deployment: isolated V2 datasets/bucket/queue, service identities and frontend audience/backend pairing. All 29 previous Cloud Run service configurations and IAM policies match the baseline. BigQuery counts: one user, three test businesses, zero canonical invoices, zero statement records.

Initial live login returned 503 because Windows consumed gcloud's custom environment separator. Corrected new V2 services with structured environment files; real sign-in subsequently passed. The first report test incorrectly expected a generic empty panel for the cash report, which intentionally retains tax-head scenario rows. Corrected the assertion to require zero source invoices without changing financial behavior.

Cloud invoice extraction, post-upload dashboard arithmetic and imported-statement reconciliation are not live-accepted: the owner explicitly requested no financial seeding/uploads. These remain manual acceptance steps against the generated pack.

All nine dedicated report routes passed live browser checks with the actual deployed API and empty persisted financial tables: usable ITC, GST liability, cash requirement, purchases without ITC, pending reviews, reconciliation mismatches, unmatched invoices, sales register and purchase register. All three business profiles, private logos, switching and refresh persistence passed. These checks do not establish financial accuracy after future uploads.

Final live browser run exited successfully, including logout, authenticated page-navigation smoke and profile widths 1440/768/390px with no page overflow. Sanitized synthetic screenshots are retained locally in artifacts/gst_easy_v2/live-profile-{1440,768,390}.png; desktop and mobile images were visually inspected. Evidence JSON: live-results.json, live-access-results.json, resource-verification.json. These private execution artifacts are excluded from Git; reproducible verification scripts are committed. Release helper Python compilation and git diff --check passed after the environment-file fix.
