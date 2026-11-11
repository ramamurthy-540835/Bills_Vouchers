# GST Easy V3 diagnostics and sign-in troubleshooting

Update, 11 November: the repairs described below have now been deployed and tested on the public V3 URL. See [the release report](GST_EASY_V3_UPLOAD_RELEASE_2026-11-11.md) for current status; the following records the earlier diagnostic stage.

Date: 10 November 2026 (IST). Diagnostics started under the 9 November request and continued on 10 November. Status: live checks completed; login hardening implemented and tested locally, not deployed.

Application: https://gst-easy-v3-web-foovqasysa-el.a.run.app/login

## Outcome

Both existing synthetic demo accounts signed in through the real browser, reached the dashboard and remained signed in after refresh. A newly registered synthetic diagnostic account completed actual email delivery, owner-confirmed verification, sign-in, identity/profile/dashboard reads and logout. This proves the tested registration/email/login flow works for the authorized Gmail inbox; it does not prove delivery to every recipient or certify an absence of bugs.

The live assistant/core acceptance run passed 16 functional/security groups. All nine report APIs loaded, financial assistant summary answers agreed with the dashboard, private history survived a new sign-in and cross-account history/evidence access was denied. A real synthetic AI interpretation request returned a controlled provider-unavailable fallback; open-ended model reliability remains unresolved.

## Current live deployment

| Item | Verified value |
|---|---|
| Branch at start | GST_NEW_V3 |
| Local committed HEAD at start | 61f16eb63f6670ff75730f0b295ef9c028023a75 |
| Deployed application revision | 02383640a28b21609cea76beb335da21cbd99ed1 |
| API serving 100% traffic | gst-easy-v3-api-00019-tid |
| Web serving 100% traffic | gst-easy-v3-web-00019-bay |
| Backend pairing | Canonical V3 API with matching Cloud Run OIDC audience |
| Financial dataset | aidirac-503309.gst_easy_v3_finance_analytics |
| Private documents | aidirac-503309-gst-easy-v3-documents |
| Queues | gst-easy-v3-auth and gst-easy-v3-bills, both RUNNING |
| Infrastructure changes during diagnostics | None; service specifications, traffic and IAM compared unchanged |

V2 and older bills-voucher services were inspected read-only and remain unchanged. Their data, identities, queues and storage were not used for diagnostic writes. No new build, deployment, traffic promotion, secret rotation, DNS update, migration, Git commit or push was performed for this task.

## Sign-in findings

### Demo accounts

- Preloaded synthetic account: successful real-browser login, HTTP 200; login API sample 6.078 seconds. Identity, profile and dashboard requests succeeded; refresh preserved the workspace.
- Manual-testing synthetic account: successful real-browser login, HTTP 200; login API sample 5.790 seconds. Identity, profile and dashboard requests succeeded; refresh preserved the workspace.
- Existing operator activation is explicitly limited to the two synthetic identities and isolated demo resources. Neither account was falsely marked email verified or granted global administration.
- These timings are small functional samples, not load benchmarks. Sign-in is still slower than a low-latency target.

### Confirmed design defects and local repairs

1. The persistent authentication limiter counted successful sign-ins against the same five-attempt/15-minute budget as failed requests. Shared demo users could therefore exhaust the account budget through normal use. The local repair reserves an exact timestamped attempt before authentication, then removes only that reservation when an authorized sign-in completes. Other failed/in-flight reservations remain counted. The failed-attempt cap is unchanged.
2. Transient BigQuery transaction contention was classified as an authentication rate limit. The repair retries contention up to three times, preserves genuine HTTP 429 rate limits and returns HTTP 503 with Retry-After for exhausted contention. Login bookkeeping has the same bounded handling.
3. API exception serialization discarded HTTPException response headers. The repair preserves Retry-After and other exception headers.
4. Unverified and inactive accounts shared an inaccurate verification-only message. The repair separates those outcomes and returns an explicit email-verification-required code after correct credentials.
5. The login form had no request deadline or inline resend recovery. The repair adds a 45-second client timeout, preserved input after recoverable failure, an accessible error region and an inline resend action for the unverified state. Fresh authenticated navigation uses the new cookie through a document navigation rather than a potentially cached signed-out redirect. A cached-redirect incident was not independently reproduced; this is preventive hardening.
6. Session authentication is now assigned only after successful login bookkeeping and audit; failed bookkeeping cannot return an error while creating the new signed-in session.

No account passwords were reset, email verification bypassed, users force-activated, permissions broadened or rate-limit tables cleared.

## Actual registration-email test

A single new diagnostic registration used a plus-address of the previously authorized Gmail inbox. Its profile/business were explicitly marked synthetic in the isolated V3 dataset. The diagnostic account is not one of the shared demo identities, contains no invoices and has no global-admin access.

| Step | Actual result |
|---|---|
| Registration API | HTTP 201, 15.090-second sample |
| Sign-in before verification | HTTP 403, correctly denied |
| Durable outbox/queue | Worker completed, no pending auth tasks at inspection |
| Token | One verification token generated; 30-minute expiry; digest stored rather than plaintext |
| SMTP provider acceptance | 10 November 2026, about 13:37 IST |
| Inbox delivery | Owner explicitly confirmed receipt, including successful verification |
| Link consumption | Normal public verification flow; not a SQL activation or a token retrieved by the diagnostic runner |
| Sign-in after verification | HTTP 200 |
| Identity/profile/dashboard | HTTP 200 for each |
| Logout | HTTP 200 |

Provider correlation Message-ID: `<179429804764.2.12684500618690300063@aidirac.com>`. This identifier is not a verification token.

