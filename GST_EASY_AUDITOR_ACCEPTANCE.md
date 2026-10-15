# Auditor acceptance pack - 15 October 2026

Status: awaiting independent auditor validation. The owner has requested an auditor to check accuracy. No accountant sign-off is recorded.

## Review procedure

Use an authorized real business workspace and evidence the business has permitted for testing. Keep source documents private. Register/verify the auditor through normal ownership and invitation flows; assign only the needed accountant/tax-administrator role. A different authorized person must approve prepared returns.

For each selected month, use Reports to export the purchase register, sales register, invoice listing, tax-head summary, ITC decisions, reconciliation and audit history. Excel includes source invoice IDs, versions and period fingerprints. Tax summary also supports PDF; CSV/Excel preserve register text, including Unicode names. Amounts are exported as decimal text to preserve precision. Confirm negative credit-note signs before importing into other spreadsheets.

Open source invoice IDs in Bills and compare originals, corrections and review history. Obtain the genuine GSTR-2B source from the business, import only supported B2B records and inspect every mismatch. Unsupported sections must not be discarded to force an import. Treat review acknowledgement as workflow evidence, never approval of ITC by itself.

Independently calculate taxable amounts, tax heads, eligible/ineligible ITC and payable amounts using the applicable verified rules. Compare all four cash scenarios separately. Quarter/year reports retain monthly calculation boundaries; opening credit/carry-forward is not implemented, so they are not a certified period ledger.

## Required evidence matrix

For every case record: source invoice IDs/versions, statement source hash, expected figures, application figures, difference, applicable official rule/version, reviewer, review date and pass/fail with reason.

- Intrastate purchase and sale: CGST/SGST and invoice totals.
- Interstate purchase and sale: IGST and permitted set-off.
- Exact matching and deliberately mismatched dates/tax values.
- Repeated file, repeated business invoice and simultaneous uploads.
- Credit/debit notes and amendments: verify support before acceptance; broader statement adapters remain pending.
- ITC eligibility facts, restricted categories and missing evidence.
- Opening credit, reversal, reclaim, utilization and closing carry-forward: blocked until ledger implementation and acceptance.
- ECO/RCM where relevant: verify classification, payment evidence and cash-only requirements.
- Delete/restore/reject effects, locked-period denial and reopened corrections.
- Same-data report refresh, changed-source snapshot denial and maker-checker role separation.
- Genuine upload/extraction/recovery and cross-tenant denial.
- Official GSTR-1/GSTR-3B export/validator acceptance: blocked until verified adapters exist.

## Sign-off record

Supported business/return scope:
Evidence period and record IDs:
Independent expected-results attachment:
Rule/schema versions checked:
Known unsupported cases:
Material differences and resolutions:
Auditor name/qualification/date:
Auditor decision and reasons:
Owner acceptance/date:

Leave these fields blank until an actual reviewer supplies evidence. A synthetic test, successful build or generated report is not an accountant approval.
