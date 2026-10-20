# Multi-source intake

The new `/api/gst/bills/intake` routes reuse selected-business membership and
bill-write permission. CSV, XLSX and JSON are bounded to 10 MB and 10,000 rows;
expanded XLSX is capped at 50 MB. Explicit column mapping is available in the API
and UI. Source columns are inspected before preview; ignored columns are visible.

Rows carry source identity/version, event type, references and Decimal text
amounts. Unknown fields are rejected rather than silently accepting tenant IDs.
Trip, payment and settlement events never implicitly create taxable invoices.
Preview quarantines malformed rows and identifies duplicate/conflicting source
identities. The original file is retained privately. Parameterized staging writes
are tenant-bound and serialized using the existing guard. Repeating the same
file/source/mapping returns the existing deterministic batch ID.

The batch and source-record tables are additive V3-only tables. History reads are
tenant-bound. Files retained before a failed transaction may be orphaned evidence;
no customer evidence is deleted to compensate.

Implemented: normalization, mapping API, preview, staging, history, source
provenance, within-batch duplicate/conflict detection and bounded inputs.
Cross-batch same/older versions are conservatively flagged duplicate_or_conflict.

## Exact reconciliation and evidence

The import-review UI exposes staged rows, an authenticated original-source
download, current-period reconciliation, saved snapshot history and authorized
canonical invoice links. Business/period changes remount this component so old
import results do not remain under a new context.

Identity requires supplier GSTIN, customer GSTIN, invoice number, financial year
and document type. Full comparison uses exact Decimal amounts and invoice date.
Missing identity, missing amounts, rejected/unreviewed invoices, duplicate
canonical candidates, superseded source versions and conflicting source payloads
remain explicit. No amount-only or fuzzy matching is performed.

Trip/booking references link events only through one fully matched canonical
invoice. Unresolved additional references and conflicting source records block
the link. Linking does not establish payment, ITC eligibility or tax liability.
Source-only invoices still require the existing upload/review workflow.

Snapshots bind tenant, batch, period, source hashes/versions, canonical source
fingerprint, actor and observation time. Concurrent canonical changes reject
the save. Snapshot IDs are deterministic; unchanged-input replays are idempotent.
Saved results are historical and visibly require rerunning after changes.
Limits: 20,000 relevant source-version rows, 10,000 canonical invoices and 5 MB
serialized evidence. Limits fail explicitly; no partial success is reported.

Migration: `migrations/v3_source_reconciliation.sql`, additive V3 ops table
`external_transaction_links`. No invoice or return tables are changed.

Real V3 BQ/GCS integration exercised synthetic source-only and ambiguous driver
reference results, retained originals and idempotent replays. Financial invoice
count stayed zero. This operator service test is separate from browser login
acceptance. Its first snapshot query failed because a conditional SELECT lacked
FROM; the corrected query passed against the actual BigQuery service.

Remaining: asynchronous large-job execution, explicit canonical promotion/review,
failed-row retries, approved compensation and 100,000-row acceptance. Exact
comparison is not completion of the entire financial consolidation workflow.
No canonical financial totals are changed by this intake.
