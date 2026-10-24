# GST Easy V3 — Progress Report

**Date:** 24 October 2026

**Development branch:** `GST_NEW_V3`

**Latest application commit:** `f675d096ef7124a52f198f7373c12f8e9aa10ccb`

**Status:** Development progressing; Auto Review 2.0 is not fully accepted.

## Completed development

- Invoice Intelligence and the optional Auto Review policy support existing pending bills and future uploads. The default remains OFF; failed checks go to manual review.
- Added focused safety tests for tenant changes, revoked membership, duplicate originals, replay, failed extraction, saved-progress recovery and worker fencing.
- Added optional unit price, line discount and inclusive/exclusive price basis to canonical invoice lines. Supplied values are checked using Decimal arithmetic, with readable review reasons for conflicts. Legacy invoices without source-price evidence remain readable.
- Added PDF page-count evidence and conservative checks for repeated text-visible pages and distinct invoice numbers in one PDF. Original private evidence remains authoritative.
- Verified signed credit-note tax treatment and that three external app feeds stage records without automatically creating three canonical invoices.
- Updated the 108-scenario matrix: **81 partial deterministic/workflow contracts; 27 skipped**. Partial contracts are not legal or live OCR acceptance.

## Test evidence

| Check | Result |
|---|---|
| Backend pytest | 689 passed, 27 skipped, 6 warnings |
| Ruff | Passed for `app` and `tests` |
| Mypy | Passed for 91 application files |
| Frontend TypeScript | Passed |
| Next.js production build | Passed |
| Focused local Playwright | 1 passed: source-price save, refresh and responsive widths |
| Full browser regression for this commit | Not run |
| Live V3 acceptance for this commit | Not run |

Local screenshots: `artifacts/auto-review/source-price-1440.png` and `artifacts/auto-review/source-price-390.png`. The browser test used isolated synthetic localhost services. An earlier attempt against an older local server did not expose the new fields; the current-build rerun passed.

## Deployment status

The latest code is pushed to GitHub, **not deployed to Cloud Run**. A read-only check on 24 October found the public V3 web URL at `https://gst-easy-v3-web-foovqasysa-el.a.run.app`, serving revision `gst-easy-v3-web-00012-dar` at 100%. The V3 API serves `gst-easy-v3-api-00013-vaf` at 100%. Those revisions predate commit `f675d09`; the new valuation and PDF checks are not yet available on the public URL. No V2 or older service was changed by this development.

## Remaining work

The 27 skipped cases are listed individually in `100_SCENARIO_MATRIX.md` and grouped in `GAP_ANALYSIS.md`:

- Seven document-quality cases need an independently labeled PDF/image corpus and measured extraction against the configured provider.
- Twelve identity, special-document and GST-policy cases need verified, effective-date-aware source evidence and qualified tax review.
- Five advanced valuation cases need source-backed freight, insurance, discount and advance models with reviewed tax treatment.
- Three source-conflict and AI-grounding cases need independent evidence comparison and cross-source lineage.

Only nine of the requested 15 combined-fault tests have bounded contracts. Live Vertex reliability, representative load testing, and professional GST calculation acceptance also remain open. The new PDF text checks cannot identify conflicts hidden in an image-only PDF. Government filing remains disabled without authorized provider access and official acknowledgement.

## Next release gate

Complete the remaining engineering and evidence work, obtain specialist review for legal policies, run the full browser and live synthetic V3 acceptance suites, then build and test a V3 candidate revision. Promote only after release review. Do not label the 27 skipped cases complete merely because a fallback sends them to manual review.
