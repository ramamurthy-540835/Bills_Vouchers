# v5 route audit

Updated 2026-09-24. This table inventories every Python route decorator in the checkout. Static PASS means the dependency/scope is present in source, not that every legacy business workflow has an end-to-end test. Runtime isolation gates cover the v5 workspace, document detail/search, pipeline and filing actions; legacy workflows retain their existing tests.

## Resolution chain

Next.js server page -> signed backend session -> users -> active client_memberships -> selected client -> current client_user_role -> gst_client_profile. Workspace queries bind client_id and period. A missing profile produces incomplete-profile chrome; a missing session redirects before rendering. Legacy illustrations require DEMO_FALLBACK. The explicitly selected /demo workspace uses generated synthetic records from mock_data.py; live Overview has no sample fallback.

D1 was located in the recovered preview frontend/app/page.tsx: its company context used the Umesh GSTIN independently of the resolved user name. That component and the fixture-only filing page have been replaced. Recovery source: Cloud Build f70ce346-7cda-4642-8b8c-c6b2ca829795; the later production build did not contain the complete preview implementation.

## Frontend

| Route | Auth | Client | Without data | Layer | Result |
|---|---|---|---|---|---|
| `/` | Server proxy + backend session | Workspace identity | Complete shell / empty or error card | Bronze, silver, gold via API | PASS (browser gate) |
| `/documents` | Server proxy + backend session | Workspace identity | Complete shell / empty or error card | Bronze, silver, gold via API | PASS (browser gate) |
| `/documents/[id]` | Server proxy + backend session | Workspace identity | Complete shell / empty or error card | Bronze, silver, gold via API | PASS (browser gate) |
| `/gst/filing` | Server proxy + backend session | Workspace identity | Complete shell / empty or error card | Bronze, silver, gold via API | PASS (browser gate) |
| `/gst/workspace` | Server proxy + backend session | Workspace identity | Complete shell / empty or error card | Bronze, silver, gold via API | PASS (browser gate) |
| `/search` | Server proxy + backend session | Workspace identity | Complete shell / empty or error card | Bronze, silver, gold via API | PASS (browser gate) |
| `/assistant` | Server proxy + backend session | Workspace identity | Complete shell / empty or error card | Bronze, silver, gold via API | PASS (browser gate) |
| `/demo` | Server proxy + backend session | Workspace identity | Complete shell / empty or error card | Bronze, silver, gold via API | PASS (browser gate) |
| `/login` | Public sign-in | Not yet selected | Sign-in form | Identity | PASS |
| `/settings` | Server proxy; password API session | Not needed for own password | Password form | Identity | PASS; standalone security flow |
| `/api/[...path]` | Forwarded cookie, backend authorization | Backend | Structured error | Backend | PASS |

## Backend

