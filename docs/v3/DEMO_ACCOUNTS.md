# V3 synthetic demo accounts

These accounts are separate from the existing V2 identities and records.
Passwords are supplied by the owner and stored only in separate V3 Secret Manager
secrets and application password hashes. Never put plaintext credentials in this
document, source control or execution reports.

| Identity | Purpose | Businesses |
|---|---|---|
| naturelabs1@demo.com | Preloaded synthetic invoice demonstration | Nature Labs Synthetic Manufacturing Pvt Ltd |
| naturelabs@demo.com | Manual synthetic upload testing, no preloaded financial records | Nature Labs Demo Manufacturing Pvt Ltd; Nature Labs Demo Trading Pvt Ltd; Nature Labs Demo Services Pvt Ltd |

The profiles and fictional logos were provisioned through existing application
services. All four businesses have is_test=true, SYNTHETIC_TEST_ONLY provenance
and gstin_verified=false. Both users have business-owner memberships, not platform
administrator rights. Operator activation does not set email_verified or
mobile_verified, and automatic registration mail to synthetic addresses is
suppressed.

Runtime activation requires the exact isolated V3 dataset, dataset prefix and
bucket, the explicit feature flag, the two allowed email identities, client role,
operator activation and synthetic provenance. V2's existing behavior is retained
in source but its branch and deployments are not changed.

The V3 release script validates all four expected demo memberships/profiles before
enabling their synthetic-only global inference access. Other customer businesses
remain excluded. Upload only synthetic documents into these demo workspaces.
Official filing and restricted financial exports remain disabled for test tenants.

Provisioning:

- `scripts/store_gst_new_v3_demo_passwords.py`: hidden-input Secret Manager storage.
- `scripts/provision_gst_new_v3_demos.py`: profiles, memberships and logos only.
- `scripts/populate_gst_new_v3_demo.py`: normal live upload, extraction, versioned
  review/confirmation/rejection and GSTR-2B import for naturelabs1 only.

The fixture period is October 2026. There are 23 original invoice identities:
20 intended confirmed documents, two review examples and one rejected example.
Expected values are in `demo bills/naturelabs1/EXPECTED_RESULTS.xlsx` and
`TEST_MANIFEST.json`. No dashboard totals are directly seeded.

October 2026 expected KPI values (INR for monetary rows):

| KPI | Expected |
|---|---:|
| Usable input credit | 5,781.60 |
| Sales GST liability | 23,960.16 |
| Estimated cash requirement | 18,178.56 |
| Purchases without ITC | 11,038.00 |
| Confirmed sales | 1,90,918.16 |
| Confirmed purchases | 93,874.72 |
| Pending reviews | 2 |
| Reconciliation mismatches | 3 |
| Unmatched invoices | 3 |

These use documented illustrative fixture rates and the existing application's
supported calculations. They are not a government filing or professional GST
acceptance. Test-tenant filing/export restrictions remain in force.

Application release: `ee2ae388c70ec5106a15477eabf7f02b42b02fc1`, Cloud Build
`e4f45dcf-54f7-4074-8294-708782d803da`. Ready revisions are
`gst-easy-v3-api-00006-g98` and `gst-easy-v3-web-00005-jbp`.
The release guard verified all 31 older service configurations and IAM policies
against their preservation baseline.

The first deployment attempt encountered Windows command-wrapper interpretation
of an environment-variable delimiter; no revision changed in that attempt.
The release now supplies a structured, nonsecret gcloud flags file. Existing
environment variables are preserved, and the corrected build/deployment passed.

Acceptance evidence:

- 509 backend tests, Ruff and mypy passed before release.
- Seven demo-isolation regression tests passed again after deployment (one local
  pytest cache-write warning).
- Two synthetic-pack tests passed against the current application calculations,
  reconciliation, grounded assistant and all nine report projections.
- Twenty targeted job-recovery, idempotency and evidence-retention tests passed.
  Warnings were dependency deprecations and the local pytest cache-write warning.
- Independent Decimal checks reconciled all 23 invoice/line totals and the
  confirmed purchase/sales expectations.
- Nine live public reachability/authentication-boundary checks passed, including
  private backend IAM and CSRF rejection.
- Manual account: real browser login, all three business profiles/logos,
  business switching, zero invoice counts, refresh and logout passed.
- Cross-business switching from the manual account to the preloaded account
  returned HTTP 403.
- Manual profile screenshots were captured at desktop and 390px mobile widths.
- Preloaded account: real browser login, its single authorized business, owner
  membership, website and logo passed. Desktop/mobile profile screenshots passed
  the no-horizontal-overflow check.
- Synthetic invoice uploads encountered BigQuery concurrent job-update aborts.
  Saved originals and extracted records were retained. Population uses the
  existing authenticated job retry mechanism with bounded attempts, respecting
  the 35-minute active-worker protection; it never resets claims directly.

Live acceptance completed on 20 October 2026. All 23 upload jobs completed, with
20 confirmed invoices, two pending-review examples and one rejected example.
All nine persisted KPI comparisons and report row counts passed, and all nine
report pages rendered in the live browser. Eight supported GSTR-2B records were
imported, producing 11 reconciliation cases. Search, the grounded pending-review
assistant answer, original PDF/PNG/JPEG byte checks, tenant restrictions, refresh
and logout passed. Both accounts' desktop/mobile layouts were inspected.

The extraction audit records 20 Gemini extractions and three manual-review
fallbacks. Fallback fields were completed from the original synthetic documents
through the versioned review API. No claim of universal AI extraction accuracy
or high-concurrency load readiness is made.

See [live acceptance](DEMO_ACCOUNTS_ACCEPTANCE.md) for actual financial values
and execution limitations. Sanitized local evidence is under
`artifacts/gst_new_v3/`; credentials are excluded.
