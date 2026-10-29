"""Progressive portal instructions; never a credential or filing tool."""
import re

from .assistant_catalog import MANUALS, VERSION, normalized

FORMS = {
    'gstr1': ('GSTR-1', 'Outward-supply statement for applicable taxpayers', [
        'Sign in yourself at gst.gov.in. Open Services > Returns > Returns Dashboard. Select financial year, quarter/month and Search. Open the GSTR-1 tile and the available preparation option.',
        'Classify B2B/B2C, exports/SEZ, notes, amendments, exempt/non-GST supplies and applicable advance, HSN and document summaries. Reconcile with books. Review auto-populated/e-invoice entries to avoid duplicates. Generate the summary, preview totals and resolve errors.',
        'After authorized review, use Proceed to File/Summary and File Statement as displayed. Choose the authorized signatory and permitted DSC/EVC method. Enter OTPs only on the official portal. Save the ARN and confirm Filed status.'
    ], 'https://tutorial.gst.gov.in/userguide/returns/Creation_of_Outward_Supplies_Return_in_GSTR-1.htm'),
    'gstr1a': ('GSTR-1A', 'Same-period additions/amendments within the permitted window', [
        'Check the period and whether the portal makes GSTR-1A available after GSTR-1 and before the applicable GSTR-3B filing. Open the relevant tile in Returns Dashboard.',
        'Add or amend only applicable records. Reconcile the revised liability, save and review the summary under the current portal validations.',
        'Obtain review, file with the permitted signing method and retain acknowledgement. Recheck GSTR-3B before filing it; do not assume an already filed GSTR-3B can simply be revised.'
    ], 'https://tutorial.gst.gov.in/downloads/news/creative_faqs_on_gstr1a_fo_cr25785.pdf'),
    'gstr2b': ('GSTR-2B', 'Auto-drafted ITC statement — view/download, not a return you file', [
        'Log in to gst.gov.in. Open Services > Returns > Returns Dashboard, choose the financial year/period and Search. Use the GSTR-2B tile to view or download.',
        'Inspect the summary and document details. Use the displayed Excel/JSON download options when needed. Check generation/version and applicable IMS recomputation before relying on a copy.',
        'Compare the statement with purchases and investigate differences. For GST Easy, use its supported canonical B2B JSON contract; a portal download may require normalization. Matching alone does not approve ITC.'
    ], 'https://tutorial.gst.gov.in/userguide/returns/FAQ_gstr2b.htm'),
    'gstr3b': ('GSTR-3B', 'Summary return and liability discharge for applicable taxpayers', [
        'Log in yourself and open Services > Returns > Returns Dashboard. Choose the period and GSTR-3B. Check applicable prerequisites and portal questions before preparing.',
        'Review applicable liability sections 3.1/3.1.1/3.2, ITC/reversals in 4, inward-supply information in 5 and applicable interest/fees/payment sections. Use the live form and current manual: not every table applies to every taxpayer. Reconcile with books and statements, preview and resolve differences with the accountant.',
        'Review actual cash/credit balances, applicable interest/fees and the portal payment/offset workflow. After final approval, file using the permitted DSC/EVC method and retain acknowledgement. A challan deposit alone is not filing.'
    ], 'https://tutorial.gst.gov.in/userguide/returns/GSTR3B.htm'),
    'gstr2a': ('GSTR-2A', 'Inward-supply reference statement — not filed by the recipient', [
        'Open the official Returns Dashboard for the selected GSTIN and period and choose the GSTR-2A view/download option available to you.',
        'Inspect supplier/document details and compare them with books. Do not assume a dynamic reference and the selected GSTR-2B version must be identical.',
        'Keep the dated copy and investigate differences. Do not treat appearance in a statement as complete ITC entitlement.'
    ], MANUALS),
}

