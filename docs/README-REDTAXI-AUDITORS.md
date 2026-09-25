# Red Taxi GST Workspace — auditor guide

## Start with the demonstration

Open [Red Taxi September 2026 demonstration](https://preview---bills-voucher-web-foovqasysa-el.a.run.app/demo?scenario=redtaxi&period=2026-09). Sign in with your assigned account, then reopen this link if sign-in returns you to Overview. Do not share passwords in audit workpapers.

This is a demonstration prepared for Red Taxi Coimbatore. Every supplier, customer and amount in this view is fictional. It is not Red Taxi's accounts, return, GST liability or approved ITC position. GSTIN remains pending. The prominent synthetic-data banner must remain visible during presentations.

The Python generator produces 26 sample purchases, six sales invoices and a simulated GSTR-2B register. It includes reviewed purchases, pending review, unreadable evidence, supplier mismatches, blocked/deferred credit, a reversal example, common-use credit and non-GST fuel. The frontend and downloadable JSON use the same repeatable generator and seed.

## A ten-minute auditor walkthrough

1. **Dashboard:** explain recorded input tax, eligible credit, output tax, estimated cash and credit adjustments. Only sample purchases marked validated contribute to the synthetic Gold summary. Pending-review amounts are excluded.
2. **Documents:** open View on a servicing, insurance and fuel document. Inspect supplier, date, invoice number, taxable value, tax heads and total. PNG filenames describe planned example assets; images are not attached until separately generated. The displayed fixture is not an OCR result from an original bill.
3. **Filing:** inspect the per-invoice decision and rule reference, then compare matched, unmatched and amount-mismatch counts. Discuss why an accountant must resolve exceptions rather than approve all bills together.
4. **Sales / GSTR-2B:** inspect the fictional registers behind the demonstration. Sales tax adds up to the displayed output tax. These registers are not portal imports.
5. **Search:** try `servicing`, `insurance`, `diesel`, `Coimbatore` or an `RTX-DEMO` invoice number. Combine a review status and amount range. Open a result to inspect details.
6. **Assistant:** ask “Why is some credit deferred?”, “Which bills need review?” or “What is the sample cash required?” Check every answer against its source links. The assistant is read-only and cannot approve bills or submit a return.
7. **Download mock JSON:** retain the labelled demo file for training. It must never be imported into a live client account or presented as filing evidence.

## Generate the handoff pack

From the repository root on Windows:

```powershell
.\.venv\Scripts\python.exe scripts/generate_redtaxi_demo.py --period 2026-09 --seed 42 --output artifacts/redtaxi-demo-2026-09
```

The output directory contains `mock-data.json`, `sales.csv`, `gstr2b.csv`, `itc-decisions.csv`, `PNG-PROMPTS.md`, this README and a SHA-256 manifest. The script does not insert financial records, create images or change customer accounts. The web demo invokes the same generator; it does not read this local folder.

To generate other demonstrations use `scripts/generate_mock_data.py --scenario all`. The separate `rate_restricted` scenario demonstrates restrictions on input credit; do not assume the positive-credit Red Taxi illustration represents its chosen or legally applicable rate option.

## Create relevant PNG examples

Use one prompt from `PNG-PROMPTS.md` at a time in an image generation tool. Save the PNG with the exact filename in its prompt. Keep the visible “SAMPLE — NOT VALID FOR GST FILING” watermark. Never insert a real GSTIN, bank account, signature or payment QR code into a fictional invoice.

Verify invoice text and every amount against `mock-data.json`; image tools can alter characters and numbers. Fuel examples show no GST credit. A clean image does not resolve the fixture's GSTR-2B mismatch, rule exception or review state. Keep generated assets in a dedicated demo location such as `demos/redtaxi/2026-09/`, separate from live Bronze evidence. The application currently presents fixture details, not an image attachment viewer for demo PNGs.

## Onboard Red Taxi's actual records

1. Obtain authorised access and confirm the correct client is selected. Tax administrators manage GST settings and filing acknowledgements; client users upload/review records; viewers inspect only.
2. Confirm legal entity, GSTIN, state, monthly versus QRMP filing, relevant supply classifications, applicable tax-rate options and ITC restrictions with the responsible tax professional. Do not infer these from the mock dataset. The current profile view is read-only; the administrator profile API manages settings.
3. Choose the period in **GST Workspace**. Upload actual supplier bills in **Documents**. Preserve the originals. Review supplier GSTIN, invoice number/date, totals, tax split, line classification, duplicate warnings and extraction confidence before accepting a bill.
4. Import the actual sales and GSTR-2B records through **GST Filing & ITC**. The importer expects the application's normalised JSON structure, not arbitrary CSVs or every GST portal download format. Use the supported importer contract and verify counts and totals after import.
5. Run ITC computation, reconcile supplier differences and inspect every blocked/deferred/reversed line. Determine common-credit attribution with the preparer; retain the basis. Check all rules against the applicable period and taxpayer facts.
6. Review monthly, quarterly and financial-year views. Download working papers for the required scope, review checks.csv and reconcile the registers to source evidence. Missing records are not a nil declaration.
7. Independently verify the final return in the GST portal, pay any amount due and submit there. An authorised tax administrator can then record the ARN and filing date in the monthly preparation screen and lock the period. Record the actual acknowledgement only after submission.

## Current filing boundaries

- The tool prepares records, calculations and working papers. It does not submit GST returns or make payments. Current portal-upload JSON schemas are not verified.
- Quarterly reports aggregate monthly records; they are not a complete QRMP/IFF/payment workflow. Financial-year reports are review papers, not completed GSTR-9/GSTR-9C returns.
- Cash estimates exclude opening electronic credit/cash balances, payments, interest and late fees. Quarter/year cash estimates add monthly estimates without carrying credit between months.
- Composition, reverse charge, credit notes, amendments, exports and other special cases must be separately reviewed; the demonstration does not establish complete support for every return type.
- The 12% sales model in this sample is an arithmetic illustration, not advice on Red Taxi's tax rate or credit entitlement. All eligibility and rate choices must be confirmed before actual use.

## Audit evidence to retain

Keep source invoices, review decisions, GSTR-2B and sales extracts, reconciliation explanations, ITC calculation basis, downloaded working papers, final portal return, payment evidence and ARN. Download manifests help check file integrity; they do not establish that underlying records are correct or that a return was filed.

When an irrelevant test document is removed from the active workspace, retain its archive manifest and original evidence separately. Do not delete unrelated customer documents or whole GCS folders as part of demo preparation.
