# V3 test evidence — 20 October 2026

| Gate | Executed result |
|---|---|
| Full pytest | 474 passed, 7 warnings, 8.97 seconds |
| Ruff app/tests | Passed |
| mypy app | Passed, 85 source files |
| TypeScript noEmit | Passed |
| Next.js production build | Passed, 29 generated pages |
| Full local Playwright | 76 passed, 2.0 minutes |
| Local synthetic REST/MCP + intake subset | 25 passed before final route test addition |
| CPU benchmark | Executed; see PERFORMANCE_BASELINE.md |
| Live V3 / actual inbox / GSP | Pending, not counted as passed |

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
