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

Current acceptance: profile provisioning completed; 509 backend tests, Ruff and
mypy passed. Live activation, invoice processing and both-account acceptance are
recorded separately after execution.