The strong random diagnostic password existed only in the test-process memory; it was neither logged, saved to a report nor committed. Original demo/customer passwords and financial records were preserved. Existing-account last-sign-in/audit entries and explicitly requested synthetic assistant history were expected effects of the live tests.

### Why some new users can remain unable to sign in

One recent unverified identity had provider-accepted mail and an expired, unused verification token. That proves the activation prerequisite was incomplete, not whether that person received the message. They need a new verification link and must complete verification before login. Other recent registrations were verified. No affected recipient was silently activated.

SMTP currently uses smtppro.zoho.in on port 587 with STARTTLS, ai@aidirac.com as sender and the V3 public URL for callbacks. The password is referenced from V3 Secret Manager. Public DNS returned SPF including zoho.in; the `_dmarc.aidirac.com` TXT query returned NXDOMAIN. DKIM alignment was not established from DNS alone because the active selector/message Authentication-Results were not available. Missing DMARC is a deliverability-hardening item, not a proven cause of the reported non-delivery. DNS/provider-admin changes were not made.

Acceptance by SMTP is distinguished from inbox delivery. Only this authorized test inbox was confirmed. For another affected recipient, provider/mail-administrator tracing using the Message-ID and recipient/time is still needed if a fresh request is accepted but not delivered.

## Test evidence

| Check | Actual result |
|---|---|
| Initial backend suite | 885 passed, 27 skipped |
| Final backend suite after login repairs | 895 passed, 27 skipped |
| Ruff, app/tests | Passed |
| mypy, app | Passed, 94 source files |
| Frontend TypeScript | Passed |
| Next.js production build | Passed before and after frontend repair |
| Initial complete browser regression | 94 passed |
| Browser regression plus new recovery tests | 94 passed; two new test locators initially matched Next.js's route announcer as well as the form alert |
| Focused corrected login-recovery tests | 2 passed |
| Final consolidated browser run | 96 passed; runner exit code 0 |
| Live template/portal sequence | 11/11 HTTP 200, history saved, no degraded template answers |
| Live functional/security acceptance | 16 groups passed |
| Live synthetic model probe | HTTP 200 with safe degraded provider_unavailable response; history saved |
| Cloud preservation comparison | All six inspected services unchanged (specification, traffic and IAM) |

The full local browser suite covers Add Business, profile editing, logo/website actions, permissions, business switching, invoice uploads and duplicate handling, review/confirmation/rejection/correction, original preview, Auto Review policies, financial displays, all nine reports, GSTR-2B import, return safety restrictions, private assistant history and responsive navigation. These tests use isolated local synthetic fixtures and mocked external services; they are not equivalent to live provider, government or customer acceptance.

The initial live-harness copy had a Windows text-encoding mismatch in a Unicode locator. The corrected UTF-8 copy completed successfully. This was a diagnostic-harness error, not an application crash. Original failed-run evidence was retained.

## Live diagnostic coverage and limits

Passed live groups: unauthenticated history denial; authorized originals; repeated templates; history persistence/CSRF; history across sign-in; responsive history UI at 1440px/390px; two-account isolation; cross-business evidence denial; authorized business switching; synthetic-export protection; core pages/invoice APIs; nine report APIs; unchanged financial totals; unchanged invoice records; invalid-file rejection; three financial answers reconciled to the dashboard.

No financial confirmation/deletion, live return filing, paid GSP request, real-customer bill upload, unrestricted global AI processing, real-client profile edit, load test, mailbox-wide certification or every possible UI action was performed live. Valid upload/OCR and financial mutations were exercised locally rather than adding invoices to an existing demo/customer workspace.

Recent seven-day logs contained five handled extraction errors reporting that automatic AI processing was not enabled for the applicable business. This is the existing global-model tenant allowlist protecting unapproved business data. No inference authorization was broadened. Those uploads fall back to manual review; AI extraction for an unapproved business cannot be claimed operational. No matching HTTP 5xx request entries were returned by that bounded log query. That is evidence for the query window, not an assurance of zero historical errors.

The 27 skipped specialized/legal/extraction/integration scenarios remain unverified. Formal GST/legal approval, unrestricted live government filing, universal email delivery and consistent open-ended Gemini availability remain outside verified readiness.

## Changes awaiting release

- `app/services/auth_identity.py`: exact successful-attempt cleanup and bounded contention recovery.
- `app/routes.py`: distinct sign-in states; safe bookkeeping/session ordering.
- `app/main.py`: preserve error response headers.
- `frontend/app/login-form.tsx`: timeout, input preservation, verification resend and fresh navigation.
- `tests/test_auth_identity.py`: security, limit, contention and session/error contracts.
- `tests/frontend/login-recovery.spec.ts`: unverified/resend flow, failed transport and safe retry.

These changes are local on GST_NEW_V3. The Cloud Run URL still serves the previously released application revision. Production traffic promotion requires explicit release approval under the earlier V3 deployment instructions. No V2 changes are proposed.

## Evidence and next actions

Evidence directory: `artifacts/diagnostics-2026-11-09/` (the start-date directory was retained across continuation).

Key files: `auth-live.json`, `auth-storage.json`, `registration-delivery.json`, `mail-runtime.json`, `cloud-before.json`, `cloud-after.json`, `cloud-preservation.json`, `cloud-errors.json`, `queues.json`, `diagnostics-live.json`, backend XML/log reports, browser JSON/log reports, production-build logs and synthetic screenshots.

Next steps: release the tested login repairs to a V3 candidate and approve main traffic separately; trace any still-affected recipient using a fresh Message-ID; arrange mail-administrator review of DKIM/DMARC; investigate the intermittent model failure under the approved synthetic-only boundary; complete the 27 unverified scenarios and professional GST review. Do not certify the entire platform bug-free from this diagnostic run.
