https://preview-v3---bills-voucher-web-foovqasysa-el.a.run.app

# Stephen version 3 — remaining-work handoff

Updated: 2026-10-09

Branch: [stephen_version3](https://github.com/ramamurthy-540835/Bills_Vouchers/tree/stephen_version3)

## Status: approximately 95% complete; 5% acceptance work remaining

This is a scope estimate, not a source-line metric. The old 65% snapshot is superseded. V3 is now built, deployed and verified on isolated web/API tags. Production, original preview and preview-v2 routing are unchanged.

| Area | Completed scope points | Remaining |
|---|---:|---:|
| GST Easy copy and customer interface | 23 / 25 | 2: unavailable glossary DOCX |
| Bill upload, review, validation and calculations | 35 / 35 | 0 |
| BigQuery, GCS configuration, queue and isolated deployment | 20 / 20 | 0 |
| Automated verification and release acceptance | 17 / 20 | 3: actual customer evidence acceptance |
| Total | 95 / 100 | 5 |

## Completed since the 65% snapshot

- Independent recorded/matched/eligible/no-credit scenarios, GSTR-2B import, mixed-line credit allocation and canonical Returns & Credit working papers.
- Reverse-charge payment references restricted to admin/tax_admin; stale-version handling, concurrent duplicate protection, retained period for missing dates, rejected-record correction and credit-note treatment.
- File signatures, workbook safety limits, formulas rejected, state names in template instructions and appropriate original-file preview/download.
- Actual Vertex schema compatibility checked; missing extraction values force human review.
- Durable Cloud Tasks uploads, per-file progress, retry-safe invoice IDs, silver extraction caching and browser polling resume.
- Shared copy audit, mobile checks and frontend branding build argument.
- Additive BigQuery migration applied; invoice and matching write probes rolled back without retaining test invoices.
- Runtime permissions checked, isolated queue created and real OIDC delivery verified using an empty operational job.
- GCP build/deploy complete: web `bills-voucher-web-00050-rij`, API `bills-voucher-00109-quv`; both have zero production traffic.
- 129 backend tests and 3 local browser tests passed. Live: 2 browser tests passed, 1 synthetic-upload test intentionally skipped, 6 API smoke groups and the queue check passed. TypeScript, Ruff, source-copy search and SQL checks passed.
- Release report, exact deployment evidence and live screenshots: [docs/releases/v7.md](releases/v7.md).

## Remaining 5%, with concrete acceptance steps

### 1. Integrate the supplied glossary document — 2 points

Dependency: `GST_Dashboard_Terms_Explanation.docx` is not present in this workspace.

1. Read sections 1–4 and 6 when the document becomes available.
2. Compare them with `frontend/lib/copy/gst.ts` (`TOOLTIPS` and glossary copy).
3. Add missing explanations as paraphrases without changing financial calculations. Preserve the clearly labeled Supplier A/B/C illustration.
4. Check every KPI/scenario Learn more link and the glossary's live-number formula on desktop/mobile.
5. Run TypeScript and `tests/frontend/copy.spec.ts`, then build/deploy the changed frontend to `preview-v3` only.

Current fallback: the prompt's minimum explanations and formula are implemented. Do not claim the unavailable document's full sections have been incorporated.

### 2. Run customer-evidence acceptance — 3 points

Dependencies: real client GSTIN/profile details and genuine customer bills/GSTR-2B. Do not fabricate these or load demo invoices into Red Taxi's canonical tables.

1. Complete and verify the actual client GSTIN in Client profile. Upload/review already work while it is missing; confirmation is correctly blocked.
2. Upload an actual PDF/photo plus a completed template under `/bills` in the relevant period.
3. Verify progress survives a reload; open the original through the authenticated endpoint; correct extracted fields and confirm eligible records.
4. Check bronze original, silver JSON and canonical invoice/line/audit records have the same tenant and source ID. Check extraction usage for a genuine AI-read bill.
5. Import that period's real GSTR-2B B2B invoice JSON. Compare recorded, matched, eligible and no-credit calculations, tax heads, a blocked/non-GST purchase and any genuine credit note with the CA's figures.
6. Export the purchase register and CA working papers; confirm that only confirmed customer bills are included.
7. Record the result without committing personal bill evidence, credentials or raw customer exports. Investigate any mismatch before treating the estimates as return-ready.

Automated equivalent scenarios are covered locally. Live checks intentionally did not write synthetic financial records, so a complete live customer ingestion/confirmation cycle is not yet claimed.

## Operating boundaries

- Real filing submission, full GSTR-2B amendment/CDNR ingestion and opening-credit-ledger management are outside the completed v3 bill flow. The estimate remains indicative.
- Parameterize client IDs, preserve Decimal/string/NUMERIC money and additive migrations, and check `can` on writes. Never export or persist sample bills.
- Keep `preview-v3` and `api-preview-v3` at zero production traffic. Re-read current traffic immediately before a future deployment; another operator may change production.
- Preserved web: original `00036-zoq`, v2 `00042-joq`, production `bills-voucher-web-public-redtaxi-api` at 100%.
- Preserved API: `v5-api=00096-bik`, `api-preview=00098-fim`, `v7-api=00101-sip`, production `bills-voucher-redtaxi-account` at 100%.

## Verification and deployment entry points

- Backend: `python -m pytest -q`; lint: `python -m ruff check app/gst app/routers/gst_bills.py tests/gst`.
- Frontend: `npx tsc --noEmit`; `npx playwright test` from `frontend/`.
- Local browser harness: `uvicorn tests.gst.browser_backend:app --port 8103`; frontend on port 3100 with `BACKEND_URL=http://127.0.0.1:8103`. Never deploy this fake-auth harness.
- Live checks: `scripts/v3_live_smoke.py`, `scripts/v3_queue_smoke.py`, and Playwright with `BV_TEST_URL`, `BV_TEST_EMAIL`, `BV_TEST_PASSWORD` supplied through the environment. The queue probe leaves one empty operational job and no financial rows.
- Schema: `scripts/prepare_v3_bq.py`; account SQL dry run: `scripts/v7_sql_gate.py`. These remove PYTHONPATH from gcloud's subprocess environment.
- Build: `cloudbuild-v3.yaml`; deploy tested build IDs with `scripts/deploy_v3.py --api-build <id> --web-build <id>`.
- Decisions: [docs/decisions/v7.md](decisions/v7.md). V2 history: [docs/v7-progress.md](v7-progress.md).
- One-time copy/shell migration scripts have already run; do not rerun them on the current source.
