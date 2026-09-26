# Stephen version 3 — implementation handoff

Snapshot date: 2026-09-26

Branch: `stephen_version3`

GitHub: https://github.com/ramamurthy-540835/Bills_Vouchers/tree/stephen_version3

## Status: approximately 65% complete; approximately 35% remaining

This is a scope estimate, not a measured percentage of source lines. The branch
is a work-in-progress snapshot, not a release-ready build. It includes the earlier
uncommitted v7/v2 improvements as well as the new v3 implementation.

**V3 has not been built or deployed in GCP. The v3 BigQuery migration has not been
applied.** The latest instruction was to push the current code and leave this
handoff, so further implementation/deployment stopped for this snapshot.

The migration attempt stopped while obtaining an access token, before any SQL
was submitted. A local test dependency on PYTHONPATH conflicted with gcloud's
bundled OpenSSL libraries. This is a local process-environment issue; do not
reinstall gcloud or alter production to fix it.

## Completed and checked

- Central copy module `frontend/lib/copy/gst.ts`: default GST Easy name with env
  override, requested rename map, KPI/scenario explanations, field/reason labels.
- GST Easy dashboard and glossary drawer with formula and labeled A/B/C example.
- Bills page with multi-file selection/drop, per-file progress, template download,
  period/status filtering, review layout, original-file panel, edits, confirmation,
  rejection and purchase-register export links.
- `/documents` returns a 301 redirect to `/bills`; existing backend API routes remain.
- Decimal-based canonical invoice schema, GSTIN checks, arithmetic/tax-head checks,
  financial-year duplicate detection and profile-driven v6 eligibility reuse.
- Deterministic XLSX/CSV template parsing; structured Vertex extraction for PDFs
  and images, with low-confidence review behavior and token-usage logging code.
- Tenant-bound API and BigQuery storage implementation; original-file access is
  authenticated. Gold/silver/audit mutations use parameterized transactional SQL.
- Additive migration `infra/bq/migrations/007_gst_invoice.sql` is written.
- Missing client GSTIN permits upload/review but prevents confirmation.
- **109 backend tests passed**: existing suite plus 23 new v3 tests, including
  permissions, tenant isolation, Decimal values and mocked extraction.
- **2 local Playwright tests passed**: naming/tooltips/glossary/navigation/redirect,
  and CSV upload → edit → blocked confirmation → rejection.
- TypeScript check passed after the browser-test fixes; rerun it after further edits.
- Required source search returned no forbidden legacy strings in `frontend/app`.
  The requested CA caption retains “Eligible ITC” inside `lib/copy/gst.ts`.

Local test results are not proof that BigQuery, GCS or Vertex work in the deployed
environment. Browser upload testing used an isolated in-memory test backend; it
did not create test records in Red Taxi's workspace.

## Remaining work, in order

### 1. Finish functionality and reliability (about 15 percentage points)

- [ ] Complete dashboard reconciliation against real GSTR-2B records. Currently
  the matching scenario says “Not yet matched”; recorded and eligibility scenario
  amounts share the same confirmed-credit calculation. Do not present these as
  four independently computed scenarios until actual matching is wired.
- [ ] Review mixed eligible/blocked/non-GST line treatment. The current canonical
  invoice has one ITC status; an invoice containing mixed categories needs correct
  allocation before headline usable credit is considered complete.
- [ ] Connect canonical bills to Returns & Credit/filing preparation. The new
  GST Easy dashboard reads canonical confirmed records; the older filing screen
  still uses its existing medallion workflow. Never mix v2 sample amounts into
  real customer calculations or exports.
- [ ] Define and complete reverse-charge review/payment evidence. These bills
  currently remain in review instead of being confirmed without evidence.
- [ ] Finish validation edge cases: rejected bill reopening policy, concurrent
  duplicate uploads, edit-version conflicts, missing-date period retention,
  credit/debit notes, unequal line/header totals and tax-negative cases.
- [ ] Validate production Vertex response-schema compatibility and PDF/image
  extraction with approved non-customer test evidence; never silently treat a
  failed extraction as a validated invoice. Current failures retain the original
  and create a record for manual review.
- [ ] Harden file handling: MIME/signature checks, XLSX archive-expansion limits,
  spreadsheet formula handling, aggregate API payload limits and batch recovery.
- [ ] Upload processing currently runs inside each HTTP request. The UI sends
  each file separately and displays per-file results. Confirm bounded processing
  time, or use durable Cloud Tasks if queued processing/resume is required; do
  not introduce in-memory background tasks in Cloud Run. The progress endpoint
  exists, but job_id is returned after processing rather than immediately.
- [ ] Make the original-file panel choose an appropriate preview for PDF/images
  and a download treatment for XLSX/CSV. Verify authenticated iframe behavior.
- [ ] Complete the template Instructions state-code **names** list and check
  formatting/dropdowns, row grouping, supplier-name completion and CSV parity.
- [ ] Finish a copy audit of shared GST shell/older filing components and
  backend-produced messages. Move remaining customer copy to the central module;
  show technical identifiers only in a Details disclosure. Check mobile layouts.
- [ ] The referenced `GST_Dashboard_Terms_Explanation.docx` was not supplied.
  The current drawer uses the prompt's explanations, not the missing document's
  full sections 1–4 and 6. Incorporate that document when available.
