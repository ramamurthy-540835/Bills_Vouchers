# GSTR-2B and IMS boundary

Preserve statement GSTIN, period, original provenance, import/version and matching
evidence. Existing parser support is bounded to its canonical supported contract;
unsupported portal sections must not be claimed reconciled.

Matching must distinguish books-only, statement-only, amount/head/GSTIN/date/number
differences, duplicates, credit notes and unresolved evidence. Missing statement
is not zero mismatches. Import does not approve ITC.

Internal reconciliation reviews are not submitted IMS decisions. Accept/reject/
pending/no-action portal semantics, recomputation and effective rules remain
subject to verified provider/schema integration. Live IMS submission is disabled.
