# Assistant reliability, templates and private history

Date: 29 October 2026. Branch: GST_NEW_V3. Status: deployed and verified on the main
V3 URL. See ASSISTANT_RELEASE_2026-10-29.md for actual revisions, migration, live
results and remaining provider/legal limitations. The sections below describe the
implementation and its original local verification.

## Implemented behavior

- 120 deterministic scenario entries in 12 categories, plus 29 common wording
  aliases. This is routing/guidance coverage, not 120 certified legal decisions.
- 31 progressive portal topics. The initial response covers only the requested
  topic/stage; Next step advances it using the user's own server-side conversation.
  Full guide/all steps explicitly requests the three stages together.
- GSTR-1, 1A, 2A, 2B, 3B; CMP-08; GSTR-4, 5, 5A, 6, 7, 7A, 8, 9, 9C, 10, 11;
  IFF; challan, refund, IMS, ledgers; registration/amendment/cancellation/revocation,
  notices, LUT, QRMP, e-invoice and e-way bill guidance.
- GSTR-1B is clarified rather than treated as a real supported filing form.
  GSTR-2A/2B and GSTR-7A are distinguished from returns the user files.
- Specialist forms have preparation/navigation checklists and official-manual
  references. They are not invented field-by-field schemas. Current taxpayer,
  period, legal applicability and professional review still govern real actions.
- Common summary amounts remain backend-derived. Ambiguous ITC and explicitly
  different YYYY-MM periods trigger clarification. Other financial analysis still
  requires the needed records; no arithmetic or eligibility logic was changed.
- Public guidance is resolved before loading financial records. Unknown permitted
  financial questions retain the grounded Gemini path; unrelated questions receive
  scope guidance. This is conservative routing, not universal natural-language understanding.

## Reliability diagnosis and changes

The old in-process limit stopped conversations at eight questions per minute.
It is now 30 requests/minute per user/process, with explicit recoverable throttling.
The persistent eight/minute budget remains for actual provider calls, not template
answers. This is not a claim of a distributed global limit for template traffic.

The persistent provider budget formerly mapped concurrent/aborted BigQuery
transactions to 429. Transient conflicts now receive at most three attempts, then
503 with Retry-After rather than a misleading user-budget error. The shared guard
still exists; this change does not replace the underlying transactional architecture.

Model client construction now occurs inside the safe failure boundary. Provider
attempts have 12-second HTTP timeouts (at most two attempts), bounded conversation
history and circuit recovery. Oversized report arrays are excluded from financial
summary context; reconciliation sent to Gemini is capped and labelled incomplete.
The frontend has a 60-second request timeout, preserves failed questions and supports
retry. Fallback logging emits sanitized JSON containing category/reference only.

Read-only Cloud Logging diagnostics found the latest three assistant requests on
28 October had HTTP 200 latencies 8.859, 23.585 and 42.838 seconds, and a fallback
event at 09:48:07 UTC. HTTP 200 is not evidence of a successful model interpretation.
These samples do not prove one root cause or establish percentiles. No new live
model call or before/after deployment performance claim is made.

## Privacy and ownership

GET /api/assistant/history returns only the authenticated user's rows within the
selected authorized business and period. Actor/business IDs are not taken from a
browser history request. Conversation UUIDs alone do not grant access. Every
read, conversation lookup, insert and clear is scoped by user and business/period.

POST /api/assistant/chat ignores browser-supplied history for real workspaces.
Recent turns are loaded from that user's server-side conversation. Demo scenario
chat remains separate and ephemeral. No shared personal-answer cache, localStorage
or shared browser history store was introduced.

Recently asked is a collapsed addition to the existing chat panel. It supports
saved answer viewing, paged older questions, historical/freshness labels, new
conversations and Clear my history. New conversation does not erase saved turns.
Clearing affects only the actor's selected business/period. Response caching is
private/no-store, including through the existing Next.js API proxy.

