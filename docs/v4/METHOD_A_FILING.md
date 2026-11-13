# GST Easy V4 — Method A filing workflow

## Purpose and statutory boundary

GST Easy prepares and checks a return package. A taxpayer signs in to the official GST Portal, verifies the current values, completes any required payment/liability offset and files there. GST Easy does not log into GSTN, submit a return, perform OTP/DSC/EVC, pay tax, or verify an acknowledgement. Downloading an export or recording payment is not filing.

## Workflow in V4

1. Select the business and return period.
2. Review and confirm the applicable invoice records and imported GSTR-2B reconciliation.
3. Use **Validate return**. The API checks profile/GSTIN format, supported regular-taxpayer category, invoice review state, selected period, and current reconciliation blockers. Warnings remain visible; they are not represented as legal advice.
4. Prepare the source-fingerprinted snapshot, submit it for maker-checker review, and approve it with a different reviewer.
5. Download the approved filing package. The package contains the immutable snapshot, validation/reconciliation output, GSTR-1 sales-entry worksheet, purchase/ITC review worksheet, GSTR-3B entry worksheet, checks, readme, and per-file SHA-256 manifest.
6. Open `https://www.gst.gov.in/`, confirm applicability and current portal data, complete statutory steps, and file.
7. Upload optional supporting acknowledgement evidence and record the reference/date. GST Easy stores an audit event with status `customer_reported_unverified`; that status is not changed to `filed`.

## Export compatibility

The current package is deliberately a human-guided working package, not GSTN JSON. The GST Portal tutorial describes GSTR-1 offline JSON prepared with its utility/compatible schema; a current schema/version compatibility test has not been completed for this V4 source. Therefore V4 does not label its worksheets as portal-importable. GSTR-3B is presented as a guided worksheet because no compatible import schema was verified for this implementation. Re-check official portal requirements before every filing period.

## Evidence and permissions

- Preparation requires a current profile and canonical invoice data; sample workspaces are blocked from statutory package/evidence actions.
- Approval remains maker-checker and source-version aware.
- Evidence uploads use the existing authenticated, tenant-scoped private object store and a digest-derived idempotency reference.
- Filing package and customer-evidence events are written to the return audit table scoped by client and snapshot.
- Customer-provided references/files are never called GSTN-verified.

## Verified official guidance

- [GST Portal: Creation of Outward Supplies Return in GSTR-1](https://tutorial.gst.gov.in/userguide/returns/Creation_of_Outward_Supplies_Return_in_GSTR-1.htm)
- [GST Portal: Create and Submit GSTR-3B](https://tutorial.gst.gov.in/userguide/returns/Create_and_Submit_GSTR3B.htm)

These references explain portal workflows; they do not certify this application’s calculations or imply that this package is an official upload format.
