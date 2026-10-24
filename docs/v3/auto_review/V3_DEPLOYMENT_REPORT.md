# V3 Invoice Intelligence deployment

Status: LIVE V3 CODE RELEASED on 24 October 2026. Complete Auto Review 2.0 statutory and scenario acceptance remains incomplete.

- Source branch: GST_NEW_V3
- Runtime source commit: 2dc46b9ab09a4ac1e74e17220e47887d536ebfc1
- Successful final Cloud Build: 529145b8-a4f8-4831-96c4-83f08b496a0a
- Live API revision: gst-easy-v3-api-00013-vaf (100%)
- Live web revision: gst-easy-v3-web-00012-dar (100%)
- Live web: https://gst-easy-v3-web-foovqasysa-el.a.run.app/login
- Live API: https://gst-easy-v3-api-foovqasysa-el.a.run.app
- Prior live API revision: gst-easy-v3-api-00006-g98
- Prior live web revision: gst-easy-v3-web-00005-jbp
- Candidate web: https://intelligence---gst-easy-v3-web-foovqasysa-el.a.run.app/login
- Candidate API: https://intelligence---gst-easy-v3-api-foovqasysa-el.a.run.app
- API immutable image: asia-south1-docker.pkg.dev/aidirac-503309/gst-easy-v3/api@sha256:d27e4b3dd434fd42f3f108c1462ecd58a9ffbc4131c670c745234c1276ba385c
- Web immutable image: asia-south1-docker.pkg.dev/aidirac-503309/gst-easy-v3/web@sha256:b02c535194e17d7ccb1a3053b3d924a7b2dc8e98e8ccaddac14558874fdd7631

Earlier successful builds: 6bd9b889-1ff1-41eb-922d-6971d97c6d68 (55412be; first tested candidate), 789c63a0-274b-409b-adc1-e234be85a385 (f25f508; superseded before deployment by the parallel-loading build). Build logs are available in Google Cloud Build for project aidirac-503309 using those IDs.

Only gst-easy-v3-api and gst-easy-v3-web were deployment targets. The tested images were first placed on the no-traffic `intelligence` tag. A second pair of revisions using those same image digests was configured for the main V3 auth callback, worker and backend URLs, then each V3 service was routed to its matching new revision at 100%. Existing `auto-review` and `intelligence` tags were retained. V3-specific datasets, private bucket, service accounts and authenticated worker audience were checked by the release script. No live approved GST policies were seeded. Existing additive CREATE-IF-NOT-EXISTS V3 migrations were reapplied; no financial schema or customer data migration was run.

The strict all-project preservation assertion FAILED on prism-frontend: baseline revision prism-frontend-00027-nur became prism-frontend-00030-nuh with a different traffic mapping. No command in this release targeted that service. It was not reverted. Therefore an assertion that every project service remained unchanged would be false. The separate read-only comparison verified unchanged V2, bills-voucher and bills-voucher-web live traffic, and the intended V3-only changes. Evidence: artifacts/intelligence-v3/preservation-diff.json and the final Cloud Run revision inspection.

Final live candidate acceptance passed: authorized login/navigation; policy default OFF and persistence; durable existing-bill batch processing with four manual exceptions; explicit individual exclusions surviving a later business-level batch; responsive intelligence views; unchanged confirmed financial status; inherited future ON and explicit future OFF CSV uploads; original-byte retention; deterministic assistant evidence; and policy reset to OFF. Synthetic test records remain as manual-review evidence in the authorized demo business. Auto-confirmation with an approved synthetic policy passed locally only; live automatic confirmation is blocked by missing reviewed legal policies. Evidence: artifacts/auto-review-v3/intelligence-live-acceptance.json.

The first repeated assistant test reproduced a five-per-15-minute authentication limiter incorrectly reused for chat. The live revision contains its dedicated tenant/user eight-per-minute repair, direct canonical answers for four common financial questions, and a short provider circuit breaker. Final repeated-question outcomes from the earlier candidate are recorded separately in TEST_RESULTS.md; HTTP 200 fallback is not counted as a model-generated answer.

The current candidate and main V3 URLs both passed synthetic login, Invoice Intelligence UI, business policy OFF, and four direct canonical assistant answers. Main URL evidence: artifacts/intelligence-v3/smoke-live.json. V3 live traffic was rechecked after the switch; V2 and older Bills & Vouchers live revisions were unchanged. Source code was not modified between image build and live deployment; the follow-up smoke script and this report are separate release evidence.

Rollback: route `gst-easy-v3-api` to `gst-easy-v3-api-00006-g98=100` and `gst-easy-v3-web` to `gst-easy-v3-web-00005-jbp=100` using `gcloud run services update-traffic` in project `aidirac-503309`, region `asia-south1`; verify both URLs afterward. Keep audit rows and original evidence. Do not delete V3 financial records as part of a code rollback.
