"""Versioned, public guidance only. Never put tenant values in this catalogue.

Answers are deliberately bounded; conditional legal questions collect facts rather
than impersonating a professional determination. Portal navigation is guidance,
not an integrated submission. Reviewed against official portal references 2026-10-29.
"""
import re
from dataclasses import dataclass

VERSION = '2026-10-29.1'
PORTAL = 'https://www.gst.gov.in/'
MANUALS = 'https://tutorial.gst.gov.in/userguide/returns/index.htm'
TAX = 'https://taxinformation.cbic.gov.in/'


@dataclass(frozen=True)
class Scenario:
    id: str
    question: str
    answer: str
    category: str


# Ten independently addressable intents per category; metrics are filled only by
# the authoritative summary handler, never by strings or guessed calculations.
GROUPS = {
'A': ('GST basics', '''What is GST and how does it apply to my business?|GST concerns supplies of goods/services. Determine registration, supply classification and the transaction period before assessing obligations.
What is the difference between CGST SGST UTGST and IGST?|These are different GST tax heads. Ordinary domestic treatment depends on supplier location and legally determined place of supply; special rules can change the outcome.
What is the difference between inward and outward supplies?|Inward supplies are received by the business; outward supplies are made by it. The same invoice may be outward for the supplier and inward for the recipient.
What is taxable value?|Taxable value is the base used for tax calculation after applicable valuation adjustments. It is different from a tax-inclusive invoice total.
What is the difference between input tax and output tax?|Input tax relates to inward supplies; output tax relates to outward supplies. Recording input tax does not alone establish eligible credit.
What is input tax credit?|ITC is eligible input tax available under applicable conditions and restrictions. It is different from the full purchase invoice value. Ask for usable ITC to inspect your application figure.
How do taxable nil rated exempt zero rated and non GST supplies differ?|These classifications have different tax and credit consequences. Provide the supply description, transaction date and relevant evidence before choosing a classification; zero-rated does not mean every exempt supply.
What are HSN and SAC codes?|HSN classifies goods and SAC classifies services. A description or code alone is insufficient to guarantee a statutory rate; date, conditions and notifications matter.
What is the difference between a tax invoice and a bill of supply?|The appropriate document depends on the supplier and supply treatment. Do not use a bill of supply as proof that GST was charged and is creditable.
How are invoice confirmation ITC eligibility and return filing different?|Confirmation records an application review decision. ITC needs separate eligibility/reconciliation checks. Filing requires an authorized government process and acknowledgement.'''),
'B': ('Registration', '''Does my business need GST registration?|Provide state, activities, turnover period, supply types and any compulsory-registration facts. Registration cannot be decided from turnover alone without the applicable rules.
Which GST registration category applies to my business?|Share the business activity and whether it involves composition, ISD, TDS/TCS, SEZ, non-resident, OIDAR or UIN treatment. Eligibility needs period-specific review.
What information is saved in my GST business profile?|Open the account menu, Business Profile and inspect the selected business identity, registration, address, contacts, website and preferences. Missing optional fields are not fabricated.
Is my saved GSTIN structurally valid?|Use the GST registration/checks panel in Business Profile. Format/checksum checks are different from a live registration or ownership verification.
Has my GST registration been verified against an authorized provider?|Inspect Business Profile verification source, time and outcome. If automatic verification is unconfigured, no provider verification can be claimed; opening the portal is not verification.
Do I need separate registration for operations in another state?|Provide states, establishments and activities. Additional-state registration is a legal applicability question, not an automatic consequence of any interstate sale.
Can one business have multiple GST registrations?|Separate registrations can require separate books/obligations. The current selected-business context must be preserved; do not merge records solely because a PAN or name matches.
How do regular and composition taxpayers differ?|Their eligibility, documents, credit and returns differ. Verify current scheme eligibility before changing a profile; do not apply regular-taxpayer ITC assumptions to composition.
What happens when registration is cancelled?|Check the effective date, pending obligations, final-return applicability and cancellation order. Cancellation does not establish that all past compliance is complete.
How do I update business details safely?|Select the intended business, open Business Profile, edit permitted fields and save. Check success and refresh. GSTIN edits may require separate permission.'''),
'C': ('Invoice checks', '''Is the GST arithmetic on this invoice correct?|Open the identified invoice, compare the original and run the review validation. Supply the invoice reference; a statement of arithmetic accuracy is not legal rate approval.
Does the invoice total match taxable value tax and adjustments?|Use invoice review to compare line totals, tax heads, charges and documented round-off against the original. Identify the invoice; do not insert an unexplained adjustment to force a match.
How do I calculate GST when the price excludes tax?|For a simple single-rate example, tax equals taxable value multiplied by the applicable rate divided by 100. Supply values and the approved rate; do not assume 18% for every supply.
How do I extract GST from a tax inclusive amount?|For a simple single-rate inclusive price, base equals total divided by (1 + rate/100); tax is the difference. Mixed rates, cess and extra charges require separate treatment.
How should a discount affect taxable value?|Provide when the discount was agreed, invoice treatment, linkage and any credit-note facts. Not every post-sale discount automatically reduces GST value.
How should freight insurance and handling charges be treated?|Provide who charges them, contractual terms, invoice presentation and supply classification. Charges cannot be classified for GST solely by their label.
How do I check an invoice containing multiple tax rates?|Review each line with its own taxable value, approved rate and tax heads, then aggregate. Do not apply an average rate to the invoice total.
Should this invoice use IGST or CGST with SGST UTGST?|Provide supplier location, legally determined place of supply, supply type and special facts such as SEZ/export treatment. Customer postal address alone is not always decisive.
Why does the system show a rounding or tax head mismatch?|Open Validation Details and compare each line and total with the original. Resolve the specific code; do not silently rewrite source evidence.
What evidence confirms the applicable rate on the invoice date?|Provide description, HSN/SAC, invoice date and conditions/exemptions. A professional should verify the effective notification before material rate decisions.'''),
'D': ('Sales', '''What are my confirmed sales for the selected period?|Open the Sales Register for the selected period. The confirmed invoice-value metric includes tax and signed note effects; it is different from taxable sales.
What are my taxable sales and output GST by tax head?|Use the sales/tax-head report with the same period. Taxable value and invoice value must be labelled separately; unavailable subtotals must not be guessed.
Which sales invoices are pending review or rejected?|Open Bills and Vouchers and filter status and sales direction. Rejected and pending records must not be included as confirmed sales.
What are my recorded B2B and B2C sales?|This needs supported customer-registration classification and a dedicated register breakdown. Do not infer registered status from a customer name.
What are my intrastate and interstate sales?|Use classified sales evidence with place-of-supply validation. If the breakdown is unavailable, review the Sales Register rather than inferring it from addresses.
Which customers account for the highest confirmed sales?|This requires an exhaustive grouped sales query. The assistant's small evidence sample cannot establish a complete ranking; use a supported report.
How have sales credit notes affected my totals?|Inspect confirmed credit notes and their period/sign in the Sales Register. Do not count a credit note as an additional positive sale.
How should a debit note affect sales records?|Link the original transaction and check reason, date, taxable value and tax increase. Review the note through normal confirmation and period controls.
How should advances and later invoice adjustments be treated?|Provide goods/services classification, dates and existing advance/invoice records. Do not treat every receipt as a fresh taxable sale.
Why do my sales register and return working paper differ?|Compare scope, status, notes, adjustments and source versions. Reprepare a stale paper only after investigating the difference.'''),
'E': ('ITC', '''What are my confirmed purchases for the selected period?|Open Purchase Register. Confirmed invoice value includes tax and signed notes; unconfirmed records are excluded.
How much ITC is currently usable?|Ask for usable ITC in the selected period. It is an application-calculated amount subject to source coverage and statutory eligibility, not a guarantee of a portal claim.
What is my usable ITC split by tax head?|Use the current tax-head summary. IGST, CGST, SGST/UTGST and cess must remain separate.
Which purchases have no usable ITC?|Open Purchases Without ITC and inspect each reason and source. Absence of usable credit is not always permanent ineligibility.
Which credits are blocked deferred or pending evidence?|Use credit decisions and their rule references. Reconciliation delays, blocked categories and missing evidence are separate reasons.
Can I claim ITC on capital goods?|Provide business use, asset details, depreciation/tax treatment, supply mix and documents. Capital goods do not create an unconditional credit entitlement.
How should personal exempt and business use be separated?|Identify the actual use and relevant period. Mixed use may require apportionment/reversal calculations and supporting evidence.
What happens if supplier payment conditions are not met?|Provide invoice, receipt/payment dates and credit already availed. Any reversal/reclaim requires the applicable period-specific conditions, not a guessed deadline.
Which ITC reversals or reclaims need review?|Inspect reversal/reclaim evidence and reasons. If the records are not captured, the assistant cannot claim a complete list.
What time limits affect this ITC claim?|Provide invoice/debit-note date, financial year, return history and special facts. Verify effective statutory limits and exceptions professionally before claiming.'''),
'F': ('Reconciliation', '''Has GSTR 2B been imported for this period?|Check Returns and Credit statement status for the selected GSTIN and period. A missing statement prevents statement-based matching conclusions.
Which purchases match the imported statement?|Use Reconciliation Cases with the matched filter and inspect evidence. A match is not complete ITC eligibility approval.
Which purchases are in books but not GSTR 2B?|Use books-only cases after a statement is imported. Check supplier reporting, period and invoice identity before deciding credit treatment.
Which statement records are missing from books?|Use statement-only cases. Request the missing original or investigate incorrect association; do not invent a purchase record.
Which invoices have amount or tax head mismatches?|Use mismatch cases and compare the original, statement and book values. Keep amount and tax-head differences distinct.
Could punctuation explain an invoice number mismatch?|Punctuation can suggest a candidate, but validate GSTIN, date, amounts and duplicate identity before treating it as matched.
Are there duplicate reconciliation candidates?|Inspect duplicate candidates and source versions. Do not count multiple rows for the same logical invoice as independent credit.
Why does a credit note differ between books and statement?|Compare note identity, original linkage, date, signed amounts and the relevant statement generation version.
What do IMS accept reject pending and no action mean?|IMS treatment depends on document type and applicable period. Internal review is not a submitted government IMS decision; use the current official IMS guidance.
Does a GSTR 2B match automatically approve ITC?|No. Matching is evidence; eligibility, restrictions, documents and other statutory conditions remain separate checks.'''),
'G': ('Special supplies', '''Could this transaction attract reverse charge?|Provide supply description, supplier/recipient category, date and notification facts. Do not infer RCM solely from an unregistered supplier.
What is my recorded reverse charge liability?|Use supported RCM records and the working paper. If those records are not captured, an ordinary sales total is not a substitute.
When can reverse charge tax become eligible ITC?|Check actual payment, receipt, documents, business use and restrictions under applicable rules. Liability recognition alone is insufficient.
What facts determine transport or GTA treatment?|Identify the provider, consignment-note facts, recipient category, service date, chosen treatment and applicable conditions. The word freight alone cannot determine the rate.
How should imported goods be recorded?|Keep bill-of-entry and import tax evidence alongside the purchase. Do not substitute supplier invoice tax for actual import IGST evidence.
How should an import of services be assessed?|Provide supplier/recipient location, service description, place-of-supply facts and consideration. Cross-border treatment requires case-specific review.
How do exports with and without payment of IGST differ?|Confirm export eligibility, relevant period, LUT/bond and payment/refund conditions. Do not classify a foreign customer alone as a qualifying export.
What evidence supports supplies to an SEZ?|Check recipient status, authorized-operation evidence, supply documents and applicable treatment. SEZ tax handling needs separate review.
How should branch transfers or job work be reviewed?|Identify ownership/registrations, movement, documents and return timeline. Not every stock movement is the same taxable event.
What GST facts matter for e commerce settlements?|Separate sales, returns, commission, operator liabilities, TCS and payments. A net settlement is not automatically taxable turnover.'''),
'H': ('Returns', '''Which GST returns apply to my taxpayer category?|Confirm registration type, period and frequency. Regular, composition, ISD, TDS/TCS, non-resident, OIDAR and UIN obligations differ; ask for the specific form guide.
What outward supply information belongs in GSTR 1?|Classify sales, notes and amendments using the applicable form tables. Ask how to file GSTR-1 for the portal sequence.
What is GSTR 1A and when is it relevant?|It is a same-period correction/addition facility subject to its permitted window and prerequisites. Ask for the GSTR-1A guide; do not assume GSTR-3B is freely revisable.
What figures support GSTR 3B preparation?|Reconcile sales liability, RCM, eligible credit, reversals and payment facts. Ask how to file GSTR-3B for guided portal stages.
Do my GSTR 1 and GSTR 3B figures reconcile?|This needs actual return versions, scope and adjustments. Application working papers alone do not prove what was filed on the portal.
What should I check before a nil return?|Check all relevant supply, liability, credit and adjustment facts against the form's eligibility conditions. Zero recorded sales alone does not prove nil eligibility.
How do QRMP and IFF affect reporting?|Check opted frequency, relevant month and records already furnished. Do not report IFF invoices a second time in the quarterly reconciliation.
What is needed for CMP 08 and GSTR 4?|Verify composition applicability, quarter/year, payment statements, books and RCM facts. Ask for either form's portal guide.
What supports annual GSTR 9 and GSTR 9C reconciliation?|Gather books, filed returns, notes, tax/credit adjustments and payment evidence. Check year-specific applicability before preparation.
What is preventing my working paper review?|Open the current preparation exceptions and source versions. Resolve validation, stale inputs and permissions before submission.'''),
'I': ('Payments', '''What is my estimated GST cash requirement?|Use the selected-period application calculation. It is not proof of payment or a full opening/carry-forward portal ledger position.
How much liability is covered by usable credit?|Use the supported tax-head utilization summary with the same period. Do not subtract a total credit pool indiscriminately from all liabilities.
How do cash credit and liability ledgers differ?|Cash ledger records deposits/use, credit ledger records eligible credit/use and liability register records obligations. Obtain authoritative ledger evidence for actual balances.
What opening balances are needed for payment assessment?|Gather tax-head opening balances, liabilities, utilization and adjustments. Quarter/year application estimates do not supply a complete carry-forward ledger.
How may credits be utilized?|Credit utilization is tax-head and effective-rule dependent. Use approved backend calculations and current ledger facts; do not invent cross-head set-off.
Why does estimated cash differ from the portal?|Compare opening balances, actual liability, eligible credit, RCM, interest/fees, payments and period. The application estimate is not the official ledger.
What are PMT 06 and a challan?|They support depositing amounts into the cash ledger. Deposit is distinct from offsetting liability and filing; ask how to create a challan for guidance.
What proves payment was credited?|Check bank/payment reference, portal challan/CIN status and ledger credit. A bank debit or generated challan alone is not filing proof.
Could interest apply to my delay?|Provide liability, credit/payment, due-date and actual discharge facts. Use the applicable rules and notified relief; no flat guess is appropriate.
Could late fees extensions or waivers apply?|Provide form, taxpayer type, state and period. Verify the applicable notification rather than using a permanent hardcoded deadline.'''),
'J': ('Cases and special taxpayers', '''Which refund category fits my case?|Describe the transaction, tax/payment facts and refund reason. Eligibility, limitation and documents depend on category; ask for RFD-01 navigation.
What evidence supports export or SEZ refunds?|Collect relevant supply, export/SEZ, tax/credit and realization evidence as applicable. Required documents vary by category and period.
What is needed for an inverted duty refund?|Provide supply/rate classifications, inputs, output and credit records. Do not infer eligibility solely because purchase tax exceeds sales tax.
How can excess cash ledger balance be reviewed for refund?|Obtain the actual cash ledger and relevant liability/payment evidence before preparing the applicable refund request.
What is my refund application status?|Use the official ARN/status or authorized imported evidence. GST Easy cannot claim a live portal status without that evidence.
What does this notice require and what deadline is shown?|Supply a redacted notice and its dates/reference. Identify the requested documents and obtain professional review; do not invent an extension or reply.
What records support a discrepancy reply?|Gather the notice, period-specific books, filed returns, reconciliation, payment and original evidence. Explain differences with traceable versions.
What should an ISD check for GSTR 6?|Review received credit, eligible distribution, recipients and amendments under current rules. Use the GSTR-6 portal guide for navigation.
What obligations apply to TDS TCS non resident OIDAR or UIN taxpayers?|Specify your registration category and form: GSTR-7, GSTR-8, GSTR-5, GSTR-5A or GSTR-11. Each has separate eligibility and preparation requirements.
What needs review for cancellation revocation or final return?|Identify the order/application, effective date and pending obligations. Ask for cancellation, revocation or GSTR-10 guidance separately.'''),
'K': ('Application help', '''How do I upload purchase and sales bills?|Choose the correct business/period, open Bills and Vouchers, Upload Bills, select supported files and submit once. Review direction, evidence and extracted values before confirmation.
Which invoice formats are supported?|The invoice uploader supports PDF, JPEG/JPG, PNG, XLSX and CSV within displayed limits. Use the expected spreadsheet template; do not assume arbitrary ZIP or workbook compatibility.
Why is my bill still processing?|Inspect Upload History and the per-file result. Use Retry saved upload only when offered; repeated new uploads risk duplicates.
How do I correct extracted values and retain the original?|Open Review, inspect View Original Bill, edit evidence-supported fields, Save Changes and read validation. Source evidence and history must remain retained.
How do I reject request correction and resubmit?|Reject with a category/reason. Use Bill corrections, request correction, edit/save and resubmit through available controls. Resubmission is not confirmation.
What changes when Auto Review is ON or OFF?|OFF retains validation but requires manual confirmation. ON evaluates eligible bills; all hard gates still apply and missing legal policy can keep a bill manual.
How do I run Auto Review on existing pending bills?|In Invoice Intelligence enable the existing or both scope, inspect the eligible count and Run Auto Review. Up to 100 records are handled per durable batch.
Why is this invoice in Requires Attention?|Open Review and Validation Details for the specific reasons. Fix evidence-supported errors; do not force a total or bypass a policy gate.
Why was this invoice flagged as duplicate?|Compare original file identity, supplier, invoice number, date/financial year and existing record. A renamed copy is not a different invoice.
Why can I not confirm edit or approve this record?|Check membership, required permission, record status, latest version and period locks. Do not borrow another user's credentials.'''),
'L': ('Combined analysis', '''Why did usable ITC change since the previous period?|This needs two period-scoped snapshots, notes, eligibility and reconciliation decisions. The current-period evidence sample cannot prove a complete comparison.
Why did cash requirement rise even though sales fell?|Compare liability, usable credit, RCM, notes and adjustments across both periods. Do not infer the cause from sales alone.
Which suppliers have the largest unresolved differences?|Use an exhaustive grouped reconciliation report. A few retrieved invoices cannot establish a ranking for the whole business.
Which invoices have multiple issues and need review first?|Use Requires Attention filters and full validation reasons. Prioritize material identity, evidence and arithmetic failures with the authorized reviewer.
Is a GSTIN mismatch a problem when the total is correct?|Yes. Correct arithmetic cannot override a wrong business identity. Investigate the original and selected context before confirmation.
How does a credit note in another period affect review?|Check the original linkage, note date, financial year, applicable adjustment rules and filed/locked periods. Do not silently backdate it.
Is an invoice repeated in Vendor Customer and Driver feeds?|Cross-reference stable source IDs, invoice identity and booking/trip links. Payments or settlements must not create duplicate taxable invoices.
Why do dashboard export and approved snapshot differ?|Compare selected period, refresh time, status, source versions and adjustments. Exports can be current while a snapshot preserves an earlier approved version.
What changes after a filing period is locked?|Mutations are restricted. Use permitted reopening/correction procedures and record a reason; do not alter a confirmed financial record through chat.
What evidence is missing before completing this period?|Review pending invoices, statements, reconciliation exceptions, eligibility evidence and approval prerequisites. Missing portal ledgers/acknowledgements cannot be inferred from application data.'''),
}

