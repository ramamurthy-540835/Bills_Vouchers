# Financial validation boundary
The canonical validator and Auto Review use Decimal. Auto Review independently calculates taxable value times rate, apportions tax heads, rounds to paisa, compares each head, sums lines and compares the invoice total exactly. The automatic path is stricter than existing manual tolerance. Original amounts are not silently corrected.

The canonical line model does not yet persist unit price, discount, inclusive/exclusive basis, freight, other charges or round-off. Complete quantity-times-price reconciliation and these advanced valuations are NOT IMPLEMENTED in this release. The existing comparison utility has isolated inclusive/exclusive and discount tests; that is not end-to-end invoice valuation support. Do not approve policies for unsupported valuation scenarios.

Credit/debit notes, RCM, cess and corrected invoices are intentionally referred to manual review. Full requested source/extracted/calculated field lineage remains pending schema and review work. No financial formula or reporting aggregate was replaced.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
