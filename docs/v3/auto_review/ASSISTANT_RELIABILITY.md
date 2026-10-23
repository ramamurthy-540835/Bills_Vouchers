# Assistant recovery
Live repeated-question testing reproduced a second, persistent throttle: the canonical assistant route reused auth_identity.throttle, permitting only five requests per 15 minutes. Four sequence answers plus the acceptance status query consumed that budget; subsequent requests returned 429. The initial audit found only the separate in-memory eight/minute limiter and missed this route-level cause. The fix gives authenticated assistant requests a tenant/user-bound persistent eight/minute budget; login/recovery limits remain five/15 minutes. No rate-limit records are deleted.

Implemented: readable 429 with Retry-After, bounded model history (six turns, 1,500 characters each), 100 KB context cap, existing output limit, two provider attempts maximum for transient failures, 20-second attempt timeouts, sanitized request IDs, categorized failures and authorized evidence-only fallback. Deterministic status answers precede provider calls. Invalid citations cannot introduce foreign evidence. Frontend retains a failed question for Retry and bounds the transcript to 50 messages.

Local tests cover 25 questions across rate windows, provider categories/retries and fallback. Circuit breakers, streaming and semantic summarization are not implemented. Live repeated model-question acceptance remains separate. Global model use remains limited to approved synthetic tenants.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.

First live sequence stopped after 12 requests: four HTTP 200 responses (one provider_rate_limit evidence fallback), followed by eight HTTP 429 responses. Provider failure recovered on the next request; application throttle required the code repair. Retest pending on the repaired candidate.
