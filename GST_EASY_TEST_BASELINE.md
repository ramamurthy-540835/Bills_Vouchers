# Test baseline — 14 October 2026

Executed before new Phase 01 edits, including preserved October changes.

| Check | Result |
|---|---|
| python -m pytest -q | 151 passed; 7 dependency/deprecation/cache warnings |
| python -m ruff check app tests | Passed |
| python -m mypy app | Failed: 11 errors in 4 files |
| TypeScript tsc --noEmit | Passed |
| Next.js production build | Passed; 16 static pages processed |
| Playwright | 4 passed against local synthetic API |
| git diff --check | Passed; Windows line-ending notices |

Mypy errors predate new phase work: report.py nullable match row (1); template.py inferred mixed iterable/row/date types (5); jobs.py Cloud Tasks import (1); gst_bills.py untyped upload/job collections (4). Do not hide these with disabled checking.

Browser coverage: dashboard/navigation/empty states; CSV upload, exact duplicate, review/save/reopen/reject/delete and missing GSTIN confirmation block; registration mismatch; 390px mobile/viewer controls. These are not live customer financial acceptance tests.

Python interpreter: C:/Users/BIS/Stephen/GST/Bills_Vouchers/.venv/Scripts/python.exe, with PYTHONPATH set to repository .testdeps. Sandbox execution initially failed to load cryptography DLLs; approved execution outside the sandbox passed. Node: C:/Users/BIS/Stephen/ITR/income-tax/.tools/node-v22.22.0-win-x64/node.exe. Browser: installed Chrome. Local test API: tests.gst.browser_backend on 8103; frontend on 3100 with BACKEND_URL pointing to that API. Do not deploy the synthetic test backend.

No newly implemented verification, recovery, OTP or migration is included in these baseline results.

## Follow-up validation

The initial 11 type errors were corrected. Checking again with .testdeps on PYTHONPATH exposed two additional pre-existing Gemini heterogeneous-input inference errors in app/gst/extract.py and app/services/gemini.py. Explicit SDK ContentListUnion annotations fix those without altering the request payload. Fresh mypy with this dependency path passes for all 61 source files; the extraction regression and Ruff pass. See GST_EASY_PHASE_01_REPORT.md for subsequent account tests and outstanding acceptance requirements.
