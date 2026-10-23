# Auto Review policy
Only an authorized bill reviewer can change business policy. enabled defaults false; scope defaults both but has no effect until explicitly enabled. Policy version, actor and timestamp are audited. Existing invoice-level OFF choices with an explicit request timestamp remain exclusions.

Auto-confirmation requires canonical required fields and identity, exact-cent tax-head arithmetic and summed totals, duplicate exclusion, retained original evidence, writable period, current membership and a unique effective-date approved GST/identity rule for every line. Correction/resubmission, credit/debit notes, reverse charge and cess remain manual-review boundaries.

A missing approved rule never becomes a successful check. GSTR-2B import is not a prerequisite for basic invoice confirmation, but confirmation does not grant ITC claim readiness. No government filing or automatic ITC approval is added.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
