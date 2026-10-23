# Candidate deployment status
Not deployed for this change at this report revision. Existing live V3 traffic and prior auto-review candidate remain unchanged. New candidate tag reserved: intelligence. The wrapper scripts/release_v3_intelligence_candidate.py reuses the reviewed V3 release mechanism with a separate artifact directory and tag.

The release must build the exact pushed commit, deploy immutable digests without traffic, pair candidate web/API and worker URL, retain existing tags, and verify all other service configurations against the captured snapshot. No live promotion is authorized.

Incomplete advanced valuation and scenario coverage preclude declaring this a complete enterprise release. Candidate functional testing does not waive these gaps. Rollback is to cease using the candidate; existing live revision allocations must remain unchanged.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
