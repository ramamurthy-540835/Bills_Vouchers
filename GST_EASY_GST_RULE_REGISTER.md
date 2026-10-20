# Versioned GST rule register design

Required record: rule_id, act, section, rule, notification, effective_from,
effective_to, taxpayer_type, business_scenario, calculation, required_evidence,
official_source, last_verified, review_status, rule_version and reviewer evidence.

A rule cannot participate in automatic legal conclusions until its effective
interval and taxpayer applicability are verified and independently approved.
Missing, overlapping or stale rules must return professional-review required.
Historical transactions use their effective-period rules, never today's rate by
default. Council recommendations alone are not activated rules.

The new arithmetic rule declared-rate-arithmetic-1 checks arithmetic only. It has
legal_rate_verified=false. No statutory rules are falsely marked approved.
The 50-scenario workbook is the review inventory, not an executable legal engine.
