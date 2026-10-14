# Phase 07 — Customer interface validation

New onboarding/workspace-access headings identify their pages correctly. Changing the period on settings pages preserves the current page instead of returning to the home screen. Canonical search/assistant references open the bill review drawer. Return preparation shows state, stale-source feedback, distinct reviewer actions and reasoned reopen controls. Earlier password visibility, mobile verification error handling, logo management and bill-review improvements remain.

Validation: frontend production build and ten Chromium journeys pass, including 390px navigation, password keyboard toggles, onboarding, bill duplicate/review/delete/restore, statement evidence and return review UI. Provider responses and workflow transitions in selected browser cases are mocked; backend/domain/BigQuery checks are separate.

Remaining: exhaustive screen/assistive-technology review, durable refresh/failure UX in all upload states, real notification delivery, live authenticated preview journeys and genuine-customer accessibility acceptance. This phase is not fully accepted. No schema change. Roll back paired preview images without deleting data.
