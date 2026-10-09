https://preview-v3---bills-voucher-web-foovqasysa-el.a.run.app

# v7 preview progress

## Demo default month fixed - 2026-10-09

Fresh test-account login now opens the latest populated month, September 2026,
instead of empty October. Live browser sign-in and Bills navigation passed;
21 bills confirmed, 7 need review. Explicit month selections remain available.
139 backend tests passed. API revision `bills-voucher-00111-viz` updates only
`api-preview-v3`; production, original preview and v2 remain unchanged.

## Isolated test client — 2026-10-09

The owner requested a separate test account populated with the local dummy bill
pack. Added an explicit test-client flag and blocked exports/filing for that
client. API-only update: `bills-voucher-00110-wuv` on `api-preview-v3`, 0% traffic.
All web revisions and non-v3 API routing remain unchanged. 132 backend tests
passed. See [test workspace release note](releases/v3-test-workspace.md).

## V3 deployed — 2026-10-09

GST Easy and canonical bill uploads are live on isolated `preview-v3` and
`api-preview-v3` tags. Web revision: `bills-voucher-web-00050-rij`; API revision:
`bills-voucher-00109-quv`. Both have zero production traffic. Original and v2
tags and the current production revisions were verified unchanged.

129 backend tests, 3 local browser tests, 2 live browser tests, 6 live API smoke
groups and the live queue check passed. One synthetic-upload browser test was
intentionally skipped against the live customer. No mock financial records were
loaded. Full evidence and screenshots: [v3 release](releases/v7.md).
Remaining acceptance work: [handoff](STEPHEN_VERSION3_REMAINING.md).

The revision/traffic information below is historical; use the current release
report and fresh Cloud Run state for future deployments.

## V2 frontend update deployed — 2026-09-25

Following the owner's explicit GCP build instruction, deployed the accumulated
frontend changes to `preview-v2` only with `--no-traffic`. The two-line sample/rate
banner, profile notice and Overview introduction are removed. The top-right header
uses the unchanged `docs/Red taxi.png` asset. Overview amounts stay on one line.

- Build: `12b84f35-9469-4a22-a938-ad3cf1cff413` (SUCCESS).
- Image: `v7-preview-v2-20260925-r5`.
- V2 revision: `bills-voucher-web-00042-joq`.
- Original preview remains `bills-voucher-web-00036-zoq`; production remains
  100% on `bills-voucher-web-00027-67p`. Backend configuration is unchanged.
- Authenticated browser verification: four complete currency amounts fit within
  their boxes on one line at 10 viewport widths from 320 to 1440px. Logo loads and
  the requested notices/headings are absent. Evidence: `artifacts/v7/kpi-layout.json`
  and `artifacts/v7/overview-kpi-{1440,390}.png`.
- The broader page still has horizontal overflow at some tablet widths; KPI
  amounts fit. This verification does not claim the entire page is responsive.

The deployment and verification results below describe the earlier v7 release.

The owner subsequently requested separate old and new previews. The original
`preview` tag has been restored to `bills-voucher-web-00036-zoq`, with its original
`api-preview` backend. v7 now uses the `preview-v2` tag on
`bills-voucher-web-00040-sep`. Future v7 web deployments must use
`--no-traffic --tag preview-v2`; do not repoint `preview`.
The Cloud Run URL uses a hyphen: `preview-v2`.
Both URLs passed authenticated login, origin/CSRF and browser checks after the
split. The restored URL shows the original 22 posted seed examples; preview-v2
shows the new 120-purchase sample experience and blocks sample downloads.
Evidence: `artifacts/v7/preview-split.json`.

Deployed on 2026-09-25. Production traffic is unchanged. The initial deployment
preceded the requested test gates. A login import error caught by those gates was
corrected; the previous working preview was restored during the fix.

- Web preview-v2: `bills-voucher-web-00040-sep`, image `v7-preview-20260925-r4`.
- Backend: `bills-voucher-00101-sip`, image `v7-preview-20260925-r3`, tag `v7-api`.
  This configuration-only revision adds the preview-v2 origin for browser login and CSRF checks.
- Both deployments used `--no-traffic`; the current v7 web tag is `preview-v2`.
- Original preview restored: `bills-voucher-web-00036-zoq` with backend `api-preview`
  (`bills-voucher-00098-fim`). Its URL and deployment remain the pre-v7 version.
