# Invoice Intelligence UI
The Bills page has a keyboard-accessible business switch, existing/future/both scope selector, real period counts and durable batch progress. Requires Attention is rendered only when pending exceptions exist. It offers category filtering, 20-row pagination, two readable reasons, expandable codes and the existing review dialog.

Counts include auto-confirmed invoices, pending manual-review invoices, active file work and duplicate/failed attempts. Duplicate/failed is a mixed operational count, not a financial invoice total. Progress details use the latest job history; aggregate job counts query the whole period.

Desktop and mobile synthetic browser screenshots: artifacts/auto-review-v3/intelligence-1440.png, intelligence-768.png and intelligence-390.png. Four status columns become two on smaller screens. Bulk opt-in, per-file exclusion and existing review actions remain available.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
