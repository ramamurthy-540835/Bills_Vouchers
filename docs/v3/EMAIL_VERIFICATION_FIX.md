# Email verification investigation

The existing application already has a persisted outbox, Cloud Tasks dispatch,
OIDC-protected worker, expiring hashed tokens, resend, verification and recovery.
V3 does not replace authentication or auto-verify accounts.

Two source defects were reproduced locally: expired/consumed links could be
recorded as sent without a send, and SMTP recipient refusals were not inspected.
The worker now distinguishes provider_accepted, expired and ignored outcomes.
SMTP acceptance includes a message ID and explicitly does not assert delivery.
Legacy sent rows remain terminal for retry compatibility.

V3 uses its own auth queue, session secret and SMTP secret. The approved sender is
ai@aidirac.com through smtppro.zoho.in:587 with STARTTLS. Only ai@aidirac.com is
authorized for live test mail. V2 runtime and secret versions are unchanged.
V3 callback URL is https://gst-easy-v3-web-foovqasysa-el.a.run.app, retrieved
from the newly created service.

Executed local evidence: auth identity/outbox/outcome tests passed. Missing SMTP
configuration produces a real unavailable state; registration is not silently
reported as email-delivered. The queue has five attempts with bounded backoff.

Still pending: actual inbox confirmation, V3 link verification/replay/expiry and
recovery smoke tests, DNS/provider delivery-event investigation, bounce/complaint
handling and signed webhooks. The current SMTP adapter has no verified delivery
webhook. Do not equate provider_accepted with delivered or diagnose an inbox
problem solely from an HTTP 200. Repair-worker invocation also requires an
operational retry budget; it is not a substitute for delivery monitoring.

## Live investigation, 20 October 2026

Actual V3 registration returned 201 and the durable worker recorded provider
acceptance at 10:22:02 UTC. The authorized recipient reported nonreceipt,
including spam. A separate plain-text diagnostic at 10:33:56 UTC received SMTP
DATA response 250 with no recipient refusal; this was also not received.
Diagnostic Message-ID: `<179249243520.16120.2334133968598681690@aidirac.com>`.
Neither outcome is successful delivery.

The diagnostic isolates the failure beyond verification-link content: plain
mail is also affected. It does not identify the exact downstream cause.
SPF lookup returned `v=spf1 include:zoho.in ~all`; DMARC lookup had no record.
DKIM selector/validation and provider disposition are not verified. Missing
DMARC is not asserted to be the cause. Read-only IMAP authentication failed;
no mailbox messages or settings were changed.

Zoho organization-level tracing is a mail-administrator dependency. The user
does not have that access. Development continues using backend/runtime evidence.
No DNS, V2 SMTP, existing sender policy or authentication requirements changed.

The follow-up source adds a Date header and safe Message-ID/failure-code logging
for provider correlation. Logs omit recipient, credentials, link and body.
These changes improve traceability; they are not presented as a proven delivery
fix. Cloud Tasks retains five attempts with bounded backoff. Provider acceptance
is terminal to avoid repeatedly mailing an accepted message. A user-requested
resend creates a new request; inbox acceptance is still required for live QA.