| Method / route | Auth applied | Client resolved | Without data | Reads from | Static result |
|---|---|---|---|---|---|
| `GET /login` | Public identity/health endpoint | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `POST /login` | Public identity/health endpoint | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `GET /signup` | Public identity/health endpoint | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `POST /signup` | Public identity/health endpoint | Bound selected client | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `POST /logout` | Public identity/health endpoint | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `POST /clients/select` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /gst` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /gst/returns` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /gst/returns` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /gst/health` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `GET /gst/gstr1` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /gst/validation` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /gst/reconciliation` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /gst/itc` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /accounts` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /accounts` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /transactions` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /transactions` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /expenses` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /expenses` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /documents/upload` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /documents/upload` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /documents/{document_id}/scan` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /documents` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /documents/export.csv` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /documents/bulk-delete` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /documents/search` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /documents/{document_id}/review` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /documents/{document_id}/file` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /documents/{document_id}/review` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /documents/{document_id}/approve` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /documents/{document_id}/reject` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /reports` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /powerbi` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /audit-logs` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /users` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /users/{user_id}` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /settings` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /settings` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /settings/client` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /settings/client/create` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /api/auth/login` | Public identity/health endpoint | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `GET /api/auth/csrf` | Session dependency | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `POST /api/auth/logout` | Session dependency | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `GET /api/auth/me` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `POST /api/auth/password` | Session dependency | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `GET /api/review/queue` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/review/{document_id}` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `PATCH /api/review/{document_id}` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /api/review/{document_id}/approve` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /api/review/{document_id}/reject` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/dashboard` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Gold financial data; profile/status metadata | PASS |
| `GET /api/documents` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/documents/search` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /api/documents/upload` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /api/documents/{document_id}/scan` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/documents/{document_id}/scan-status` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `DELETE /api/documents/{document_id}` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/documents/{document_id}` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /health` | Public identity/health endpoint | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `GET /api/health` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `GET /healthz` | Public identity/health endpoint | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `GET /readyz` | Public identity/health endpoint | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `GET /api/v1/health` | Public identity/health endpoint | Identity / service scope | Empty response or explicit error; page templates retain shell | Identity / operational | PASS |
| `GET /api/v1/review/queue` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/v1/review/{document_id}` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `PATCH /api/v1/review/{document_id}` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /api/v1/review/{document_id}/approve` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /api/v1/review/{document_id}/reject` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/v1/documents/{document_id}` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/v1/documents` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/v1/documents/search` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /api/gst/demo/compute` | Session dependency | Identity / service scope | Empty response or explicit error; page templates retain shell | GST profile / gold | PASS |
| `POST /api/gst/clients/{client_id}/validate` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | GST profile / gold | PASS |
| `GET /api/gst/clients/{client_id}` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | GST profile / gold | PASS |
| `GET /api/gst/clients/{client_id}/history` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | GST profile / gold | PASS |
| `POST /api/gst/clients` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | GST profile / gold | PASS |
| `POST /api/gst/itc/compute` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | GST profile / gold | PASS |
| `POST /api/gst/itc/scenarios` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | GST profile / gold | PASS |
| `GET /api/reports/gstr` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/documents/{document_id}/review-url` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/v1/reports/gstr` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /reports/gstr.csv` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `POST /internal/tasks/scan` | OIDC identity | Identity / service scope | Empty response or explicit error; page templates retain shell | Legacy scoped tables | PASS |
| `GET /api/pipeline/search` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `GET /api/pipeline/documents/{doc_id}` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `GET /api/workspace` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `POST /api/workspace/period` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `POST /api/workspace/client` | Session dependency | Delegates to scoped handler | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `GET /gst/filing` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `POST /api/pipeline/upload` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `POST /api/pipeline/documents/{doc_id}/retry` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `GET /api/pipeline/documents/{doc_id}/file` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `POST /api/pipeline/documents/{doc_id}/review` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `POST /api/gst/filing/recompute` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `POST /api/gst/filing/import-2b` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `POST /api/gst/filing/outward` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `POST /api/gst/filing/transition` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `POST /api/gst/filing/generate/{kind}` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `POST /internal/pipeline/document` | OIDC identity | Identity / service scope | Empty response or explicit error; page templates retain shell | Medallion (bronze/silver/gold) | PASS |
| `GET /api/demo/scenarios` | Session dependency | Explicit demo namespace | Empty response or explicit error; page templates retain shell | Generated synthetic records; no customer financial tables | PASS |
| `GET /api/demo/data` | Session dependency | Explicit demo namespace | Empty response or explicit error; page templates retain shell | Generated synthetic records; no customer financial tables | PASS |
| `GET /api/demo/search` | Session dependency | Explicit demo namespace | Empty response or explicit error; page templates retain shell | Generated synthetic records; no customer financial tables | PASS |
| `POST /api/demo/chat` | Session dependency | Explicit demo namespace | Empty response or explicit error; page templates retain shell | Generated synthetic records; no customer financial tables | PASS |
| `POST /api/assistant/chat` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | Selected client Gold and scoped source evidence; read-only Gemini | PASS |
| `GET /api/gst/workspace` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | GST profile / gold | PASS |
| `GET /api/gst/workspace/download` | Session dependency | Bound selected client | Empty response or explicit error; page templates retain shell | GST profile / gold | PASS |

Backend registrations inventoried: **108**.

## Verification limits

Unauthenticated login and infrastructure health probes are intentionally public. Identity lookup queries bind user/email parameters before client selection; they are not tenant financial reads. No claim is made that every legacy write has been migrated to the new medallion tables. The new web shell uses the new tenant-bound APIs. Source documents remain immutable; no legacy routes or tables were removed.
