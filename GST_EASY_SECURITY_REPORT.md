# Security validation and outstanding controls

Implemented/tested: explicit active memberships, owner-only invitation administration, verified-email invitation acceptance, expiring/single-use identity tokens, password bounds/hashing, session revocation, provider-backed OTP state, distributed identity throttling, client-scoped bill/evidence access, version conflicts, transactional duplicate guards, separate return preparer/reviewer, locked-period mutation denial and read-only AI architecture. Production does not register the synthetic browser-test backend.

No secret values are included in release evidence. Deployment records only secret/configuration presence. Identity sender/provider readiness must not be fabricated.

Outstanding: independent penetration/security review, comprehensive revocation/concurrency/load testing, dedicated least-privilege preview/runtime identities, review of the shared compute service account permissions, full retention/backup restoration and notification/alert acceptance. Current runtime identity was previously found overprivileged. A passing regression suite is not security certification.