Rows expire after 90 days using table partition expiration and read-time bounds.
This is application-user isolation, not encryption against infrastructure/database
administrators. Authorized members can still see shared business records according
to their normal permissions; they cannot inspect another member's chat history.
Static public guidance may be identical for two users without sharing their questions.

Existing approved provider processing remains applicable for actual Gemini calls.
History privacy does not imply that model requests never reach Google. This change
does not alter billing/provider retention contracts or authorize new global processing.

## Migration and rollout

1. Review migrations/034_private_assistant_history.sql against the exact approved
   V3 project/dataset. Replace PROJECT_ID/DATASET; never run against V2.
2. Create the additive table with the intended V3 service identity permissions;
   no startup/request-time DDL occurs. Keep dataset IAM restricted.
3. Build the reviewed source and deploy a compatible API/web candidate pair.
4. Verify a real approved account can ask, log out/in and recover its history.
   Verify a different account in the same business sees none of those turns.
5. Verify selected business/period, revoked membership, CSRF, provider-disabled
   answers, real provider errors and table-backed pagination/clearing.
6. Release only through the approved V3 rollout process and monitor latency,
   provider budgets, history failures and BigQuery query costs.

If the table is unavailable, template/answer generation can continue with
history_saved=false and an explicit UI warning. History endpoints report 503 rather
than falsely showing an empty or successful saved state. Do not declare persistence
accepted until the actual table integration is tested.

Rollback: redeploy the prior compatible API/web revisions; retain the additive
history table under its retention policy. Do not delete customer history as part of
a code rollback. V2 and older resources were not modified.

## Tests actually executed

| Check | Result |
|---|---|
| Broad local backend regression | 883 passed, 27 skipped |
| Focused assistant/reliability/history suite | 231 passed |
| Ruff: app and tests | Passed |
| mypy: app | Passed, 94 source files |
| Frontend TypeScript | Passed |
| Next.js production build | Passed |
| New Playwright assistant tests | 2 passed |
| git diff --check | Passed (line-ending notices only) |

The broad suite was followed by focused checks for the final scope/logging changes,
portal wording and two production CSRF cases on chat/history deletion.
Existing skipped scenarios remain skipped and are not presented as passed.

API tests exercise production route/service code against an isolated in-memory
BigQuery-shaped repository and dependency-overridden identities. They cover
same-business different-user isolation, other businesses/periods, relogin,
conversation-ID reuse, forged browser history, revoked access, authentication,
storage failure, 25 questions, pagination and scoped deletion.

Browser tests use the built Next.js UI, local synthetic workspace fixture and
mocked chat/history HTTP responses. They cover 25 questions, reload, recovery,
unsafe-link suppression, conversation reset, clearing and 1440/390px screenshots.
They are not real provider or BigQuery/browser end-to-end acceptance.

Screenshots: artifacts/assistant-2026-10-29/assistant-1440.png and assistant-390.png.
Playwright JSON: artifacts/v3/frontend-tests.json (latest targeted run).

## Acceptance follow-up

- Actual V3 table migration and durable storage acceptance were completed in the
  subsequent release; no IAM changes were required.
- Live candidate/main repeated-question tests completed. Provider outcomes and
  measured functional sample timings are recorded in the release report; broad
  load testing and guaranteed performance remain outstanding.
- Professional GST review of conditional advice and specialist-form instructions.
- Official portal menus/eligibility may change; references are guidance, not a
  government submission integration or guarantee of statutory acceptance.
- The subsequent release completed Git push, Cloud Build, migration and live V3
  acceptance; see the release report. Government filing remains disabled.

Official references include GST Portal GSTR-1, GSTR-2B, GSTR-3B and GSTR-1A
manuals/FAQ, the portal user-guide index and CBIC payment guidance. Each portal
response links its applicable official reference. No permanent statutory rate,
threshold, due date or legal decision has been hardcoded as universally applicable.
