# Rejection and correction

The existing financial statuses remain compatible. Additive correction metadata
records rejected, correction_requested, corrected, resubmitted and approved.
Rejected records remain excluded from confirmed financial totals throughout
correction. Original evidence and normal invoice audit writes are retained.

The reviewer selects a supported rejection category and reason. Rejected edits
require a correction request; saving valid edited details marks corrected.
Resubmission requires existing invoice validation and duplicate checks. It moves
to needs_review, never directly to confirmed. Confirmation uses the existing
permissions, validation and period locks.

Correction actions require If-Match; absent versions return 428 and stale
versions return 409. Backend tests cover unauthorized actions, version conflict,
rejected-edit blocking, request/edit/resubmit/confirm and retained original data.
The UI provides separate accessible rejection category/reason controls,
correction reason, status, comparison and audit disclosure.

## Dedicated correction queue

Bills & Vouchers now provides a lazily loaded correction queue scoped to the
selected business and period. It filters active, rejected, correction requested,
corrected, resubmitted and approved corrections. Each entry opens the existing
authorized review dialog and shows recorded rejection/correction reasons.

The read-only `/api/gst/bills/corrections` endpoint checks existing bill-read
permission, uses parameterized tenant/period/state queries and returns 50 rows
per page with a lookahead. Legacy rejected invoices without correction metadata
remain visible. Confirmed approved corrections appear only in the approved filter,
not the active queue. This view does not create financial records or change totals.
Pagination reflects current data; refresh returns to the first page after changes.

Loading, genuine empty results and API failure/retry are separate UI states.
Changing business/period resets queue state, and stale requests cannot replace
new results. Existing edit/confirm permissions, version checks and period locks
continue to govern all actions in the review dialog.

Remaining: notification delivery, replacement-evidence revision workflow and
material-difference maker/checker policy.
Existing invoice audit versioning is reused; no rejected invoice is deleted
automatically.
