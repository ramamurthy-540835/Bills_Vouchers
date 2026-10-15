# GST Easy preview guide

Dashboard: select a month, quarter or financial year in Dashboard period. Confirmed sales/purchases include tax and signed credit notes. Review counts and reconciliation indicators link to supporting reports; the monthly table opens the exact bills or return workflow. Quarter/year cash estimates sum independent monthly calculations and do not carry credit between months. Refresh dashboard reloads current evidence; a failed refresh is explicitly labelled and retains previously loaded values.

Mobile verification: if SMS service is unavailable, your number remains unverified and the page explains the limitation. A configured provider must actually approve a valid code before the account can show Verified.

1. Sign in with an existing authorized account. Registration asks for full name, email, country/mobile, business name, password and confirmation. Real email verification requires configured delivery. Never share passwords in support reports.
2. Open Business onboarding from the account menu. Save progress, complete business details and manage the private logo. GSTIN format validation does not prove government registration.
3. Owners can invite staff from Workspace access. Invitations bind to the invited verified email. Revoked memberships lose business access.
4. Upload supported invoices in Bills. Open Review, compare the original, correct fields and save. Sum line totals adds the entered values; verify the result against the invoice. Confirm only after checks pass. Rejection requires a reason.
5. Upload history lists durable processing jobs. Use Retry saved upload for a failed job or an eligible new-protocol job inactive for 35 minutes; saved originals and extraction progress are retained. Active jobs cannot be manually retried. Deleted bills can be restored for review; they need confirmation again. Original evidence and audit remain retained. Frozen periods reject bill changes.
6. Returns & Credit imports the supported B2B GSTR-2B scope. Dates and explicit availability matter. Unsupported populated sections are rejected. History retains authorized original statements and version evidence.
7. Expand a reconciliation case to compare evidence and view review history. Authorized accountants/tax administrators can record a reasoned decision. A reviewed label does not resolve a mismatch or approve ITC. Refresh stale evidence before deciding. Saving a decision invalidates an older return snapshot; prepare it again before approval.
8. Prepare a return snapshot, then submit it for review. A different tax administrator must approve it. Reopen requires a reason. An approved working paper is not a verified government upload or proof of filing.
9. Search and the assistant use the selected business and period. The assistant is read-only and uses limited retrieval; rely on deterministic reports and source documents for figures.

The preview has incomplete release gates. Credit-ledger coverage, official exports, verified email delivery and SMS configuration, genuine-client UAT and accountant acceptance are still required for the intended full client-ready scope.

Reports: choose Reports in navigation, select a report and month/quarter/financial year, and download Excel or CSV. The tax-head summary also supports PDF. Invoice IDs open the corresponding bill. Excel provenance includes source versions and hashes. Monetary columns are decimal text to retain precision; account for that when doing spreadsheet calculations. Exports regenerate current evidence. Quarter/year views preserve separate monthly estimates and do not include an opening/carry-forward credit ledger.