# Specialist forms get an explicit preparation checklist, not invented field-level
# instructions. Eligibility/table details must be checked in the linked official manual.
SPECIAL = {
    'cmp08': ('CMP-08', 'Composition statement/payment', 'quarter, composition status, outward supplies and applicable RCM/payment facts'),
    'gstr4': ('GSTR-4', 'Composition annual return', 'financial year, filed CMP-08 records and annual purchase/supply reconciliation'),
    'gstr5': ('GSTR-5', 'Non-resident taxable person return', 'registration validity, inward/outward supplies and applicable liability/credit'),
    'gstr5a': ('GSTR-5A', 'Applicable OIDAR/specified cross-border return', 'taxpayer category, supply location and current form applicability'),
    'gstr6': ('GSTR-6', 'Input Service Distributor return', 'received credit, permitted distribution, recipient registrations and amendments'),
    'gstr7': ('GSTR-7', 'GST TDS return', 'deductee GSTINs, deductions, amendments and deposit evidence'),
    'gstr7a': ('GSTR-7A', 'TDS certificate, not an independently prepared return', 'filed TDS records and certificate availability'),
    'gstr8': ('GSTR-8', 'E-commerce TCS statement', 'operator applicability, supplies/returns, collections and supplier identities'),
    'gstr9': ('GSTR-9', 'Annual return', 'year-specific applicability, books, filed returns and tax/ITC reconciliation'),
    'gstr9c': ('GSTR-9C', 'Annual reconciliation statement', 'year-specific applicability and financial-statement/annual-return reconciliation'),
    'gstr10': ('GSTR-10', 'Final return where applicable', 'cancellation facts, stock/assets, liabilities and pending obligations'),
    'gstr11': ('GSTR-11', 'UIN inward-supply statement', 'UIN eligibility, inward documents and relevant period'),
    'iff': ('IFF', 'Eligible QRMP invoice furnishing facility', 'opted frequency, eligible month and invoices already furnished'),
}
for key, (name, purpose, checklist) in SPECIAL.items():
    FORMS[key] = (name, purpose, [
        f'Confirm that {name} applies to this registration and period. Check {checklist}. Open the official Returns Dashboard and select the matching available tile.',
        f'Use the current official {name} manual for its table-by-table requirements. Prepare/reconcile records and resolve validation errors. GST Easy does not claim to generate every specialist form.',
        'Use only the portal actions actually available to your role. Preview and obtain professional review; where this is a fileable form, use permitted signing and retain the official acknowledgement. For reference statements/certificates, view or download instead of filing.'
    ], MANUALS)

SERVICES = {
    'challan': ('Challan / PMT-06', 'Deposit into cash ledger, distinct from filing', [
        'On gst.gov.in open Services > Payments > Create Challan using the appropriate authenticated workflow. Confirm GSTIN, tax heads, amounts and payment mode.',
        'Generate the challan, check its reference and complete payment through the official supported method. Do not share banking credentials or OTPs in chat.',
        'Verify payment status/CIN and the cash-ledger credit. Then complete the separate applicable liability-offset and return-filing workflow; a bank debit alone is insufficient.'
    ], 'https://cbic-gst.gov.in/gst-payment-rules.html'),
    'refund': ('Refund / RFD-01', 'Category-specific refund application', [
        'Identify the appropriate refund category, period, eligibility and required evidence before using Services > Refunds on the official portal.',
        'Open the applicable application and follow its category-specific statement/document validations. Obtain specialist review rather than applying one universal refund formula.',
        'Submit only through the authorized portal process. Save ARN and track notices/status in the application; GST Easy cannot claim live status without authoritative evidence.'
    ], 'https://tutorial.gst.gov.in/userguide/refund/index.htm'),
    'ims': ('IMS', 'Official invoice-management actions', [
        'Open the official portal IMS facility for your registration. Review the applicable document categories and period-specific guidance.',
        'Compare each document with books before choosing an available action. Accept, reject, pending and no action have document/period-specific consequences.',
        'Check whether GSTR-2B recomputation is required before GSTR-3B filing. An internal GST Easy review is not a submitted government IMS action.'
    ], MANUALS),
    'ledgers': ('Electronic ledgers', 'View actual cash, credit and liability records', [
        'In the official portal open Services > Ledgers and choose the cash, credit or liability record available to your registration.',
        'Select the period and download the authoritative entries. Compare opening balance, deposits/credits, utilization and adjustments.',
        'Reconcile discrepancies against payment/return references. An application estimate cannot establish an official ledger balance.'
    ], 'https://tutorial.gst.gov.in/userguide/returns/index.htm'),
}
FORMS.update(SERVICES)

