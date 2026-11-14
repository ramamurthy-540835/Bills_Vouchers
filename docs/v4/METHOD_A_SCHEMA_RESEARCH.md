# GST Portal export schema research — V4 Method A

Review date: 14 November 2026
Scope: official public GST Portal tutorials accessible without taxpayer credentials. This is a technical capability review, not legal or GST-professional approval.

## Findings from primary sources

### GSTR-1

The GST Portal's current user guide describes both online preparation and a **PREPARE OFFLINE** path for uploading JSON prepared with the official offline tools. It also describes current portal sections and period-specific changes, so an exporter must be versioned and checked against the applicable filing period. The official Returns Offline Tool guide describes generating JSON and uploading it through the portal. This proves an official GSTR-1 offline JSON workflow exists; it does **not** prove that GST Easy's current CSV worksheets or any generated JSON conform to the current schema.

Sources:

- [Creation and Submission of GSTR-1](https://tutorial.gst.gov.in/userguide/returns/Creation_of_Outward_Supplies_Return_in_GSTR-1.htm)
- [Returns Offline Tool guide](https://tutorial.gst.gov.in/downloads/invoiceuploadofflineutility.pdf)
- [GST Portal downloads — Returns](https://www.gst.gov.in/download/returns) (the downloads page returned HTTP 403 to this unauthenticated research fetch; its current utility artifact was not inspected)

### GSTR-3B

The current GST Portal user guide describes preparing GSTR-3B online, reviewing generated values, making required entries, proceeding to payment/liability offset, and filing with DSC/EVC. The separate GSTR-3B offline-utility PDF discoverable in public search is explicitly dated 16 October 2017; it is not reliable evidence that a current GSTR-3B upload/import format is available or compatible.

Sources:

- [Create and Submit GSTR-3B](https://tutorial.gst.gov.in/userguide/returns/Create_and_Submit_GSTR3B.htm)
- [Legacy GSTR-3B Offline Utility PDF](https://tutorial.gst.gov.in/downloads/gstr3bofflineutility.pdf) (document metadata says last updated 16 October 2017; not used as a current schema)

### GSTR-2B reference data

The GST Portal FAQ says a taxpayer can view/download GSTR-2B in Excel and/or JSON after the statement is generated and lists normal, SEZ, and casual taxpayers as eligible viewing categories. GST Easy's current importer is narrower: it accepts its documented normalized JSON shape for supported B2B invoice sections, not arbitrary portal Excel or every GSTR-2B section. A successful import is not ITC approval.

Source:

- [View and Download GSTR-2B](https://tutorial.gst.gov.in/userguide/returns/FAQ_gstr2b.htm)

## V4 capability status

| Capability | Current status | Evidence / boundary |
|---|---|---|
| Internal GSTR-1 summary and guided worksheet | Implemented, locally tested | Included in the V4 Method A package. |
| Official GSTR-1 offline JSON export | Not implemented / not verified | Current portal schema/utility artifact was not available to this review; current app does not claim compatibility. |
| GSTR-3B preparation worksheet | Implemented as guided working paper | No current official import schema was established; taxpayer enters and verifies values on the portal. |
| GSTR-2B manual import/reconciliation | Partial, format-limited | Supported normalized JSON/B2B shape only; arbitrary portal downloads or unsupported sections must be normalized/blocked. |
| Portal login, payment, filing, OTP/DSC/EVC | Not implemented | Taxpayer completes these actions at gst.gov.in. |
| Acknowledgement verification | Not implemented | User-entered references/evidence are recorded as customer-reported and unverified. |

## What is required before claiming portal-compatible export

1. Obtain the current GST Returns Offline Tool and official schema/release notes from an authorized official source. The publicly reachable downloads page returned HTTP 403 in this review, so no schema file is checked into this repository.
2. Record the exact tool/schema version, applicable return type, form sections, effective period, and source URL/hash in a versioned schema registry.
3. Map approved canonical records to that schema using deterministic Decimal values and effective-period rules; reject unsupported return categories, sections, and missing fields.
4. Validate generated files against the acquired official schema and the corresponding official offline utility using synthetic fixtures. Retain validation fixtures and expected output without taxpayer identifiers.
5. Obtain a GST professional's review of table mapping, classifications, adjustments, and period applicability.
6. Only then expose a clearly named GSTR-1 offline JSON export. Keep GSTR-3B as online-entry guidance unless a current, independently verified import facility is demonstrated.

Until these prerequisites pass, V4 must continue to call its generated CSV/JSON/ZIP artifacts **guided worksheets / filing package**, never a GST Portal upload file. The live synthetic tenant's statutory package guard remains enabled.
