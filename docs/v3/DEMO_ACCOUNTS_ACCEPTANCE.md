# V3 demo account live acceptance

Observed: 2026-10-20T15:19:51.164751+00:00

URL: https://gst-easy-v3-web-foovqasysa-el.a.run.app/login

| Account | Verified state |
|---|---|
| naturelabs1@demo.com | One synthetic manufacturing business; 23 retained original invoices; 20 confirmed, two needing review, one rejected |
| naturelabs@demo.com | Three configured synthetic businesses; zero invoices in each |

Both accounts passed real browser sign-in using the owner-supplied credentials.
Credentials are stored in separate V3 Secret Manager secrets and password hashes;
no plaintext credentials are included here. These are synthetic operator-activated
accounts, not claimed mailbox-verified identities.

## Persisted October 2026 KPI comparison

| KPI | Expected | Actual |
|---|---:|---:|
| eligible_credit | 5781.60 | 5781.60 |
| output_tax | 23960.16 | 23960.16 |
| cash_required | 18178.56 | 18178.56 |
| non_gst | 11038.00 | 11038.00 |
| confirmed_sales | 190918.16 | 190918.16 |
| confirmed_purchases | 93874.72 | 93874.72 |
| pending_reviews | 2 | 2 |
| reconciliation_mismatches | 3 | 3 |
| unmatched_invoices | 3 | 3 |

All nine Decimal comparisons passed. Totals were produced by normal application
calculations from persisted, reviewed synthetic invoices; no dashboard totals were seeded.

## Live checks

- All 23 upload jobs completed; PDF, PNG and JPEG original-byte checks passed.
- All nine dedicated reports rendered and matched expected API row counts.
- Synthetic GSTR-2B imported; 11 reconciliation cases were returned.
- Invoice-number search and grounded pending-review assistant answer passed.
- Business profiles, logos, desktop/mobile layouts, refresh and logout passed.
- Cross-business access attempts were denied; test export restrictions remained enforced.

## Execution and limitations

Recorded local checks: 509 backend tests before release, Ruff and mypy passed.
Targeted reruns passed: seven isolation tests, two fixture tests and 20 recovery/evidence tests.
Nine live public/authentication boundary checks passed. Dependency deprecation and local
pytest-cache warnings were recorded separately; they did not fail tests.

Upload/job writes encountered BigQuery transaction conflicts. Saved progress was recovered
using the authenticated retry workflow, including the existing 35-minute worker-claim timeout.
This demonstrates successful recovery, not a claim of high-concurrency load readiness.
The extraction audit records 20 Gemini extractions and three manual-review fallbacks.
Fallback records were completed from original synthetic evidence through the normal
versioned review API; this is not a claim that AI extracted every document successfully.
No real government verification or filing was performed. Illustrative GST fixture rates
remain subject to the documented test assumptions.

## Deployment and preservation

Application source: `ee2ae388c70ec5106a15477eabf7f02b42b02fc1`.
Cloud Build: `e4f45dcf-54f7-4074-8294-708782d803da`.
API revision: `gst-easy-v3-api-00006-g98`.
Web revision: `gst-easy-v3-web-00005-jbp`.
The guarded release and subsequent read-only preservation check passed for all 31
older service configurations/IAM policies. V2 and older customer data were not provisioned.

Screenshots and sanitized detailed JSON evidence: `artifacts/gst_new_v3/`.
Synthetic fixture files: `demo bills/naturelabs1/`.