- Production remains 100% on web `bills-voucher-web-00027-67p` and API `bills-voucher-00084-5gr`.
- Backend configuration: `DEMO_FALLBACK=true`, `REQUIRE_OTP=false`.
- Additive account migration job: `e62e1f99-0430-4577-a531-85fbb099e4a5`.

The root Dockerfile builds FastAPI; the web Dockerfile is in `frontend`.
Cloud Build therefore built the correct images before image-based Cloud Run
deployment, instead of deploying the root backend image as the web service.

## Scope and sample behavior

The previous owner-authorized September mock load remains in BigQuery. v7 recognizes
its `synthetic_` run as sample data, overlays the new read-only 120-purchase fixture,
and blocks sample writes, downloads and filing. It does not load more mock records.
With DEMO_FALLBACK enabled, an empty Red Taxi period receives the same in-memory
fixture. A genuine summary takes precedence automatically. Other clients never
receive Red Taxi fixtures. The account and business profile remain editable under
membership permissions; financial sample records do not.

GST Workspace provides reporting views, checks and registers. GST Filing & ITC
provides import, calculation and filing transitions, so both navigation entries
are retained. No duplicate-page redirect is applicable.

## Benchmark references

- [ClearTax reconciliation](https://docs.cleartax.in/product-help-and-support/clear-finance-cloud/gst-compliance/gstr-2b-vs-pr-recon): show matching buckets and exceptions with their evidence.
- [Zoho Books GST](https://www.zoho.com/in/books/gst-accounting-software/): keep registration and return preparation understandable.
- [TallyPrime dashboard](https://help.tallysolutions.com/dashboard/): use compact financial summaries and period context.
- [Xero dashboard](https://www.xero.com/ae/accounting-software/dashboard/): prioritize headline figures and actionable records.
- [QuickBooks India](https://quickbooks.intuit.com/in): discontinued from July 2023; historical reference only, not a current Indian filing benchmark.

The implementation applies the requested spacing, typography, table and action
patterns; it does not claim identical features or tax filing parity with these products.

## Verification

- Full Python suite: 83 passed. The subsequently expanded v7 gate suite: 10 passed
  (three additional tests cover genuine-summary precedence, parameterized profile
  changes and the OTP-required stub).
- Ruff: passed. Mypy: passed for 44 source files. TypeScript: passed.
- Decimal/set-off checks: passed, including one interstate inward, two passenger
  vehicles, Rule 37, head totals and no CGST/SGST cross-utilisation.
- SQL lint: tenant-bound read/mutation checks passed. BigQuery dry-run compilation
  of the account profile transaction passed without executing DML.
- Live September and empty-August API gates: Overview, documents and GST Workspace
  populated with 120 purchases and 13 sales; sample labels and tenant IDs verified.
- Live working-paper, sample-pack and sample-evidence downloads return 403
  `sample_data_blocked`. JSON generation, validation and recomputation also return
  that code. Unauthorized client selection is denied and query overrides cannot
  switch the authenticated client.
- Desktop browser gates passed for Overview, Workspace, Documents, Filing, Account
  and Client profile. No client-name header block, role badge, sidebar footer,
  Umesh name or old GSTIN appeared. Account contact fields and last sign-in work.
- Mobile browser gate: bottom navigation visible, sidebar hidden, no horizontal
  overflow at 390px. The final deployed frontend also passed the targeted gate for
  a single GSTIN notice, Checked labels, account action placement and disabled
  sample controls; refreshed screenshots are saved.
- Production traffic checked after deployment; unchanged.

Evidence: `artifacts/v7/live-gates.json`, `final-ui-gates.json`, `overview.png`,
`gst-workspace.png`, `account.png`, and `mobile.png`.

## Account behavior

Business edits create a new profile version atomically and retain the previous
version. `can(user, 'edit_profile', client_id, repo)` checks membership and role.
Login email and Access level are read-only. Mobile numbers use E.164; OTP remains
an explicit stub, never a false verification claim. With REQUIRE_OTP enabled,
changing a number fails closed until OTP delivery is configured. GSTIN changes
require a tax administrator and validate format/checksum; they do not claim GST
portal verification. Missing contact details show an honest placeholder.

No live customer profile was altered merely to test the forms. SQL was compiled
in dry-run mode, and authorization/field validation were exercised in unit tests.
