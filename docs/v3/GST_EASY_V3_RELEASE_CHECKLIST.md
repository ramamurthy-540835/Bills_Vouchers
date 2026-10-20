# V3 release gates

- Branch GST_NEW_V3 derives from reviewed V2 commit 14df23a305826df0f5024ebd10705555045a9185.
- V2 branch and all existing build files must remain unchanged.
- New resource preparation completed: isolated schemas, buckets, queues, identities
  and secrets; no financial rows or V2 customer rows seeded.
- New build file: cloudbuild-gst-easy-v3.yaml.
- Deploy only after the remote V3 commit matches source and both images have
  successful immutable digests.
- `deploy_gst_new_v3.py` refuses any pre-existing requested V3 service and any
  existing-service configuration/IAM drift.
- Before live testing, verify new frontend targets only new API; API uses only V3
  datasets/bucket/queues/session secret and private worker authorization.
- Test email only to explicitly authorized recipients. The owner subsequently
  authorized a Gmail recipient and confirmed delivery, sign-in and dashboard.
- Government filing and live connector activation remain unavailable.
- This is an engineering preview, not a legally certified client-ready release.

Actual build IDs, image digests, revisions, URLs and preservation results are in
GST_EASY_V3_DEPLOYMENT_REPORT.md. Independent deployment is verified.
Client-ready acceptance is NOT achieved: recovery/bounce handling and full
authenticated financial acceptance remain pending. The broader
adjustment/consolidation/connector and legal-review gaps remain recorded in
GST_EASY_IMPLEMENTATION_STATUS.md. Source mapping/reconciliation was released
from 6f7c45f with storage integration and live access-boundary evidence.
