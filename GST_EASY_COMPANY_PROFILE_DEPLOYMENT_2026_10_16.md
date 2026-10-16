# Company profile preview deployment — 16 October 2026

Application source: 378d3b67ae966203ef7de2ec3a87cb8adc432889, pushed to GST_EASY in the existing Bills_Vouchers repository.

Frontend: https://gst-easy---bills-voucher-web-foovqasysa-el.a.run.app

API: https://gst-easy---bills-voucher-foovqasysa-el.a.run.app

| Component | Successful build | Preview revision | Immutable SHA256 |
|---|---|---|---|
| API | 848a2cfc-cfd0-4382-a684-c9b5ae9c8bc3 | bills-voucher-00123-hol | 95dad57117e84b270c684df40a51356ef461298f0f228282074d6a4ecc3ceb74 |
| Frontend | 60e84db3-f354-448b-982d-799b35906d79 | bills-voucher-web-00060-nuy | 00380ac66d79ab5754eb45cb886d21551cd2e31150884661a7510c005421e357 |

Both deployments used --no-traffic and updated only gst-easy tags. Before/after routing comparison passed. Production remains 100% on bills-voucher-redtaxi-account and bills-voucher-web-public-redtaxi-api. Other preview tags were unchanged. Frontend uses gst-easy-web-preview@aidirac-503309.iam.gserviceaccount.com with no direct project roles. API remains on the shared identity documented in the production gap review.

Predeployment checks: 332 backend tests, Ruff, mypy (74 files), frontend production build and 17 local browser scenarios passed. Actual isolated BigQuery profile-version/audit integration passed. Migration 016 was applied additively; no genuine company record was created or modified.

Live smoke at approximately 02:14 UTC passed: public authentication pages, API health/readiness, rejection of invalid administrator credentials, unauthenticated bills/reconciliation/returns/membership/reports/dashboard access and internal worker access. Desktop and 390px browser checks passed registration fields, password visibility, separate admin/client navigation and overflow checks. Empty registration reached expected mobile validation (422), with no account creation or email sent. These checks do not constitute authenticated customer or mailbox-delivery acceptance.

Existing monitoring dashboard 156a57ed-0435-4575-8ff9-253faae16f1f now tracks the two new revisions. Notification channels were unchanged. JSON evidence and screenshots are retained locally in artifacts/gst_easy.

Rollback: inspect current routing, then move only gst-easy API and web tags to bills-voucher-00122-fof and bills-voucher-web-00059-cij respectively. Preserve production percentages and every other tag. Retain website_url, profile versions and audit history. Old code does not include the new legacy-profile security hardening; assess that consequence before reverting.

Production readiness remains blocked as detailed in GST_EASY_PRODUCTION_GAP_REVIEW_2026_10_16.md. Government verification is explicitly not connected; no provider contract, company GSTIN, website ownership, customer-specific bucket or production release approval was fabricated.
