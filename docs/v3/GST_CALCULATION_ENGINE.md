# GST arithmetic comparison

`app/gst/comparison.py` uses Decimal and ROUND_HALF_UP at two decimals. It
separates first extracted GST, current extracted GST, independently calculated
declared-rate GST and confirmed GST. First extraction is not authoritative
source-document truth. Original evidence is unchanged.

`price_breakdown` supports tax-exclusive and inclusive prices and discounts on
the same price basis. For an assumed test rate of 18%, 1180 inclusive yields
1000 taxable and 180 tax. This assumption is not a legal rate determination.
The invoice comparison applies recorded rates to recorded taxable lines,
compares heads and uses a one-paise comparison classification. Existing
confirmation validation remains authoritative and is not relaxed.

The UI exposes line comparisons, differences and qualifications. Missing state
or place-of-supply facts are insufficient data. Cess requires separate review.
No LLM calculates authoritative tax.

Implemented and locally tested: declared-rate arithmetic, inclusive/exclusive
breakdown, discounts, amount/head comparison, finite monetary inputs and
original-value preservation.

Not implemented as a certified legal engine: effective-date rate lookup,
transport exceptions, all place-of-supply exceptions, inclusive-price extraction
inference, statutory cess determination, materiality thresholds or approval of
arbitrary totals. Independent specialist review remains required. The comparison
endpoint must not be represented as automatic legal approval or filing readiness.
