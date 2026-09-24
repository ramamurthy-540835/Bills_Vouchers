# Mock customer data and conversational assistant

Use **Demo workspace** in the navigation (or `/demo`). It has Dashboard, Documents, Filing, Search and Assistant tabs. The persistent banner identifies all figures as synthetic. Live Overview continues to use the selected customer's Gold records.

## Generate JSON with Python

From the repository with its Python dependencies installed:

```powershell
.\.venv\Scripts\python.exe scripts/generate_mock_data.py --scenario all --period 2026-09 --seed 42 --output artifacts/mock-data.json
```

The reusable function is `generate_mock_data(scenario, period, seed)` in `app/services/gst/mock_data.py`. It returns synthetic documents, lines, reconciliation rows, a Gold ledger and summary, plus the dashboard payload. The same function supplies the frontend; the downloaded JSON and generated JSON use the same underlying examples. No credentials, BigQuery writes, storage uploads, memberships, or real GSTINs are required. Repeatable seeds and explicit periods make results reproducible. Monetary values are Decimal-derived strings. Gold summary/ledger records are calculated before dashboard presentation; review/failed documents never contribute to Gold.

The current 15 scenarios cover mixed states, eligible purchases, an empty period, review, failed extraction, unmatched GSTR-2B invoices, amount differences, blocked credit, overdue-payment reversals, common-credit adjustments, fuel/non-GST purchases, ECO liability, rate restrictions, locked filings and a 120-invoice pagination case. These are representative supported cases, not a claim to cover every statutory/business situation. Synthetic invoice details are viewable, but no counterfeit original bill files are generated.

Search supports multiple text terms, supplier, invoice number/date, filename, status, decimal amount ranges and pagination. Live search is explicitly bounded to the latest 500 documents for the selected customer/period. Mock search covers the complete chosen scenario. The browser's **Download mock JSON** downloads the selected scenario.

## Assistant

`/assistant` answers using the selected real customer's period. The Assistant tab under `/demo` uses only that scenario's synthetic records. The Python implementation is `app/services/gst/assistant.py`; it calls the configured Gemini model through the existing Vertex AI/API-key configuration. A live Gemini synthetic-data check is separate from the stubbed local browser test.

Financial totals are supplied from the Gold dashboard. Source evidence includes a bounded selection of eight relevant invoices and their validation statuses; the assistant must not aggregate unreviewed invoice totals into financial figures. A bounded set of Gold credit decisions supplies reason/rule explanations. Conversation history is sent from the browser, bounded to eight messages, and is cleared when context changes or **New conversation** is selected. Chats are not written to the application's database. The existing Gemini service processes the selected facts and question.

The assistant is read-only: it has no SQL execution, filing, payment, document update or other action tools. Model source identifiers are checked against the server-selected source list; links are built by the server. Invoice text/history are treated as untrusted data. Missing data and model outages produce explicit unavailable/error responses rather than fabricated fallback answers. Requests require the existing authenticated session, CSRF validation and role checks; viewers may ask questions. A process-local throttle allows eight questions per account per minute (not a globally distributed quota across Cloud Run instances).

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/demo_ui_smoke.py
```

The browser script uses an isolated local API and stubbed assistant response, testing all scenarios, readonly controls, search, pagination, citations, follow-up interaction and mobile widths. Backend tests cover determinism, Gold exclusion, monetary reconciliation, search validation, authentication, input limits and source allowlisting. It does not replace the real-model deployment check.
