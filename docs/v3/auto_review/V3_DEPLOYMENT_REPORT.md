# V3 Invoice Intelligence candidate deployment

Status: DEPLOYED CANDIDATE, NOT LIVE RELEASED. Complete Auto Review 2.0 acceptance remains incomplete.

- Source branch: GST_NEW_V3
- Runtime source commit: b7bed23c7903735c009245893b97e7894683bf2f
- Successful final Cloud Build: a304c0b0-ec49-4a7c-8319-f4999914fd5b
- API revision: gst-easy-v3-api-00010-pew
- Web revision: gst-easy-v3-web-00009-kic
- Candidate web: https://intelligence---gst-easy-v3-web-foovqasysa-el.a.run.app/login
- Candidate API: https://intelligence---gst-easy-v3-api-foovqasysa-el.a.run.app
- API immutable image: asia-south1-docker.pkg.dev/aidirac-503309/gst-easy-v3/api@sha256:2f9a9fe08c7ca0b8f244465ccc1b7ff4915168f74ab3f00eee28740092ff80d3
- Web immutable image: asia-south1-docker.pkg.dev/aidirac-503309/gst-easy-v3/web@sha256:bafcb4e8088ed258f07ebb2d512ecd4cca0819f3c789ef71cd36f480185cff03

Earlier successful builds: 6bd9b889-1ff1-41eb-922d-6971d97c6d68 (55412be; first tested candidate), 789c63a0-274b-409b-adc1-e234be85a385 (f25f508; superseded before deployment by the parallel-loading build). Build logs are available in Google Cloud Build for project aidirac-503309 using those IDs.

Only gst-easy-v3-api and gst-easy-v3-web were deployment targets, with --no-traffic and tag intelligence. Existing auto-review tags were retained. V3-specific datasets, private bucket, service accounts and authenticated worker audience were checked by the release script. No live approved GST policies were seeded. Existing additive CREATE-IF-NOT-EXISTS V3 migrations were reapplied; no financial schema or customer data migration was run.

The strict all-project preservation assertion FAILED on prism-frontend: baseline revision prism-frontend-00027-nur became prism-frontend-00030-nuh with a different traffic mapping. No command in this release targeted that service. It was not reverted. Therefore an assertion that every project service remained unchanged would be false. The separate read-only comparison verified unchanged V2, bills-voucher, bills-voucher-web and other captured services, and preserved V3 live traffic/prior tags. Evidence: artifacts/intelligence-v3/preservation-diff.json. Final comparison passed for protected GST services and existing V3 traffic; artifacts/intelligence-v3/preservation-final.json retains all_project_services_unchanged=false for the unrelated drift.

First live candidate tests passed: login, policy OFF/default and persistence, three existing pending bills processed into manual exceptions, inherited future ON and per-file OFF CSV uploads, byte-for-byte authorized originals, responsive views and unchanged confirmed financial totals. Two visibly synthetic CSV originals remain as manual-review evidence in the authorized demo business. Business policy was reset OFF. Auto-confirmation with an approved synthetic policy passed locally only; live automatic confirmation is blocked by missing reviewed legal policies.

The first repeated assistant test reproduced a five-per-15-minute authentication limiter incorrectly reused for chat. The current candidate contains its dedicated tenant/user eight-per-minute repair. Final repeated-question outcomes are recorded separately in TEST_RESULTS.md; HTTP 200 fallback is not counted as a model-generated answer.

Rollback: no live routing rollback is necessary because no candidate was promoted. Stop using the intelligence URL. The previous auto-review candidate and live V3 allocations remain available; changing any tag or live traffic requires the corresponding authorized release action. Preserve audit rows and original evidence. Do not delete shared V3 financial records to roll back UI code.
