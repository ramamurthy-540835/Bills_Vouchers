"""Red Taxi presentation fixtures: explicitly synthetic, never live client records."""
from datetime import date, timedelta
from .dashboard import customer_dashboard
from .medallion import clean
from .mock_data import SCENARIOS, DemoStore, generate_mock_data
from .rules import HEADS, ZERO, amount, set_off


def generate_redtaxi_mock_data(period='2026-09', seed=42):
    bundle = generate_mock_data('mixed', period, seed)
    tenant = 'demo-redtaxi-coimbatore'
    profile = {**bundle['profile'], 'client_id':tenant, 'legal_name':'Red Taxi Coimbatore — DEMONSTRATION',
               'trade_name':'Red Taxi demo', 'filing_frequency':'monthly', 'source':'SYNTHETIC_DEMO', 'gstin':''}
    vendors = [
        ('Kovai Fleet Workshop — fictional', 'Taxi fleet servicing and brake inspection'),
        ('Kongu Fleet Cover — fictional', 'Annual taxi fleet insurance premium'),
        ('Coimbatore Tyre Centre — fictional', 'Replacement tyres for taxi fleet'),
        ('Kovai Dispatch Software — fictional', 'Taxi dispatch software subscription'),
        ('Peelamedu Fleet Workshop — fictional', 'Taxi air-conditioning repair'),
    ]
    for index, doc in enumerate(bundle['documents']):
        old = doc['doc_id']
        identifier = f'demo-redtaxi-{index+1:03d}'
        vendor, description = vendors[index % len(vendors)]
        case = doc['scenario']
        if case == 'fuel':
            vendor, description = 'Kovai Fuel Depot — fictional', 'Diesel for taxi fleet — non-GST purchase'
        elif case == 'blocked':
            vendor, description = 'Coimbatore Staff Catering — fictional', 'Staff meal expense — illustrative blocked-credit case'
        elif case == 'common':
            vendor, description = 'Kovai Office Systems — fictional', 'Dispatch office equipment — common-use attribution example'
        number = f'RTX-DEMO-{period.replace("-", "")}-{index+1:03d}'
        doc.update(client_id=tenant,doc_id=identifier,original_filename=number+'.png',
                   search_text=description+' '+case+' Coimbatore', evidence_status='PNG prompt supplied; image not yet generated')
        doc['silver'].update(supplier_name=vendor,invoice_no=number,recipient_name=profile['legal_name'],
                             recipient_gstin='',supplier_gstin='DEMO-NOT-A-GSTIN',place_of_supply='33')
        line=bundle['lines'][index]
        line.update(client_id=tenant,doc_id=identifier,description=description)
        if case == 'reversal':
            old_date = (date.fromisoformat(period+'-01')-timedelta(days=190)).isoformat()
            doc['silver']['invoice_date']=line['invoice_date']=old_date
        for entry in bundle['ledger']:
            if entry['doc_id']==old:
                entry.update(client_id=tenant,doc_id=identifier,invoice_no=number,description=description)
        for match in bundle['matches']:
            if match['doc_id']==old:
                match.update(client_id=tenant,doc_id=identifier,invoice_no=number,supplier_gstin='DEMO-NOT-A-GSTIN')
    sales=[]
    for index, value in enumerate(('125000','84000','56000','96000','72000','45000'),1):
        taxable=amount(value)
        # Illustrative arithmetic, not a determination of Red Taxi's applicable tax rate.
        cgst=amount(taxable*amount('0.06'))
        sgst=cgst
        sales.append({'client_id':tenant,'period':period,'invoice_no':f'RTX-DEMO-SALE-{index:03d}',
            'invoice_date':period+f'-{index*3:02d}','recipient_name':f'Coimbatore Corporate Customer {index} — fictional',
            'recipient_gstin':'DEMO-NOT-A-GSTIN','description':'Corporate cab service — illustrative 12% scenario',
            'taxable_value':taxable,'igst':ZERO,'cgst':cgst,'sgst':sgst,'cess':ZERO,'total':taxable+cgst+sgst,
            'sample':True})
    output={h:sum((r[h] for r in sales),ZERO) for h in HEADS}
    summary=bundle['gold_tables']['gold_filing_summary'][0]
    summary.update(client_id=tenant,output_by_head=output,**set_off(output,summary['eligible_by_head'],summary['eco_by_head']))
    two_b=[]
    for doc in bundle['documents']:
        if doc['scenario'] in {'review','failed','unmatched','fuel'}:
            continue
        row={**doc['silver'],'client_id':tenant,'period':period,'sample':True}
        if doc['scenario']=='mismatch':
            head=next(h for h in HEADS if amount(row[h]))
            row[head]=str(amount(row[head])+amount('12.50'))
            row['total']=str(amount(row['total'])+amount('12.50'))
        two_b.append(row)
    bundle['gold_tables']['gold_itc_ledger']=bundle['ledger']
    bundle['gold_tables']['gold_gstr2b_match']=bundle['matches']
    dashboard=customer_dashboard(DemoStore(bundle['gold_tables'],profile,period,'draft'))
    dashboard.update(sample=True,demo_fallback=True,scenario='redtaxi')
    bundle.update(scenario='redtaxi',profile=profile,dashboard=dashboard,outward=sales,gstr2b=two_b,
        description=SCENARIOS['redtaxi'],
        assumptions=['All suppliers, customers and amounts are fictional. No genuine GSTIN is supplied.',
                     'Sales use an illustrative 12% model solely for arithmetic demonstration. Confirm actual tax rates and ITC conditions before onboarding.',
                     'Rule examples include mixed credit outcomes, common-credit basis and unpaid-invoice reversal; they do not describe Red Taxi actual transactions.',
                     'PNG filenames are planned assets. Prompts are supplied separately; original images do not yet exist.'])
    return clean(bundle)


def png_prompts(bundle):
    intro = '# Red Taxi demonstration PNG prompts\n\nAll records are fictional. Generate each image separately; use the exact filename shown. Do not upload these images into a live customer filing. Review generated text and arithmetic against mock-data.json before using them in a presentation.\n\n'
    sections=[]
    for doc in bundle['documents']:
        row=doc['silver']
        prompt=(f"Create a clean, readable A4 portrait invoice image as a PNG, 1600 by 2260 pixels, white paper, dark text, simple table, no decorative photography. "
                f"Put a large visible watermark across the page and in its header: SAMPLE — NOT VALID FOR GST FILING. "
                f"Supplier: {row['supplier_name']}. Supplier location: Coimbatore, Tamil Nadu (fictional). "
                f"Customer: Red Taxi Coimbatore — DEMONSTRATION. Supplier GSTIN: DEMO-NOT-A-GSTIN. Customer GSTIN: Pending — demonstration only. "
                f"Invoice number: {row['invoice_no']}. Date: {row['invoice_date']}. Description: {doc['search_text']}. "
                f"Show INR amounts exactly: taxable / purchase value {row['taxable_value']}; IGST {row['igst']}; CGST {row['cgst']}; SGST {row['sgst']}; cess {row['cess']}; total {row['total']}. "
                "Include footer: Fictional training document. No payment required. Do not add a bank account, UPI QR code, official logo, signature, IRN, real address or valid-looking GSTIN. "
                "Keep all numbers sharp and aligned. Do not invent tax rates, extra charges or line items.")
        sections.append(f"## {doc['original_filename']}\n\n{prompt}\n\nAuditor scenario: **{doc['scenario']}**. This is a fixture scenario; generating an image does not reproduce a portal match or real rule determination.\n")
    return intro+'\n'.join(sections)
