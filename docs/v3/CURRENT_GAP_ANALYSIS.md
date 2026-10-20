# Current V3 gaps

Baseline inspection: 20 October 2026; full acceptance has not run.

1. Email outbox conflates SMTP acceptance with delivery; no bounce/complaint event
   adapter or provider acceptance identifiers. Worker outcomes need tests for expired
   tokens, absent invitations, rejected recipients and retry exhaustion.
2. GST validation is arithmetic at declared rates, not an effective-date legal rate
   resolver. Inclusive pricing, discounts, cess basis and exceptional place of supply
   need explicit evidence and separate calculation contracts.
3. Canonical edits have version/audit controls but not a complete maker-checker
   adjustment proposal workflow. Original evidence must remain unchanged.
4. Document upload is not Vendor/Customer/Driver event staging. Trip/payment rows
   must never silently become taxable invoices.
5. BigQuery is used for identity and transactional guards. Latency targets remain
   unmeasured; concurrency correctness must not be traded for faster unsafe writes.
6. Rejected records have reasons and audit history, but correction/resubmission is
   not explicitly represented to users.
7. Return working papers are not certified official form exports. Synthetic-tenant
   restrictions must remain, and government submission is unavailable.
8. There is no approved external REST/MCP tenant connector or authorization service.
9. Most special taxpayer/forms/IMS/refund/notice/payment scenarios are reference or
   unimplemented scope, not production features.
10. All existing V2 tests must be separated from new V3 local/live/provider results.

No cloud resources have been mutated during this initial assessment.
