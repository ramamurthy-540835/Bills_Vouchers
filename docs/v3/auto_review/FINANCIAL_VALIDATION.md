# Financial validation boundary
The canonical validator and Auto Review use Decimal. Auto Review independently calculates taxable value times rate, apportions tax heads, rounds to paisa, compares each head, sums lines and compares the invoice total exactly. The automatic path is stricter than existing manual tolerance. Original amounts are not silently corrected.

The canonical line model now optionally persists unit price, line discount and an explicit tax-inclusive or tax-exclusive price basis. When supplied together, Decimal arithmetic compares quantity times unit price, less the stated discount, with recorded taxable value. Incomplete or conflicting price evidence requires manual review; it is never silently corrected. Legacy invoices with no source-price evidence remain readable. The Bill Review form exposes the optional fields. Synthetic tests cover quantity mismatch, both price bases, mixed-basis lines and double rounding.

These arithmetic checks do not establish whether a discount or rate is legally applicable. Source-price extraction has not been measured against independently labeled documents. Freight, insurance, invoice-level discounts, advances, other charges and round-off remain outside the canonical valuation model. Do not approve automatic policies for those unsupported scenarios. The [CBIC invoice particulars reference](https://cbic-gst.gov.in/gst-invoice-rules.html) identifies invoice data fields; current effective-date notifications and professional review remain necessary for legal decisions.

Credit/debit notes, RCM, cess and corrected invoices are intentionally referred to manual review. Full requested source/extracted/calculated field lineage remains pending schema and review work. No financial formula or reporting aggregate was replaced.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
