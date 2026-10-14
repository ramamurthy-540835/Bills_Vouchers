# GST Easy gap analysis

Audit date: 14 October 2026. Branch: GST_EASY in the existing Bills_Vouchers repository. Starting commit: 6c4879c5fc2deabf7fb7956be86dc73c7e4ff142. October working changes are preserved and staged separately from subsequent changes.

## Evidence and architecture

Reviewed the handoff narrative and machine-readable snapshot in ../Reports, frontend/AGENTS.md, installed Next.js client component guidance, current authentication, account, invoice upload, job, template and calculation code, and executed the baseline checks. The handoff is historical evidence; it is not acceptance of current production readiness.

Browser -> Next.js same-origin API proxy -> FastAPI -> BigQuery/GCS. Cloud Tasks runs canonical invoice extraction with Vertex AI. Backend role and active membership checks must remain authoritative.

| Data path | Source | Intended authority |
|---|---|---|
| Legacy accounting | app/routes.py, app/repository.py; finance_analytics accounting/document tables | Legacy journals and document screens only |
| Medallion | app/services/gst; finance_analytics bronze/silver/gold tables | Existing separate filing workflow; not implicitly canonical |
| Canonical GST Easy V3 | app/gst, app/routers/gst_bills.py; gold.gst_invoice, silver.gst_invoice_line, silver.gst_bills_gstr2b, ops job/audit/lock tables | Current Bills and GST Easy calculations |

Do not aggregate the three paths together. Canonical calculations use confirmed non-sample invoices and four independent cash scenarios. Broader GST correctness requires current official specifications and accountant-approved examples.

## Highest priority gaps

1. Registration currently authenticates immediately without email ownership verification. Mobile registration, provider-backed OTP, password recovery and distributed throttling are absent.
2. Legacy /signup grants global administration in development. Disable this alternate path.
3. Password inputs lack visibility controls; bcrypt encoding/length boundaries need explicit validation.
4. Canonical bills do not enforce medallion filing-period locks. Delete preserves stored evidence but has no approved restore workflow. Rejection lacks mandatory reason.
5. GSTR-2B matching covers a limited B2B subset; full amendment, credit-ledger and carry-forward acceptance is outstanding.
6. Canonical return preparation needs its own reviewed authority, immutable approval snapshot, universal locks and verified export adapters.
7. Private logo upload exists, but removal and versioned logo audit are incomplete. Invitations/onboarding are incomplete.
8. Backup restoration, load targets, IAM least privilege and genuine client UAT are not demonstrated by local unit tests.

## Cloud evidence

Read-only Cloud Run inspection on the audit date confirms API api-preview-v3 -> bills-voucher-00113-leg and web preview-v3 -> bills-voucher-web-00052-wuc. Production remains 100% on bills-voucher-redtaxi-account and bills-voucher-web-public-redtaxi-api. Other preview tags remain present. No deployment or traffic mutation occurred during this audit.

Full live BigQuery schema/IAM, bucket retention, task queue configuration, Vertex configuration and image provenance audit remain pending. Do not describe Phase 00 as fully accepted until these are recorded.

## Migration and rollback boundaries

infra/bq/migrations/007_gst_invoice.sql is the canonical schema; migrations/007_v5_medallion.sql is a separate schema. migrations/009_v7_account.sql adds account/mobile fields. Review additive migrations individually; never execute historical seeds as a migration batch. Local changes can be reverted by reviewed commit after preserving subsequent work. There is no cloud rollback needed for this audit because no deployment or schema change was applied.