ADMIN_GUIDES = {
    'registration': ('Registration', 'Services > Registration > New Registration', 'legal identity, PAN/contact and business documents; follow the current application checklist'),
    'amendment': ('Registration amendment', 'Services > Registration and the applicable core/non-core amendment option', 'the field being changed, supporting evidence and whether approval is required'),
    'cancellation': ('Registration cancellation', 'Services > Registration and the cancellation application available to your role', 'effective date, reason, stock/liability details and continuing obligations'),
    'revocation': ('Revocation of cancellation', 'Services > Registration and the available revocation application', 'cancellation order, eligibility/window, pending returns and supporting reasons'),
    'notices': ('Notices and replies', 'Services > User Services and the relevant notices/orders or case dashboard', 'the exact notice/reference, service date, response deadline and required attachments'),
    'lut': ('LUT', 'Services > User Services and the available LUT furnishing workflow', 'financial year, eligibility, signatory and required declarations'),
    'qrmp': ('QRMP', 'Services > Returns and the quarterly-return opt-in/opt-out facility', 'eligibility, opting window, frequency and records already furnished through IFF'),
    'einvoice': ('E-invoicing', 'the authorized Invoice Registration Portal linked from official GST resources', 'effective-date applicability, supply/document class and current schema; IRN generation is not a GST return filing'),
    'eway': ('E-way bill', 'the official e-way bill system linked from GST resources', 'movement, value, parties, document and vehicle/transporter facts under applicable rules'),
}
for key, (name, path, facts) in ADMIN_GUIDES.items():
    FORMS[key] = (name, 'Official portal task guidance', [
        f'Check {facts}. Sign in yourself and open {path}. Use the current official manual when a menu differs.',
        'Complete only the relevant fields and document checklist; save and review the draft. Resolve portal validation and seek specialist review for legal applicability before submission.',
        'Use the authorized portal confirmation/signing method and retain the resulting reference and status. A saved application is not an approved registration, accepted reply or completed filing.'
    ], 'https://www.gst.gov.in/')


