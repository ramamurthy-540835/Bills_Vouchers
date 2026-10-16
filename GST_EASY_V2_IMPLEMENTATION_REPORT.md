# GST Easy V2 implementation

Repository: https://github.com/ramamurthy-540835/Bills_Vouchers
Branch: GST-EASY-V2, created from f4f6d69 plus all current approved local edits. Historical 14 October handoff and snapshot reviewed; current source takes precedence.

## Latest scope
Only profiles, logos and memberships were provisioned. No financial invoices, GSTR-2B statements, ledger balances or dashboard figures were seeded. The generated upload pack is supplied for manual use. The requested weak password was rejected without weakening policy. The owner supplied an approved stronger password, stored through hidden input in V2 Secret Manager version 1.

## Implementation
Preserves latest registration, account, business, website/logo, navigation, dashboard, upload, reconciliation, returns and nine-report changes. Adds configurable canonical BigQuery dataset prefix (empty by default), private Cloud Run API invocation from server-only Next.js fetches, and narrowly scoped operator-activated synthetic demo identity. Email/mobile/GST verification flags are never fabricated. Operator identity is disabled by default, allowed only with all V2 resource settings and explicit synthetic user flags, and cannot become platform admin.

Read-only reports are enabled only for isolated V2 test tenants. Financial exports and filing restrictions stay enabled. A full browser test exposed and fixed website editor remounting after save, which erased its success notification.

Generator: scripts/generate_gst_easy_v2_demo.py. Pack: demo bills/. 28 business invoices x 3 formats, 18 edge cases, 3 supported B2B statements plus invalid duplicate statements, 3 fictional monogram logos, expected-results workbook and manifest. Rates are illustrative test assumptions; no legal classification or live government verification is asserted. Credit notes use positive face values and negative signed contributions. ITC requires actual review.

Infrastructure: scripts/prepare_gst_easy_v2.py creates new V2 resources and copies 62 existing TABLE schemas, not rows/views. Only nonfinancial serialization guards are inserted. Runtime IAM grants data access only to V2 datasets/bucket. Existing Cloud Run baseline and IAM snapshots are private ignored artifacts.

Provisioning: scripts/provision_gst_easy_v2_demo.py uses existing registration, business creation, versioned profile validation and logo normalization/audit. It refuses non-V2 settings, reads a numeric V2 Secret Manager password version, checks unchanged policy and refuses identity mismatch. It never imports invoices/statements.

Deployment: scripts/deploy_gst_easy_v2.py validates immutable image digests/build source and refuses pre-existing V2 services. Existing build YAML files are unchanged. New files: cloudbuild-gst-easy-v2-api.yaml and cloudbuild-gst-easy-v2-web.yaml.

## Pending acceptance
Demo account and three profiles have been provisioned and live sign-in verified. Live financial processing tests require manual uploads or a separately authorized disposable workspace; none may populate the three demo dashboards automatically. Email delivery is now configured using the existing approved Zoho sender and isolated V2 queue (see GST_EASY_V2_EMAIL_FIX.md). SMS and GSP providers remain unconfigured. No claim of real-client GST/filing certification.

Deployment follow-up: Windows command processing consumed the custom gcloud environment separator, causing proxy HTTP 503. Corrected the two new services using JSON environment files (valid YAML), and changed the deployment helper to use those files. Added actual runtime configuration verification. Application image source remains eaaabd8b7a21cff1d7d15e41fe9a1fe3cceb505e; subsequent commits contain release tooling/evidence only.
