# GST policy and legal status
Only an explicitly approved, current tenant/supplier/recipient/HSN/direction/place-of-supply/document/rate policy can authorize automatic confirmation. Ambiguous, expired or missing policy evidence blocks it. No test policy is being represented as an official legal rule.

## Evidence gate added locally

The Auto Review policy evaluator now requires a reviewable HTTPS source on an official GST/Indian-law domain, a legal basis, source version, source-check date, policy identifier, reviewer and identity evidence. This is a provenance gate, not a legal conclusion: it prevents free-text or untraceable sources from authorizing automatic confirmation, but cannot establish that a policy is substantively correct.

Current source register for the implementation boundary:

| Scope | Official source | Use in GST Easy | Review status |
| --- | --- | --- | --- |
| Tax-invoice particulars / place of supply | https://cbic-gst.gov.in/gst-invoice-rules.html and CBIC Circular 90/09/2019-GST | Evidence and invoice-field review boundary | Requires effective-period specialist review |
| Valuation and discounts | https://cbic-gst.gov.in/pdf/e-version-gst-fliers/eflier-valuation-gst27062017.pdf | Manual-review boundary for unsupported valuation cases | Requires effective-period specialist review |
| GSTR-2B meaning and import boundary | https://tutorial.gst.gov.in/userguide/returns/FAQ_gstr2b.htm | Reconciliation/ITC context only; never an automatic ITC approval | Product behavior verified; legal eligibility review pending |

CBIC's compiled rules are convenience references and their own notice says Gazette notifications control. The policy register must therefore capture the applicable notification, effective period and reviewer decision before a live rule is activated.

Official sources consulted include the CBIC invoice rules, the CBIC valuation guidance and the GST portal GSTR-2B guide listed above. Rule 46/54 applicability, special supplies and Section 16/17 treatment still require an authorized specialist and effective-period sources.

The existing rate slab list is not an applicability registry. No statutory rates were added or certified. Live rules remain unseeded until separately reviewed. Legal acceptance is pending.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
