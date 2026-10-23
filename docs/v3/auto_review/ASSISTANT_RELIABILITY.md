# Assistant recovery
A reproducible source failure path is the existing eight-requests-per-minute limit combined with generic frontend error handling. This does not prove the reported live failure's root cause: the sampled Cloud Run logs contain only two successful assistant requests, about 7.00 and 7.13 seconds.

Implemented: readable 429 with Retry-After, bounded model history (six turns, 1,500 characters each), 100 KB context cap, existing output limit, two provider attempts maximum for transient failures, 20-second attempt timeouts, sanitized request IDs, categorized failures and authorized evidence-only fallback. Deterministic status answers precede provider calls. Invalid citations cannot introduce foreign evidence. Frontend retains a failed question for Retry and bounds the transcript to 50 messages.

Local tests cover 25 questions across rate windows, provider categories/retries and fallback. Circuit breakers, streaming and semantic summarization are not implemented. Live repeated model-question acceptance remains separate. Global model use remains limited to approved synthetic tenants.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
