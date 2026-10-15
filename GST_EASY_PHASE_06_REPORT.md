# Phase 06 — Canonical reporting evidence

Canonical search now uses tenant/period-scoped bill records, preserving statuses and linking to the individual review drawer. The live read-only assistant uses deterministic canonical financial summaries and bounded evidence retrieval when canonical bills are enabled. It does not combine legacy totals with canonical invoices and has no financial write tools. Ordinary search does not require Gemini. Synthetic customer context remains labelled synthetic.

Files: `app/gst/evidence.py`, GST workbench/search and assistant routes, `assistant.py`, frontend search links, workspace server routing and bill drawer deep links. Existing purchase-register exports, working papers and four cash scenarios remain.

Tests cover search status separation, evidence links, omitted private storage references and assistant source grounding. Full backend suite: 231 passed; Ruff/mypy/build pass. Live Gemini answers and genuine-client reporting have not been accepted. Query bounds cover the latest 500 bills for retrieval and up to eight selected documents in the assistant; this is not exhaustive retrieval.

No additional schema. Deployment must pair API/frontend. Roll back paired preview revisions; no data rollback is needed. Remaining: full reports/PDF coverage, all KPI drill-down/period filters, real-client tracing and accountant validation. Phase 06 is not fully accepted.


## Reporting center - 15 October 2026

Implemented a Reports screen with month/quarter/Indian financial-year filters, refresh-persistent selection, 100-row pagination, invoice drilldowns and downloads. Purchase/sales registers separate confirmed directions and sign credit notes negatively; invoice listings include review statuses. Tax-head summaries, ITC decisions, two-sided reconciliation and scoped audit history are available in CSV/Excel. Tax summaries additionally export PDF. Existing working papers remain available. The dashboard cards link to their supporting reports.

Reports use canonical invoices only. Fingerprints are checked before/after generation to reject changing evidence; Excel includes source invoice IDs/versions and period fingerprints. Four cash scenarios remain independent and monthly calculations are not pooled into an invented carry-forward ledger. Full-register Unicode is preserved in CSV/Excel; PDF is intentionally a numeric tax summary with English labels. Formula-like cells are escaped, control characters preserved visibly and oversized fields/reports fail explicitly rather than truncate. Downloads are private/no-store and synthetic workspaces are blocked.

Implementation: app/gst/reports.py, the /api/gst/bills/reports route, frontend/app/reports-panel.tsx and reports/page.tsx, workspace navigation/server, dashboard drilldowns and proxy route. Dependencies add ReportLab >=4.4,<5; tested locally with 4.5.1. No schema migration or financial write. Existing API/frontend must be deployed together.

Verification: backend reports/API tests cover privacy, tenant boundaries, signed registers, four scenarios, unsupported formats, PDF parsing, stale evidence, formula escaping and report limits. Fifteen browser journeys pass, including direct-link filters, reload persistence, PDF download, empty sales and 390px layout. A selector-label failure was corrected with explicit accessible labels. Actual read-only BigQuery integration passed all seven kinds and cross-tenant audit isolation in gst_easy_bills_test_eb306dfe1e6b at 13:04 UTC. The generated synthetic PDF was rendered and visually checked. These are synthetic tests, not accountant acceptance.

Remaining: credit-ledger integration, genuine financial tracing and independent accountant acceptance, dashboard-wide quarter/FY calculations, broader report formats where needed, real assistant security/injection UAT. GST_EASY_AUDITOR_ACCEPTANCE.md provides the review matrix; the user has requested an auditor but no sign-off is recorded. Official GST adapters remain unverified and no report is labelled filing-ready.

Rollback: restore paired prior preview revisions and retain all source/audit data. No data rollback is required for this read-only feature. Deployment details and immutable images are recorded separately.
