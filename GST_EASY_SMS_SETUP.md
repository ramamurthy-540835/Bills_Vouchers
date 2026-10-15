# SMS verification rollout recommendation - 15 October 2026

Recommended first provider: Twilio Verify, because the application already implements its API integration. The owner requested a recommendation and has not supplied a provider account or credentials. No paid account/service has been provisioned or real SMS sent.

1. Create a business-owned Twilio account and confirm with Twilio that the intended India and international verification routes are supported for this business. Complete any required company/sender/template DLT registration for the selected route. Requirements differ by route; do not assume an overseas route bypasses applicable registration requirements.
2. Create a Verify service and a least-privilege API key. Store service SID, API key and API secret in approved Secret Manager configuration. Never commit secrets or send them through chat.
3. Enable Fraud Guard, permit only required destination countries initially, configure provider rate limits and spending alerts. Preserve the application's per-user/per-number throttles.
4. Test authorized real numbers on the intended carriers/countries: send, correct/incorrect code, expiry, retry, replay, changed number, provider outage and billing limits. Trial accounts restrict recipient numbers, so trial success alone is not production-delivery acceptance.
5. Verify that mobile_verified changes only after actual provider approval and the local single-use transaction succeeds. The current implementation expires challenges after ten minutes and keeps failures unverified.
6. Keep email ownership verification mandatory. Before SMS acceptance, describe mobile numbers as unverified and do not enable a mandatory OTP gate that would lock customers out. Enable the mandatory policy only after reviewing the deployed recovery path.

Account/provider configuration and actual delivery remain external dependencies. Existing code: app/services/mobile_verification.py; settings use TWILIO_VERIFY_SERVICE_SID, TWILIO_API_KEY and TWILIO_API_SECRET. REQUIRE_OTP is a policy switch, not proof that a provider is operational.

Official references checked:
- https://www.twilio.com/en-us/guidelines/in/sms
- https://www.twilio.com/docs/verify/preventing-toll-fraud
- https://www.twilio.com/docs/verify/api/programmable-rate-limits
- https://www.twilio.com/docs/verify/api/verification

GST export research checkpoint: the official GST portal describes offline-tool JSON upload at https://tutorial.gst.gov.in/userguide/returns/Creation_of_Outward_Supplies_Return_in_GSTR-1.htm . A current machine-readable schema and validator were not obtained in this reporting changeset; customer reports must not be relabelled as official filing exports.
