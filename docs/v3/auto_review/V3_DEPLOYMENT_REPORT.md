# V3 Invoice Intelligence candidate deployment

Status: DEPLOYED CANDIDATE, NOT LIVE RELEASED. Complete Auto Review 2.0 acceptance remains incomplete.

- Source branch: GST_NEW_V3
- Runtime source commit: 7133d767b5af2a5a67d34c1b5ca47f3ab4ccd6c9
- Successful final Cloud Build: c47c4e06-cfb8-4bfd-8a81-5b1d6c65719e
- API revision: gst-easy-v3-api-00011-viy
- Web revision: gst-easy-v3-web-00010-vam
- Candidate web: https://intelligence---gst-easy-v3-web-foovqasysa-el.a.run.app/login
- Candidate API: https://intelligence---gst-easy-v3-api-foovqasysa-el.a.run.app
- API immutable image: asia-south1-docker.pkg.dev/aidirac-503309/gst-easy-v3/api@sha256:e3b835b6a81359c7fdd1c29be8067fc687a0c56e44c33ff1c03c67e8773fc6c3
- Web immutable image: asia-south1-docker.pkg.dev/aidirac-503309/gst-easy-v3/web@sha256:deda00aad77bb1f9f993fda3b640c95a81012fc9b067506f05112a7e2003d1f1

Earlier successful builds: 6bd9b889-1ff1-41eb-922d-6971d97c6d68 (55412be; first tested candidate), 789c63a0-274b-409b-adc1-e234be85a385 (f25f508; superseded before deployment by the parallel-loading build). Build logs are available in Google Cloud Build for project aidirac-503309 using those IDs.

Only gst-easy-v3-api and gst-easy-v3-web were deployment targets, with --no-traffic and tag intelligence. Existing auto-review tags were retained. V3-specific datasets, private bucket, service accounts and authenticated worker audience were checked by the release script. No live approved GST policies were seeded. Existing additive CREATE-IF-NOT-EXISTS V3 migrations were reapplied; no financial schema or customer data migration was run.

The strict all-project preservation assertion FAILED on prism-frontend: baseline revision prism-frontend-00027-nur became prism-frontend-00030-nuh with a different traffic mapping. No command in this release targeted that service. It was not reverted. Therefore an assertion that every project service remained unchanged would be false. The separate read-only comparison verified unchanged V2, bills-voucher, bills-voucher-web and other captured services, and preserved V3 live traffic/prior tags. Evidence: artifacts/intelligence-v3/preservation-diff.json. Final comparison passed for protected GST services and existing V3 traffic; artifacts/intelligence-v3/preservation-final.json retains all_project_services_unchanged=false for the unrelated drift.

Final live candidate acceptance passed: authorized login/navigation; policy default OFF and persistence; durable existing-bill batch processing with four manual exceptions; explicit individual exclusions surviving a later business-level batch; responsive intelligence views; unchanged confirmed financial status; inherited future ON and explicit future OFF CSV uploads; original-byte retention; deterministic assistant evidence; and policy reset to OFF. Synthetic test records remain as manual-review evidence in the authorized demo business. Auto-confirmation with an approved synthetic policy passed locally only; live automatic confirmation is blocked by missing reviewed legal policies. Evidence: artifacts/auto-review-v3/intelligence-live-acceptance.json.

The first repeated assistant test reproduced a five-per-15-minute authentication limiter incorrectly reused for chat. The current candidate contains its dedicated tenant/user eight-per-minute repair. Final repeated-question outcomes are recorded separately in TEST_RESULTS.md; HTTP 200 fallback is not counted as a model-generated answer.

Rollback: no live routing rollback is necessary because no candidate was promoted. Stop using the intelligence URL. The previous auto-review candidate and live V3 allocations remain available; changing any tag or live traffic requires the corresponding authorized release action. Preserve audit rows and original evidence. Do not delete shared V3 financial records to roll back UI code.
