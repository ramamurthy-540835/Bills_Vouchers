"""GST compliance workflow constants and score helpers for CA firms."""

from decimal import Decimal

RETURN_TYPES = ("GSTR-1", "GSTR-1A", "GSTR-3B", "GSTR-2B", "IMS", "CMP-08", "GSTR-4", "GSTR-9", "GSTR-9C")
RETURN_STATUSES = (
    "not_started",
    "data_pending",
    "preparing",
    "errors_found",
    "reconciliation_pending",
    "ready_for_review",
    "reviewed",
    "client_approval_pending",
    "ready_to_file",
    "filed",
)
WORKFLOW_STEPS = ("import", "validate", "fix_errors", "reconcile", "prepare", "ca_review", "client_approval", "ready_to_file", "filed")


def gst_health_score(*, pending_returns: int, overdue_returns: int, mismatch_count: int, itc_at_risk: Decimal, approval_pending: int) -> int:
    """A transparent, bounded operational score—not a statutory GST assessment."""
    deductions = pending_returns * 4 + overdue_returns * 12 + mismatch_count + approval_pending * 3
    if itc_at_risk > Decimal("0"):
        deductions += min(20, int(itc_at_risk // Decimal("50000")) + 1)
    return max(0, min(100, 100 - deductions))
