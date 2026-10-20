# Filing lifecycle boundary

Authorized GST registration and period → applicable form → source evidence →
validation → liability/ITC reconciliation → discrepancy resolution → draft →
independent review → maker/checker approval → immutable snapshot → verified
official schema → explicit authorized submission → acknowledgement verification →
ledger reconciliation → filed lock → later amendment.

Existing working-paper states and approvals are retained. The steps after
internal approval are not automatically available. Only verified official
acknowledgement may establish filed status. A stale source fingerprint invalidates
approval/export readiness. Test tenants retain existing restrictions.

Every mutation needs actor, timestamp, version, reason and evidence. Neither an
LLM nor a connector may bypass approval. Comprehensive adjustments remain a gap;
see docs/v3/MANUAL_ADJUSTMENTS.md.
