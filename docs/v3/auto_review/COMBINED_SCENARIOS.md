# Combined scenarios
Executed deterministic combinations: wrong total plus GSTIN; wrong tax head plus unavailable policy; missing original plus duplicate; low extraction confidence plus wrong tax; corrected/resubmitted state plus wrong total; wrong period plus credit note; wrong recipient GSTIN plus duplicate. High extraction confidence plus unavailable GST policy still requires manual review. Reverse charge plus unresolved ITC is retained for manual review and ITC remains pending. The first five combinations assert multiple reasons; the new cases assert the specific safety gates available in the current model. None authorizes automatic approval.

Pending full fixtures: blurry scan plus wrong percentage; changed filename/date duplicate; mixed rates plus invoice discount; credit note plus statement mismatch; driver/vendor settlement conflict; concurrent editing during selected batch; partial Cloud Tasks dispatch and replay; inclusive mixed-rate error; supplier identity mismatch plus duplicate original. The new tests cover only bounded safety behavior for high confidence with unavailable policy, period plus note, and RCM plus unresolved ITC; complete combined end-to-end acceptance remains pending.

No passing check is allowed to erase an accumulated critical reason. Nine bounded combinations run; full requested 15-case coverage is not claimed.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