def portal_answer(question, previous=None, sample=False):
    query = normalized(question)
    query = re.sub(r'\b(gstr|gst)\s*(\d+)\s+([abc])\b', lambda m: m[1]+' '+m[2]+m[3], query)
    compact = query.replace(' ', '')
    if 'import' in query and re.search(r'\b(?:gst|gstr)\s*2b\b', query):
        return {'answer':'In GST Easy, select the business and period, open Returns & Credit > Reconciliation Evidence > Import GSTR-2B, and choose supported canonical B2B JSON. Resolve GSTIN/period/duplicate errors, then inspect refreshed cases. A raw portal download may need normalization; arbitrary Excel and unsupported sections are not covered. Import does not approve ITC.',
                'sources':[], 'followups':['How do I download GSTR-2B?'], 'sample':sample, 'answer_mode':'template'}
    if re.search(r'\b(?:gst|gstr)\s*1\s*b\b', query):
        return {'answer': 'Do you mean GSTR-1 (outward supplies), GSTR-1A (same-period corrections) or GSTR-3B (summary liability/payment)? Please choose one; I will guide only that task.',
                'sources': [], 'followups': ['How do I file GSTR-1?', 'How do I file GSTR-3B?'], 'sample': sample, 'answer_mode': 'clarification'}
    topic = None
    step = 0
    if query in {'next','next step','continue','previous step','back'} and not (previous and previous.get('portal_topic') in FORMS):
        return {'answer':'Which form or portal task should I guide? Start with a named form, for example GSTR-1, GSTR-3B or downloading GSTR-2B.',
                'sources':[], 'followups':['How do I file GSTR-1?','How do I download GSTR-2B?'], 'sample':sample, 'answer_mode':'clarification'}
    if query in {'next','next step','continue','previous step','back'} and previous and previous.get('portal_topic') in FORMS:
        topic = previous['portal_topic']
        step = max(0, min(2, int(previous.get('portal_step', 0)) + (-1 if query in {'previous step','back'} else 1)))
    else:
        matches = [key for key in FORMS if key.startswith(('gstr','cmp')) and
                   re.search(r'(?<![a-z0-9])' + re.escape(key).replace('gstr',r'(?:gstr|gst)\s*').replace('cmp',r'cmp\s*') + r'(?![a-z0-9])', query)]
        # Bound form detection, so GSTR-1 never captures GSTR-1A or GSTR-11.
        matches = list(dict.fromkeys(matches))
        if len(matches) == 1:
            topic = matches[0]
        elif len(matches) > 1:
            if any(word in query for word in ('how','guide','step','file','portal')):
                return {'answer': 'Which form would you like to work on first? I can guide one portal task at a time.', 'sources': [], 'followups': [], 'sample': sample, 'answer_mode': 'clarification'}
            return None
        if not topic:
            for key, words in [('challan',('challan','pmt06','pmt 06')),('refund',('refund','rfd01','rfd 01')),('ims',('ims',)),('ledgers',('ledger',)),('iff',('iff',))]:
                if any(word in query or word in compact for word in words):
                    topic = key
                    break
        if not topic:
            for key, words in [('einvoice',('e invoice','einvoice')),('eway',('e way','eway')),('revocation',('revocation','revoke cancellation')),('cancellation',('cancel registration','cancellation')),('amendment',('amend registration','amendment')),('registration',('register for gst','registration')),('notices',('notice','reply to order')),('lut',('lut','letter of undertaking')),('qrmp',('qrmp',))]:
                if any(word in query for word in words):
                    topic=key
                    break
        if topic is None and any(text in query for text in ('file gst','gst portal guide','file returns','file my return')):
            return {'answer': 'Which task do you need: GSTR-1 outward supplies, GSTR-3B liability/payment, GSTR-2B view/download, or another named form? Tell me the form and I will guide it one stage at a time.',
                    'sources': [], 'followups': ['How do I file GSTR-1?', 'How do I file GSTR-3B?', 'How do I download GSTR-2B?'], 'sample': sample, 'answer_mode': 'clarification'}
        if topic and (query.startswith('what is ') or query.startswith('explain ')):
            name, purpose, _, source = FORMS[topic]
            return {'answer':f'{name}: {purpose}. Ask for the portal guide if you want step-by-step instructions. This does not establish applicability to your registration.',
                    'sources':[{'id':f'portal-{topic}','label':f'Official {name} guidance','href':source,'layer':'Portal reference'}],
                    'followups':[f'Guide me through {name} on the portal'], 'sample':sample, 'answer_mode':'template'}
        if not topic or not any(word in query for word in ('how','step','guide','portal','file','download','view','navigate','process')):
            return None
    name, purpose, steps, source = FORMS[topic]
    all_steps = any(word in query for word in ('all steps','full guide','complete guide','entire guide'))
    selected = '\n\n'.join(f'{i+1}. {text}' for i, text in enumerate(steps)) if all_steps else steps[step]
    label = 'Overview' if all_steps else f'Stage {step+1} of {len(steps)}'
    followups = [] if all_steps or step == 2 else ['Next step']
    return {'answer': f'{name} — {purpose}\n{label}: {selected}\n\nGuidance only: sign in and act on the official portal yourself. Check the current manual and period; never send passwords, DSC keys or OTPs here. GST Easy has not filed or paid anything.',
            'sources': [{'id': f'portal-{topic}', 'label': f'Official {name} guidance', 'href': source, 'layer': 'Portal reference'}],
            'followups': followups, 'sample': sample, 'portal_topic': topic, 'portal_step': step,
            'template_version': VERSION, 'answer_mode': 'portal_guide'}
