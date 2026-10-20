# V3 test evidence — 20 October 2026

| Gate | Executed result |
|---|---|
| Full pytest | Initial 474 passed; model-isolation follow-up 478 passed, 7 warnings, 9.51 seconds |
| Ruff app/tests | Passed |
| mypy app | Passed, 86 source files after model-isolation follow-up |
| TypeScript noEmit | Passed |
| Next.js production build | Passed, 29 generated pages |
| Full local Playwright | 76 passed, 2.0 minutes |
| Local synthetic REST/MCP + intake subset | 25 passed before final route test addition |
| CPU benchmark | Executed; see PERFORMANCE_BASELINE.md |
| Live V3 public pages | Desktop/mobile login and registration 200; no overflow |
| Actual inbox | Failed: user confirmed verification and plain diagnostic were not received |
| Authenticated live V3 / GSP | Blocked / disabled, not counted as passed |

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