- [ ] Add openpyxl/pdfplumber to `pyproject.toml` dependencies as well as the
  already updated `requirements.txt`, so a normal package installation includes them.

### 2. BigQuery and GCP preparation (about 10 percentage points)

- [ ] Fix `scripts/prepare_v3_bq.py` to invoke gcloud with PYTHONPATH removed from
  the subprocess environment. Example: copy `os.environ`, remove `PYTHONPATH`,
  and pass the result as `env=` to `subprocess.check_output`. Never print tokens.
- [ ] Apply `infra/bq/migrations/007_gst_invoice.sql` to `aidirac-503309` only after
  checking dataset locations and schema compatibility. No destructive migrations.
  Tables: `gold.gst_invoice`, `silver.gst_invoice_line`,
  `ops.gst_bill_job`, `ops.gst_bill_audit`, `ops.gst_bill_lock`, `ops.extraction_log`.
- [ ] Run and finish the rollback-only SQL probe in `scripts/prepare_v3_bq.py`.
  Verify no test invoice/audit/lock rows remain. Add concurrency/duplicate probes.
- [ ] Verify the v3 runtime identity can query/write these datasets and access
  `aidirac-503309-bills-voucher-documents`; grant only missing scoped permissions.
- [ ] Verify bronze and silver GCS paths are client-first and source downloads
  cannot access another client's path. Check token logging with the real model.
- [ ] Set `GST_BILLS_ENABLED=true` on the **new v3 API revision only**.
  V3 canonical dashboard/upload paths must stay independent of sample fallback.
- [ ] Create a separate API tag, planned `api-preview-v3`, with no production
  traffic. Include the v3 web origin in that revision's allowed origins and use
  appropriate request timeouts for extraction. Preserve existing API tags.

### 3. Final gates, build, deploy and release report (about 10 percentage points)

- [ ] Rerun the full backend suite, new edge-case tests, TypeScript, lint and the
  required source-label search after all remaining changes. All gates must pass
  **before** deployment. Do not bypass a failing test to ship the preview.
- [ ] Rerun local Playwright tests against the local test backend; add review of
  valid confirmed bills, viewer behavior, desktop/mobile layout and API failures.
- [ ] Build backend and frontend images in GCP. The root Dockerfile builds
  FastAPI; the frontend Dockerfile is under `frontend/`. Do not deploy the root
  source as the web image. `cloudbuild-v7-preview.yaml` is a reusable two-image
  build configuration, but its old “deploy first” comment is obsolete for v3.
- [ ] Deploy the new API tag without traffic, then deploy `bills-voucher-web`
  with `--no-traffic --tag preview-v3`, pointing BACKEND_URL to the new API tag.
  Use project `aidirac-503309`, region `asia-south1`. Do not move `preview`,
  `preview-v2`, `api-preview`, `v7-api` or production traffic.
- [ ] Expected web URL (not live/verified yet):
  `https://preview-v3---bills-voucher-web-foovqasysa-el.a.run.app`.
- [ ] Verify login, CSRF, role permissions, cross-client 404s, template download,
  original-file isolation, exports, GCS/BQ roundtrip and live dashboard behavior.
  Never seed synthetic verification bills into the live Red Taxi client.
- [ ] Run the read-only frontend checks against the v3 URL. The upload browser
  test intentionally skips on a live URL to avoid writing mock customer bills.
- [ ] Compare Cloud Run traffic/tag mappings before/after and recheck original
  and v2 previews. Capture screenshots of GST Easy and Bills.
- [ ] Write `docs/releases/v7.md`: preview URL first, applied rename table, added
  routes, migration job ID, exact test counts, screenshots, limitations and
  decisions. Update this handoff with completed work and real deployment IDs.

## Existing deployments that must be preserved

| Target | Current revision at handoff |
|---|---|
| Original web tag `preview` | `bills-voucher-web-00036-zoq` |
| V2 web tag `preview-v2` | `bills-voucher-web-00042-joq` |
| Web production 100% | `bills-voucher-web-00027-67p` |
| Original API tag `api-preview` | `bills-voucher-00098-fim` |
| V2 API tag `v7-api` | `bills-voucher-00101-sip` |
| API production 100% | `bills-voucher-00084-5gr` |

Re-read Cloud Run state before future deployments; another operator may change it.

## Commands and test environment

Prefer a clean Python 3.12+ virtual environment with project/test dependencies.
This workspace used Python from another checkout and `.testdeps` for new PDF/Excel
packages. Do not commit local dependencies, browser results, cookies or credentials.

```powershell
python -m pip install -r requirements.txt
python -m pip install -e '.[test]'
python -m pytest tests -q
# In frontend:
npm ci
npx tsc --noEmit
npx playwright test --config playwright.config.ts
```

For local browser tests, start `uvicorn tests.gst.browser_backend:app --port 8103`
from the repository root and Next on port 3100 with
`BACKEND_URL=http://127.0.0.1:8103`. The harness uses in-memory data and fake local
auth; **never deploy or register it in the production application**.

For live read-only browser checks set `BV_TEST_URL`, `BV_TEST_EMAIL`, and
`BV_TEST_PASSWORD` through the environment. Do not put credentials in files.

`scripts/apply_v3_shell.py` and `scripts/centralize_gst_copy.cjs` are one-time
implementation helpers already run. Do not rerun blindly.

Decisions and constraints: `docs/decisions/v7.md`. Prior v2 release history:
`docs/v7-progress.md`.
