# Phase 06 — Canonical reporting evidence

Canonical search now uses tenant/period-scoped bill records, preserving statuses and linking to the individual review drawer. The live read-only assistant uses deterministic canonical financial summaries and bounded evidence retrieval when canonical bills are enabled. It does not combine legacy totals with canonical invoices and has no financial write tools. Ordinary search does not require Gemini. Synthetic customer context remains labelled synthetic.

Files: `app/gst/evidence.py`, GST workbench/search and assistant routes, `assistant.py`, frontend search links, workspace server routing and bill drawer deep links. Existing purchase-register exports, working papers and four cash scenarios remain.

Tests cover search status separation, evidence links, omitted private storage references and assistant source grounding. Full backend suite: 231 passed; Ruff/mypy/build pass. Live Gemini answers and genuine-client reporting have not been accepted. Query bounds cover the latest 500 bills for retrieval and up to eight selected documents in the assistant; this is not exhaustive retrieval.

No additional schema. Deployment must pair API/frontend. Roll back paired preview revisions; no data rollback is needed. Remaining: full reports/PDF coverage, all KPI drill-down/period filters, real-client tracing and accountant validation. Phase 06 is not fully accepted.
