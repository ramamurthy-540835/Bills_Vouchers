https://preview-v3---bills-voucher-web-foovqasysa-el.a.run.app/gst/workspace?period=2026-09

# Isolated test workspace — 9 October 2026

The owner explicitly requested a separate test login and loading the previously generated fictional bill pack. The new user is linked only to a dedicated synthetic client; no membership in Red Taxi or any existing client was granted. Credentials are not stored in this repository.

The additive migration `infra/bq/migrations/008_test_client.sql` introduces `clients.is_test`. Existing clients retain NULL, which is treated as false. Test clients may upload, review and confirm their own test records so calculations can be exercised, but purchase-register exports, CA working papers, return JSON generation and filing transitions return 403 `sample_data_blocked`. A test marker cannot be changed through the ordinary account/profile form.

The fixture upload uses the actual v3 Bills API, GCS originals, Cloud Tasks worker, Vertex extraction and canonical BigQuery storage. Client identifiers remain parameterized and bill/profile writes retain permission checks. Account and initial membership creation were an explicitly authorized operator provisioning operation; the test user's global role is viewer and its sole scoped membership is client.

Deployment:

- Backend build: `3e90291f-1df0-400d-a568-aa00ff153c10` (SUCCESS).
- New v3 API revision: `bills-voucher-00110-wuv`, tag `api-preview-v3`, 0% production traffic.
- All web revisions, including v3, remain unchanged. Existing API tags and production routing were compared before/after and remain unchanged.
- Validation before deployment: 132 backend tests passed, including test-client export restrictions, filing restrictions and tenant isolation. Ruff and whitespace checks passed.

The local fixture folder is `C:\Users\BIS\Stephen\GST-V2\Dummy_Bills_V3`. Provisioning, processing progress, verification results and screenshots are kept there, outside Git. These synthetic results do not replace acceptance with genuine customer evidence and a verified real GSTIN.

## Default-month correction

Fresh login previously selected October while the dummy bills were dated September, leaving the dashboard empty. Test clients now default to their latest confirmed bill month (latest non-rejected month if none are confirmed). Explicit URL and session selections remain authoritative; ordinary clients retain the current-month default. Dashboard, bill listing and uploads share this selection rule, with a parameterized client filter.

- Build `8d7ebfe6-52e2-446a-bacb-3ab767f0dd50`: SUCCESS.
- API revision `bills-voucher-00111-viz`, tag `api-preview-v3`, zero production traffic. Other API tags and all web mappings verified unchanged.
- 139 backend tests passed before deployment; Ruff and whitespace checks passed.
- Live browser sign-in verified September 2026, 21 confirmed bills, 7 needing review and usable credit of INR 348,960.00. Bills returned 29 September records, and explicit April selection still returned its one confirmed bill.
- Local evidence: `Dummy_Bills_V3/demo-login-check.json`, `demo-fresh-login-fixed.png`, and `demo_period_deployment.json` (outside Git). The browser check allows asynchronous dashboard loading before asserting rendered values.
