# Manual adjustment boundary

Existing invoice edits and return working-paper approval remain in place.
The new comparison/correction flow does not provide a general ledger adjustment
engine. Do not describe it as completing all requested accountant adjustments.

A future adjustment must bind business, registration, period, original snapshot
fingerprint, adjustment type, original/proposed/difference values, evidence,
reason, rule version, maker, checker and timestamps. Approval must require a
different authorized actor and optimistic version check. Locked periods require
a separately approved later-period amendment, never mutation of a filed snapshot.

ITC reversals/reclaims, RCM, interest, fees and statutory ledger opening balances
need independently verified legal rules and source evidence. Arbitrary totals
must not become approved return lines. Current working-paper exports remain
draft/internal artifacts under existing synthetic-tenant restrictions.

Status: existing preparation/approval retained; comprehensive adjustment model,
UI, additive migrations and scenario acceptance remain NOT_IMPLEMENTED.