CATALOG = tuple(Scenario(f'{category}{i:02d}', line.split('|', 1)[0], line.split('|', 1)[1], title)
                for category, (title, text) in GROUPS.items()
                for i, line in enumerate(text.splitlines(), 1))

STOP = {'what','is','the','a','an','my','our','of','for','in','to','how','do','does','i','and','can','me','please','show','are','this','it','be'}
ALIASES = {
    'what is gst':'A01', 'explain gst':'A01', 'what is taxable value':'A04',
    'what is itc':'A06', 'explain itc':'A06', 'what is hsn':'A08', 'what is sac':'A08',
    'what is a bill of supply':'A09', 'what is a tax invoice':'A09',
    'how to add a business':'B10', 'how do i switch business':'B10',
    'is gstin validation government verification':'B05',
    'how to calculate inclusive gst':'C04', 'how to calculate exclusive gst':'C03',
    'how do i upload bills':'K01', 'how to upload bills':'K01',
    'how do i reject a bill':'K05', 'how do i correct a bill':'K04',
    'what is auto review':'K06', 'why is auto review not confirming':'K08',
    'what is reverse charge':'G01', 'what is rcm':'G01',
    'why is my bill processing':'K03', 'what formats can i upload':'K02',
    'how to import gstr 2b':'F01', 'is matched itc approved':'F10',
    'what is cash ledger':'I03', 'what is credit ledger':'I03',
    'what happens after period lock':'L09',
}


