# V2 registration email configuration fix

Root cause: isolated V2 deployment omitted SMTP and authentication-mail queue/worker configuration. POST /api/auth/register calls auth_mail.ready() before account creation and correctly returned 503. This was not a Gmail-address or password validation problem.

Configured the existing approved Zoho sender ai@aidirac.com with STARTTLS on port 587. Copied the credential in memory into the new V2-only gst-easy-v2-smtp-password secret, version 1; no plaintext credential files, source or logs. Created separate gst-easy-v2-auth queue and granted enqueue permission to the V2 API service account. The worker URL/audience target only the private V2 API, with its existing authorized service identity. Previous services, queues, secrets and their IAM policies were not modified.

Changed release tooling: scripts/configure_gst_easy_v2_mail.py. No frontend, financial calculation or authentication-policy changes. V2 API revision gst-easy-v2-api-00004-dg8 is ready, using the existing reviewed application image. Existing session-secret reference remains configured.

Validation:
- SMTP STARTTLS authentication passed without sending a test message.
- 21 registration, identity and auth-mail regression tests passed; two nonfatal existing warnings.
- Live empty registration request returned 422 field validation after rollout, replacing the previous 503 email configuration failure. It created no account and sent no email.
- Complete prior-service/configuration/IAM baseline comparison passed.
- Actual inbox delivery, verification-link consumption and the user's new registration remain pending the user's retry. No success is claimed for these steps yet.

V2 remains a separate identity/database environment. Old accounts were not migrated or linked by email. Users can create separate V2 accounts and verify their email, or use the provisioned Nature Labs demo identity. No invoices or statements were imported for this fix.

Rollback: restore only the V2 API's preceding revision (which disables new registration email) or remove only its SMTP/auth-mail configuration. Do not change old services. Retain queued mail/audit records and secrets; no destructive cleanup is automatic.
