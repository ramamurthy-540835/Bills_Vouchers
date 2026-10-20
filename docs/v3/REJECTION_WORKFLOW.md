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

Remaining: notification delivery, replacement-evidence revision workflow,
dedicated correction queue and material-difference maker/checker policy.
Existing invoice audit versioning is reused; no rejected invoice is deleted
automatically.
