# GST Easy V2 test results

Backend full pytest: 426 passed after V2 isolation/identity/report additions. Ruff app/tests: passed. mypy app: 80 files passed. TypeScript and Next.js production build: passed.

First full Playwright run: 66 passed, 1 failed (website success notification lost because profile version changed the parent component key). Root cause fixed; full rerun: 67 passed in 1.5 minutes.

Synthetic documents: every one of 28 normal invoices passes existing structural/tax arithmetic validation; expected totals independently recomputed from Decimal unit prices/quantities. All three B2B statements pass the existing parser. GSTIN-like identifiers have valid structure/checksum, not verified government registrations. Edge-case expectations are in TEST_MANIFEST.json; they are not claims of live AI extraction success.

Native Python dependencies required execution outside the sandbox. Existing FastAPI/httpx/Google typing deprecation and pytest cache warnings were non-fatal. Initial V2 guard SQL was rejected by BigQuery because SELECT lacked FROM; corrected to SELECT FROM a singleton. No financial rows were created.

Local tests use isolated synthetic repositories and response mocks where noted by existing tests. They are separate from live V2 acceptance. Live authenticated tests and cloud extraction have not yet passed; do not mark them complete.
