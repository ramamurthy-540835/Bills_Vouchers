# Nature Labs 1 test results

## Local automated gates

- Full pytest: 429 passed. Existing dependency deprecations and pytest cache-permission warning recorded.
- Ruff app/tests: passed.
- mypy app: passed, 80 source files.
- Frontend TypeScript: passed.
- Next.js production build: passed.
- Playwright local regression suite: 74 passed; includes synthetic tenant permissions, uploads, PDF/image previews, reports, profile management and mobile layouts.

## Actual live acceptance

No mocked network responses were used. See `artifacts/gst_easy_v2/naturelabs1-processing.json` and `naturelabs1-acceptance.json` for actual API outcomes and AI responses. Screenshots: `artifacts/gst_easy_v2/naturelabs1-*.png`.

## Issues found and corrected

- New demo identity required explicit V2-only operator activation; it remains unverified for email/mobile ownership.
- Customer names were absent from canonical search text; recipient names/GSTINs are now included in the already tenant-scoped adapter.
- The assistant lacked confirmed sales/purchase totals; it now receives signed confirmed-only Decimal aggregates.
- The extraction prompt assumed purchase bills. Direction and note type are now required, with selected-business context. Existing validation caught the misclassified sale; authorized review corrected it before confirmation.
- The first unmatched-invoice AI answer repeated line items and treated an unsupported credit note as unmatched. The assistant now receives actual deduplicated reconciliation cases. Simple pending-review and unmatched-purchase questions are answered directly from authoritative status classifications, excluding rejected bills and amount mismatches; live semantic checks were rerun. Synthetic labeling is enforced in responses.
- A live GET connection reset interrupted report verification; safe reads were retried without re-uploading completed invoices. A browser network-idle wait timed out; visual verification uses actual component readiness instead. Sign-in test retries exposed a pre-hydration interaction race; the harness now verifies the password toggle responds before entering credentials, and live login passed.

- login: True.
- profile_owner_website_logo: True.
- client_account_navigation: True.
- persisted_status_counts: recorded in sanitized acceptance JSON.
- report_page_usable-itc: True.
- report_page_gst-liability: True.
- report_page_cash-requirement: True.
- report_page_purchases-without-itc: True.
- report_page_pending-reviews: True.
- report_page_reconciliation-mismatches: True.
- report_page_unmatched-invoices: True.
- report_page_sales-register: True.
- report_page_purchase-register: True.
- report_search_and_period_filters: True.
- page_/settings/me: True.
- page_/settings/account: True.
- page_/settings/password: True.
- page_/settings/profile: True.
- page_/help: True.
- page_/search: True.
- page_/assistant: True.
- page_/gst/filing: True.
- search_NL1-P-001: recorded in sanitized acceptance JSON.
- search_Fictional Supplier: recorded in sanitized acceptance JSON.
- search_Fictional Customer: recorded in sanitized acceptance JSON.
- pending_search: True.
- amount_search: True.
- all_originals_accessible: True.
- duplicate_invoice_prevented: True.
- foreign_business_switch_denied: True.
- foreign_invoice_and_original_denied: True.
- restricted_/api/gst/bills/export?period=2026-10: 403.
- restricted_/api/gst/returns/working-paper?period=2026-10: 403.
- synthetic_return_preparation_blocked: True.
- duplicate_statement_rejected: True.
- repeated_statement_import_denied: True.
- wrong_statement_period_denied: True.
- wrong_statement_gstin_denied: True.
- return_status_loaded: True.
- assistant_What are our total confirmed sales?: recorded in sanitized acceptance JSON.
- assistant_What is our usable ITC?: recorded in sanitized acceptance JSON.
- assistant_Which invoices need review?: recorded in sanitized acceptance JSON.
- assistant_Which purchase invoices are unmatched?: recorded in sanitized acceptance JSON.
- assistant_What is the estimated GST cash requirement?: recorded in sanitized acceptance JSON.
- read_only_assistant_preserved_invoices: True.
- responsive_1440: True.
- responsive_900: True.
- responsive_390: True.
- mobile_report_navigation: True.
- original_preview_1440: True.
- original_preview_390: True.
- refresh: True.
- logout: True.
- logged_out_denied: True.
- assistant_reconciliation_corrected: True.
- profile_logo_rendered: True.

## Nine report data checks

- credit: 20 actual report rows; export allowed: False.
- liability: 10 actual report rows; export allowed: False.
- cash: 16 actual report rows; export allowed: False.
- without_itc: 8 actual report rows; export allowed: False.
- pending: 2 actual report rows; export allowed: False.
- mismatches: 3 actual report rows; export allowed: False.
- unmatched: 3 actual report rows; export allowed: False.
- sales: 10 actual report rows; export allowed: False.
- purchases: 10 actual report rows; export allowed: False.

## Known restrictions and blocked actions

- Synthetic test rates and HSN assignments are assumptions, not certified tax advice. GSTIN-like identifiers are fictional fixtures, not government-verified registrations or proof of ownership.
- B2B-only statement parser: the purchase credit note is an unsupported reconciliation case, not a matched portal credit note. A duplicate-candidate statement is rejected, never persisted as a fake match.
- Existing synthetic-tenant restrictions block real return preparation, approvals, filing and financial exports. Read-only reports and calculations work; these restrictions were not bypassed.
- Email and mobile verification remain false. This explicit V2 operator-activated identity is not ownership/KYC verification.
- Local browser tests use designated synthetic fixtures; live evidence is recorded separately. Password changes, account deletion and production filing were not performed during live acceptance.
- AI is read-only and model-generated; cited evidence remains the authority. Search is bounded to the latest 500 canonical records per business/period.

Live AI limitations: []
