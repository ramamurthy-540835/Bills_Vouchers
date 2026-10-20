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
V3 callback URL will be obtained from the newly created service, not guessed.

Executed local evidence: auth identity/outbox/outcome tests passed. Missing SMTP
configuration produces a real unavailable state; registration is not silently
reported as email-delivered. The queue has five attempts with bounded backoff.

Still pending: actual inbox confirmation, V3 link verification/replay/expiry and
recovery smoke tests, DNS/provider delivery-event investigation, bounce/complaint
handling and signed webhooks. The current SMTP adapter has no verified delivery
webhook. Do not equate provider_accepted with delivered or diagnose an inbox
problem solely from an HTTP 200. Repair-worker invocation also requires an
operational retry budget; it is not a substitute for delivery monitoring.
