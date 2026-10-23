# Assistant recovery
Live repeated-question testing reproduced a second, persistent throttle: the canonical assistant route reused auth_identity.throttle, permitting only five requests per 15 minutes. Four sequence answers plus the acceptance status query consumed that budget; subsequent requests returned 429. The initial audit found only the separate in-memory eight/minute limiter and missed this route-level cause. The fix gives authenticated assistant requests a tenant/user-bound persistent eight/minute budget; login/recovery limits remain five/15 minutes. No rate-limit records are deleted.

Implemented: readable 429 with Retry-After, bounded model history (six turns, 1,500 characters each), 100 KB context cap, existing output limit, two provider attempts maximum for transient failures, 20-second attempt timeouts, sanitized request IDs, categorized failures and authorized evidence-only fallback. Deterministic status answers precede provider calls. Invalid citations cannot introduce foreign evidence. Frontend retains a failed question for Retry and bounds the transcript to 50 messages.

Local tests cover 25 questions across rate windows, provider categories/retries and fallback. Circuit breakers, streaming and semantic summarization are not implemented. Live repeated model-question acceptance remains separate. Global model use remains limited to approved synthetic tenants.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.

First live sequence stopped after 12 requests: four HTTP 200 responses (one provider_rate_limit evidence fallback), followed by eight HTTP 429 responses. Provider failure recovered on the next request; application throttle required the code repair. Final results follow below.

## Final live assistant sequence

25 requests completed; HTTP statuses: {200: 25}. Only 7 were generated answers. Evidence-only fallbacks: {'provider_unavailable': 12, 'provider_rate_limit': 6}. Median response time 40.877 seconds. No application 429 lockout occurred after the dedicated budget repair. Generated answers returned after fallback responses, demonstrating recovery, but provider availability is NOT accepted as reliable. A separate minimal synthetic Vertex request with a 45-second timeout also failed with ServerError 504 after 43.008 seconds. Do not attribute every failure to chat history or claim 25 successful AI answers. Evidence: artifacts/intelligence-v3/assistant-sequence.json and provider-diagnostic.json.

## Local follow-up: deterministic summaries and provider circuit breaker

The assistant now answers four narrow, common dashboard questions directly from the already-authorized canonical summary: usable ITC, estimated GST cash requirement, GST liability on sales and blocked input tax. These answers do not invoke a model and retain the selected business/period source citation.

For other questions, two retry-bounded provider failures now open a short process-local circuit (30 seconds for timeout/unavailable; 60 seconds for provider rate-limit). During that interval, the user receives the existing safe evidence-only fallback immediately instead of repeatedly waiting for a long provider timeout. The circuit stores no tenant facts and closes after a successful provider answer. This is resilience behavior, not proof that Vertex availability is fixed.
