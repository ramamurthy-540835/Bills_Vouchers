# GST Filing & ITC Workbench — client guide

## Purpose

This workspace helps your finance team compare purchase bills with GSTR-2B, see the ITC that may be claimed, and understand the cash-flow impact before preparing returns. It supports review; it does not replace final advice from your GST practitioner.

## Production URL

Open the live GST Filing & ITC Workbench here:

https://bills-voucher-web-624683933018.asia-south1.run.app/gst/filing

The public application URL is:

https://bills-voucher-web-624683933018.asia-south1.run.app/

The backend service URL, used by the application and not intended for ordinary client use, is:

https://bills-voucher-624683933018.asia-south1.run.app/

## What you need before starting

- GSTIN, legal name, state, filing frequency, and authorised contact.
- Purchase-register export for the filing period.
- GSTR-2B download for the same period.
- Sales/output-tax totals and exempt-turnover total.
- Supporting bills, GRN/service acceptance, and payment status for unusual or high-value invoices.

## Sections in the workbench

| Section | What it does | Your action |
| --- | --- | --- |
| Client GST Profile | Stores the current GST registration profile | Check GSTIN, legal name, filing frequency and turnover details. |
| Purchase register | Lists your books-side inward invoices | Upload/confirm every invoice and tax amount. |
| GSTR-2B | Holds supplier-filed invoices | Import the matching period’s 2B file. |
| Reconciliation | Compares books and 2B invoice by invoice | Review mismatches and supplier follow-up items. |
| ITC Workbench | Applies ITC eligibility/reversal rules | Review blocked credits, deferred items and reversals. |
| Scenario comparison | Compares as-booked, 2B-restricted and compliant outcomes | Use this to understand working-capital impact. |
| Returns | Retains return-ready ITC runs and filing records | Review with your GST practitioner before export/filing. |

## Demo data included

The `gst-itc-demo` folder contains four fictional invoices and the matching 2B extract.

1. `DEMO-001` is a normal matched, eligible office-supplies invoice.
2. `CAR-017` is a Section 17(5)(a) passenger-vehicle example; it is blocked unless a documented exception applies.
3. `SVC-2026-09` is in books but absent from 2B; it is deferred in the compliant scenario.
4. `CAT-180` is unpaid for more than 180 days; it illustrates a Rule 37 reversal.

All names and values are illustrative. Do not treat the demo GSTINs or bills as real vendor evidence.

### Demo PNGs

| File | Use in the demo |
| --- | --- |
| [Input GST bill PNG](gst-itc-demo/input-gst-bill-sample.png) | Show the source bill fields that are captured: supplier GSTIN, invoice number, date, taxable value, CGST and SGST. |
| [Output ITC review PNG](gst-itc-demo/output-itc-review-sample.png) | Show how an invoice becomes matched, blocked, or deferred after 2B reconciliation and ITC rules. |

Both PNGs are fictional visual examples. They must not be presented as a client’s filed invoice, GSTR-2B, or tax return.

## Recommended monthly workflow

1. Select the correct client and filing period.
2. Confirm the GST profile. The GSTIN must pass format and checksum validation.
3. Load the purchase register and GSTR-2B for the same period.
4. Resolve invoice-number, date, and value mismatches with the vendor or bookkeeper.
5. Review invoices flagged as blocked, deferred, unpaid for 180+ days, or time-barred.
6. Compare scenarios. For client reporting, use the fully-compliant figure—not the as-booked figure.
7. Have the authorised reviewer approve the return workings before any filing action.

## Demo validation — exact steps

1. Open the [GST Filing & ITC Workbench](https://bills-voucher-web-624683933018.asia-south1.run.app/gst/filing) and sign in with an authorised demo account.
2. Select the demo client. Do not use a live client when presenting the fictional sample data.
3. In **Client GST Profile**, enter `27AAPFU0939F1ZV`. A valid result confirms the format, state code, PAN segment and checksum.
4. Change the final character to create `27AAPFU0939F1ZA`, then validate again. The expected error is `GSTIN_CHECKSUM_FAIL`.
5. Open [the input-bill PNG](gst-itc-demo/input-gst-bill-sample.png) and point out invoice `DEMO-001`, CGST `₹900.00`, and SGST `₹900.00`.
6. Load [purchase-register.json](gst-itc-demo/purchase-register.json) and [gstr2b.json](gst-itc-demo/gstr2b.json) into the corresponding demo/import flow.
7. Run the **Fully compliant ITC** scenario. Verify these outcomes:
   - `DEMO-001` is matched and eligible.
   - `CAR-017` is blocked under Section 17(5)(a), unless a supported exception is documented.
   - `SVC-2026-09` is deferred because it is absent from GSTR-2B.
   - `CAT-180` is reversed for the Rule 37 180-day payment condition.
8. Open [the output-review PNG](gst-itc-demo/output-itc-review-sample.png) to explain the matched, blocked and deferred buckets.
9. Compare **As-booked**, **2B-restricted**, and **Fully compliant**. For the client conclusion, quote only the fully-compliant amount after practitioner review.
10. End the demo by confirming that the returned result is a review aid. Do not file a GST return or upload client credentials during a demonstration.

## Reading the scenario table

- **As-booked:** book ITC before legal filters. Useful only as a starting point.
- **2B-restricted:** excludes invoices missing from 2B.
- **Fully compliant:** also removes blocked credits and recorded reversals.
- **Suppliers file late:** shows the potential cash-flow change if deferred invoices appear in 2B later.

## Controls and safety

- GSTIN failure messages include `GSTIN_CHECKSUM_FAIL`; correct the GSTIN before saving.
- Do not enter portal passwords in the application. They belong only in Secret Manager.
- A blocked-credit exception must have a business justification and supporting evidence.
- Return JSON should be reviewed and filed only by an authorised person.

## Help checklist

When seeking help, share the client code, filing period, invoice number, supplier GSTIN, screenshot of the reconciliation status, and the displayed request/run ID. Never share passwords, API keys, or Aadhaar/PAN scans in chat.
