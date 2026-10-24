# Scenario coverage: 108 specified IDs

81 partial deterministic or workflow contracts passed; 27 explicitly skipped. Source-price, rounding, mixed-price, credit-note, external-feed and text-visible PDF safety cases now have bounded tests. No row claims complete end-to-end or legal acceptance. Machine-readable fields and test references are in tests/fixtures/auto_review/scenario_manifest.json.

| ID | Scenario | Actual test coverage |
|---|---|---|
| A01 | Clear complete PDF | NOT_IMPLEMENTED_SKIPPED |
| A02 | Blurry photograph | NOT_IMPLEMENTED_SKIPPED |
| A03 | Rotated invoice | NOT_IMPLEMENTED_SKIPPED |
| A04 | Low-light obscured totals | NOT_IMPLEMENTED_SKIPPED |
| A05 | Cropped totals | NOT_IMPLEMENTED_SKIPPED |
| A06 | Multi-page invoice | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| A07 | Multiple invoices in one PDF | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| A08 | Duplicate pages | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| A09 | Handwritten alterations | NOT_IMPLEMENTED_SKIPPED |
| A10 | Visible PDF conflicts with extracted text | NOT_IMPLEMENTED_SKIPPED |
| B01 | Missing invoice number | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| B02 | Missing invoice date | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| B03 | Invalid supplier GSTIN | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| B04 | Recipient GSTIN mismatch | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| B05 | Supplier/recipient reversed | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| B06 | Supplier name/GSTIN conflict | NOT_IMPLEMENTED_SKIPPED |
| B07 | Invoice date outside selected period | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| B08 | Missing place of supply | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| B09 | Invoice belongs to another business | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| B10 | Special invoice ordinary-field exceptions | NOT_IMPLEMENTED_SKIPPED |
| C01 | Correct taxable value tax and total | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| C02 | Wrong GST percentage | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| C03 | Correct rate wrong GST amount | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| C04 | Taxable plus GST differs from total | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| C05 | Quantity times unit price mismatch | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| C06 | Line totals differ from subtotal | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| C07 | Inclusive treated as exclusive | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| C08 | Exclusive treated as inclusive | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| C09 | Incorrect tax rounding | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| C10 | Unexplained total adjustment | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| D01 | Discount before tax | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| D02 | Unsupported post-tax discount | NOT_IMPLEMENTED_SKIPPED |
| D03 | Freight valuation mismatch | NOT_IMPLEMENTED_SKIPPED |
| D04 | Insurance handling mismatch | NOT_IMPLEMENTED_SKIPPED |
| D05 | Line and invoice discount conflict | NOT_IMPLEMENTED_SKIPPED |
| D06 | Double rounding | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| D07 | Mixed inclusive exclusive lines | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| D08 | Incorrect advance adjustment | NOT_IMPLEMENTED_SKIPPED |
| E01 | Approved HSN and rate | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| E02 | Invalid HSN | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| E03 | Multiple possible rates | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| E04 | Historical rate differs | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| E05 | Goods services classification | NOT_IMPLEMENTED_SKIPPED |
| E06 | Composite mixed supply | NOT_IMPLEMENTED_SKIPPED |
| E07 | Exempt supply charged GST | NOT_IMPLEMENTED_SKIPPED |
| E08 | Zero rated classification | NOT_IMPLEMENTED_SKIPPED |
| E09 | Composition charges GST | NOT_IMPLEMENTED_SKIPPED |
| E10 | Conditional rate missing evidence | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| F01 | Interstate IGST | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| F02 | Intrastate CGST SGST | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| F03 | Interstate uses CGST SGST | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| F04 | Intrastate uses IGST | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| F05 | CGST SGST split mismatch | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| F06 | Special service place of supply | NOT_IMPLEMENTED_SKIPPED |
| F07 | RCM treated normally | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| F08 | Missing incorrect cess | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| F09 | Export SEZ treatment | NOT_IMPLEMENTED_SKIPPED |
| F10 | Transport GTA ambiguity | NOT_IMPLEMENTED_SKIPPED |
| G01 | Correct credit note | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| G02 | Credit note positive invoice | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| G03 | Incorrect debit note adjustment | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| G04 | Credit original missing | NOT_IMPLEMENTED_SKIPPED |
| G05 | Credit exceeds adjustment | NOT_IMPLEMENTED_SKIPPED |
| G06 | Cancelled invoice dashboard | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| G07 | Edit after period lock | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| G08 | Previous financial year | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| H01 | Exact duplicate file | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| H02 | Rescanned duplicate | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| H03 | Changed filename | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| H04 | XLSX PDF duplicate | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| H05 | Same supplier number different FY | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| H06 | Different supplier same number | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| H07 | Three source duplicate | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| H08 | Rejected corrected resubmission | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| I01 | XLSX grouping | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| I02 | Inconsistent spreadsheet totals | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| I03 | Unsafe formulas | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| I04 | Unsafe ZIP | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| I05 | Corrupt protected original | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| I06 | Structured evidence conflict | NOT_IMPLEMENTED_SKIPPED |
| I07 | Missing original evidence | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| I08 | Retry duplicate insert | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| J01 | Matched invoice | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| J02 | Books only | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| J03 | Statement only | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| J04 | Amount mismatch | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| J05 | Credit note mismatch | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| J06 | Wrong statement period | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| J07 | Arithmetic correct blocked ITC | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| J08 | Punctuation probable match | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| K01 | Malformed AI JSON | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| K02 | Invented supplier | NOT_IMPLEMENTED_SKIPPED |
| K03 | Taxable total swapped | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| K04 | OCR decimal confusion | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| K05 | Model unavailable | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| K06 | Prompt injection | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| K07 | Models disagree | NOT_IMPLEMENTED_SKIPPED |
| K08 | Missing mandatory extraction | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| L01 | Business switched during upload | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| L02 | Membership revoked while queued | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| L03 | Retry after confirmation | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| L04 | Existing pending auto review | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| L05 | Confirmed read-only revalidation | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| L06 | Locked period | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| L07 | OFF while processing | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| L08 | Storage success DB failure | PASSED_PARTIAL_WORKFLOW_CONTRACT |
| L09 | Concurrent human auto confirmation | PASSED_PARTIAL_DETERMINISTIC_CONTRACT |
| L10 | Stalled external service | PASSED_PARTIAL_WORKFLOW_CONTRACT |
