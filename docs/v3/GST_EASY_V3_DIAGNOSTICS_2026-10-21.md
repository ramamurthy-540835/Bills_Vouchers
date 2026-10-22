# GST Easy V3 diagnostics — 21 October 2026

Outcome: all executed local tests and live demo acceptance checks passed. This is not complete production, statutory or external-provider acceptance. No application code or cloud configuration was changed, and no financial records were uploaded, edited, confirmed or deleted during this pass. Login/logout, selected-business session changes and a grounded assistant request were exercised.

## Source and runtime

- Local branch: `GST_NEW_V3`; HEAD `00ade9e489603e44d9e8848ad0f8de24a7059232`.
- Live frontend: https://gst-easy-v3-web-foovqasysa-el.a.run.app
- Frontend revision: `gst-easy-v3-web-00005-jbp`.
- Backend revision: `gst-easy-v3-api-00006-g98`.
- Frontend BACKEND_URL points exclusively to the V3 API.
- Runtime configuration references V3 BigQuery datasets, document bucket, bill queue, auth queue and frontend callback URL. This configuration inspection is not a new exhaustive IAM least-privilege audit.
- Existing untracked user-guide PDF and generator were preserved.

## Executed quality gates

| Check | Actual result |
|---|---|
| Full pytest suite | 509 passed, 6 dependency/FastAPI deprecation warnings; 12.36 seconds |
| Ruff, app and tests | Passed |
| mypy, app | Passed; 87 source files |
| TypeScript noEmit | Passed |
| Next.js production build | Passed |
| Full Playwright suite, synthetic local backend | 79 passed; 1.9 minutes |
| Live public access boundaries | 9 checks passed |
| Live manual demo acceptance | Passed across all three businesses |
| Live preloaded demo acceptance | Passed |
| Live KPI comparison | All nine match the independent fixture manifest |
| Live report row comparison | All nine match expected counts |

Local browser coverage includes business creation/profile, website/logo editing and permissions, navigation, uploads and validation, invoice preview formats and fallback, financial formatting, nine reports, statement import, return-review separation, source mapping/reconciliation, and correction workflows. These local mutation tests use the synthetic backend; they are not fresh live upload, OCR, filing or provider acceptance.

## Live checks

Both demo logins succeeded, refresh preserved sessions, and logout invalidated access. The manual account retains three authorized owner businesses with logos and profile websites and zero invoices. Switching selected business correctly; switching to an unrelated preloaded business returned 403.

The preloaded account retains 23 invoices: 20 confirmed, two needing review and one rejected. All 23 upload jobs were completed. Downloaded PDF, PNG and JPEG originals matched fixture hashes. Invoice-number search returned the expected record. The grounded assistant identified the two pending invoices and excluded the rejected example. Reconciliation returned 11 cases. All nine report pages rendered. Synthetic export protection and foreign-business denial remained enforced.

Desktop (1440px) and mobile (390px) live dashboard/profile screenshots were captured, with automated page overflow checks. Dashboard screenshots were visually inspected: desktop retains the 3×3 KPI grid and mobile stacks cards; wide financial tables use contained scrolling.

| KPI | Actual and expected |
|---|---:|
| Usable ITC | ₹5,781.60 |
| GST liability | ₹23,960.16 |
| Estimated cash requirement | ₹18,178.56 |
| Purchases without ITC | ₹11,038.00 |
| Confirmed sales | ₹1,90,918.16 |
| Confirmed purchases | ₹93,874.72 |
| Pending reviews | 2 |
| Reconciliation mismatches | 3 |
| Unmatched invoices | 3 |

Report row counts: ITC 20; liability 10; cash 16; purchases without ITC 8; pending 2; mismatches 3; unmatched 3; sales 10; purchases 10. Expected values came from `demo bills/naturelabs1/TEST_MANIFEST.json`; monetary comparisons used Decimal. No totals were seeded.

## Findings requiring follow-up

1. **Dashboard latency:** one authenticated dashboard API request took 4.435 seconds, including client/network time. This exceeds the proposed 500ms cached-read target for this sample. It is not a p95 measurement; cache behavior and repeated warm samples need profiling before claiming an SLA.
2. **Historical preservation drift:** the strict baseline check failed for unrelated `prism-frontend`, which moved from revision `00020-84c` to `00027-nur`, with different traffic. This run made no deployment/configuration changes. Attribution and authorization of that historical change were not established. Do not overwrite the baseline or roll back this unrelated service automatically.
3. **V2 preservation verified separately:** `gst-easy-v2-web`, `gst-easy-v2-api`, `bills-voucher` and `bills-voucher-web` configurations and IAM match the historical baseline. The broader comparison output records every baseline service; full IAM comparison stopped at historical drift, so no blanket all-service IAM assertion is made.
4. **Historical runtime errors:** the bounded last-24-hour severity ERROR query returned 21 entries, all dated October 20. None were returned for October 21 at query time. Only sanitized timestamp/service/status metadata was collected; no new root-cause claim is made from metadata alone. Previous upload concurrency/recovery issues still warrant dedicated load and retry testing.
5. **Maintenance:** six Python deprecation warnings remain. Local production start also warns that standalone output should use its generated server; browser tests nevertheless passed against the local built app.

## Not verified or intentionally excluded in this pass

- Fresh live registration, inbox delivery, password recovery, bounce/complaint handling and verification expiry. Prior user-confirmed Gmail delivery is historical evidence, not a test executed today.
- New live uploads/OCR, duplicate submission, destructive invoice actions, business creation, profile mutation and statement re-import: exercised locally where covered, not repeated against the demo baseline.
- Live government submission, government acknowledgements, authorized GSP verification and external customer MCP/REST credentials remain unavailable; synthetic tests cannot certify these integrations.
- Full statutory/effective-date GST coverage and all 50 scenarios require professional review. Decimal fixture agreement is not legal certification.
- Live maker-checker return approval and restricted exports remain blocked for synthetic tenants by design.
- Large concurrent ingestion, 100,000-row workloads, disaster recovery and production cost/SLA acceptance were not executed.

## Local performance measurements

These CPU-only synthetic benchmarks exclude network, authentication, storage and OCR.

| Operation | p95 |
|---|---:|
| Declared-rate inclusive arithmetic, 1,000 iterations | 0.0074 ms |
| Normalize 10 records, 25 iterations | 0.1018 ms |
| Normalize 1,000 records, 25 iterations | 14.3345 ms |
| Normalize 10,000 records, 25 iterations | 102.5065 ms |

No microsecond end-to-end upload claim or before/after performance improvement is asserted.

## Evidence

Local evidence directory: `artifacts/diagnostics-2026-10-21/` (ignored generated diagnostics).

- `pytest.log`, `pytest.xml`, `ruff.log`, `mypy.log`, `typescript.log`, `build.log`
- `browser.log`, `browser.json`
- `source-release-smoke.json`, `manual-demo-acceptance.json`, `naturelabs1-browser-acceptance.json`
- `financial.json`, `runtime.json`, `preservation-drift.json`, `live-results.json`
- `cloud-errors.json`, `local-performance.json`
- `naturelabs1-live-dashboard-1440.png`, `naturelabs1-live-dashboard-390.png`
- `manual-demo-profile-1440.png`, `manual-demo-profile-390.png`

No deployment, push, secret rotation, cloud IAM change or financial-data mutation was performed. Remaining release dependencies must not be represented as completed merely because this diagnostic pass succeeded.
