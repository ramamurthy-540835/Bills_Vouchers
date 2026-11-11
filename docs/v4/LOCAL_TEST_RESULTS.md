# V4 local acceptance before Cloud Build

11 November 2026. Source branch: `GSTv4`; isolated worktree created from verified remote V3 commit `5656ed8caaf76abc1b859effe5368893ee4fb637`.

| Gate | Actual result |
|---|---|
| Full pytest | **1,014 passed, 27 skipped**, 23.08 seconds |
| Ruff (`app tests`) | Passed |
| mypy (`app`) | Passed, 98 source files |
| TypeScript | Passed |
| Next.js production build | Passed |
| Full production-mode Playwright | **103 passed, 0 failed, 0 skipped, 0 flaky**, 3.3 minutes |
| Before/after protected service/branch/IAM comparison after resource provisioning | Passed |

Machine-readable evidence is in ignored local `artifacts/v4-audit/`: `backend-final.xml`, `backend-final.log`, `frontend-tests.json`, `frontend-production-tests.log`, `frontend-final-build.log`, and `preservation.json`.

The browser suite uses the production Next.js build with the isolated synthetic `tests/gst/browser_backend.py`. It verifies real UI behavior, but does **not** prove live Google Cloud database/storage, email receipt, model extraction or government acceptance. Those require separate V4 live evidence.

Initial backend failures caused by the membership-read refactor were repaired. Development-mode browser runs exposed initialization issues and fixture/readiness problems; these were corrected, and the final complete production-mode run passed. Failed-run evidence is retained locally rather than relabeled passed. The 27 skipped specialist scenarios remain explicitly incomplete.

## Measured local concurrency comparison

The immutable V3 login handler and V4 handler were exercised in the same local ASGI environment: 40 concurrent sign-ins, each with five identical synthetic 25 ms blocking storage/password operations. No cloud calls or real accounts were involved.

| Metric | Before | V4 |
|---|---:|---:|
| Completion P50 from common batch start | 2,825.51 ms | 252.99 ms |
| Completion P95 from common batch start | 5,074.87 ms | 265.09 ms |
| Batch wall time | 5,332.15 ms | 267.56 ms |

Measured batch-wall improvement: 94.98%. This demonstrates removal of event-loop blocking under that controlled workload. It is **not** a Cloud Run latency guarantee, a real password-hashing speed improvement, or a BigQuery performance measurement. Independent live navigation/upload measurements are still required.

## Cloud preparation evidence

Only V4 resources were created. Sixty-eight physical table schemas were copied from current V3 metadata; **zero existing user/customer/financial rows were copied**. Two serialization guard rows were initialized. Fresh V4-only demo credentials and four synthetic business profiles were provisioned through existing application services, with owner memberships, private logos and `gstin_verified=false`. Synthetic operator activation is recorded separately from email verification; these demo identities are not falsely marked mailbox-verified.

No V4 Cloud Run URL, successful build, live extraction or inbox delivery is claimed by this pre-build report. See the final deployment report once those checks execute.