def normalized(text):
    return ' '.join(re.findall(r'[a-z0-9]+', text.casefold()))


def match(question):
    query = normalized(question)
    if query in ALIASES:
        return next(s for s in CATALOG if s.id == ALIASES[query])
    exact = next((s for s in CATALOG if normalized(s.question) == query), None)
    if exact:
        return exact
    # Conservative matching: ambiguity goes to clarification/LLM, never a guessed metric.
    terms = set(query.split()) - STOP
    ranked = []
    for scenario in CATALOG:
        tokens = set(normalized(scenario.question).split()) - STOP
        score = len(terms & tokens) / max(1, len(terms | tokens))
        ranked.append((score, scenario.id, scenario))
    ranked.sort(key=lambda value: (value[0], value[1]), reverse=True)
    if len(terms) >= 3 and ranked[0][0] >= .65 and ranked[0][0] - ranked[1][0] >= .15:
        return ranked[0][2]
    return None


def guidance(question, sample=False):
    scenario = match(question)
    if scenario is None:
        return None
    return {'answer': scenario.answer, 'sources': [
        {'id': 'gst-official', 'label': 'Official GST guidance — check applicable period',
         'href': MANUALS if scenario.id[0] in 'FHJK' else TAX, 'layer': 'Reference guidance'}],
        'followups': [], 'sample': sample, 'intent': scenario.id, 'template_version': VERSION,
        'answer_mode': 'template', 'review_status': 'guidance_not_case_acceptance'}
