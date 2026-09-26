"""Deterministic, Decimal-only transport illustration for the selected period."""
from calendar import monthrange
from datetime import date, timedelta

from app.services.gst.medallion import clean, period_value
from app.services.gst.rules import HEADS, ZERO, amount, rule, set_off

NOTICE = "Sample data for illustration — not Red Taxi's filed figures"


def generate(period, client_id, profile=None):
    period_value(period)
    year, month = map(int, period.split('-'))
    end = date(year, month, monthrange(year, month)[1])
    stamp = period + '-01T00:00:00+00:00'
    profile = {**(profile or {}), 'client_id':client_id, 'legal_name':'Red Taxi',
        'state_code':'33', 'business_nature':'passenger_transport', 'filing_frequency':'monthly',
        'itc_rate_restricted':False, 'composition_flag':False}
    run = 'sample_redtaxi_'+period
    tables: dict[str, list[dict]] = {k:[] for k in ['bronze_document','silver_invoice_header','silver_invoice_line',
        'silver_outward_invoice','silver_gstr2b_invoice','gold_itc_ledger','gold_gstr2b_match',
        'gold_filing_summary','gst_filing_status']}
    booked, eligible, restricted = ({h:ZERO for h in HEADS} for _ in range(3))
    categories = [
        ('Fleet insurance','insurance_repair','Kovai Fleet Insurance', '18000'),
        ('Vehicle servicing','insurance_repair','Kovai Service Centre','12500'),
        ('Diesel — non-GST','fuel','Kovai Fuel Depot','9000'),
        ('Tyres and spare parts','services','Tamil Nadu Tyres','7200'),
        ('Driver uniforms','services','Kovai Uniforms','2400'),
        ('Office rent','services','Kovai Office Rentals','25000'),
        ('Telecom','services','Kovai Telecom','1800'),
        ('Dispatch software / SaaS','services','Fleet Software','3600'),
        ('Driver app commissions','services','Taxi App Services','5200'),
        ('Vehicle servicing','insurance_repair','Peelamedu Workshop','8000')]
    non_gst = ZERO
    for i in range(120):
        description, category, supplier, base = categories[(i-2) % len(categories)]
        if i < 2:
            description, category, supplier, base = 'Passenger taxi vehicle purchase','vehicle','Kovai Motors','650000'
        factor = amount('1') + amount(month)/amount('100')
        taxable = amount((amount(base) + (ZERO if i < 2 else amount((i % 7)*137)))*factor)
        taxes = {h:ZERO for h in HEADS}
        rate = amount('0.28' if i < 2 else '0.18')
        if category != 'fuel':
            if i == 9:
                supplier = 'Bengaluru Fleet Software'
                taxes['igst'] = amount(taxable*rate)
            else:
                taxes['cgst'] = taxes['sgst'] = amount(taxable*rate/amount('2'))
        number = f'RTX-SAMPLE-{period.replace("-", "")}-{i+1:03d}'
        doc = f'sample-redtaxi-{period}-{i+1:03d}'
        dt = (end-timedelta(days=190)).isoformat() if i==18 else period+f'-{i%min(28,end.day)+1:02d}'
        common = {'client_id':client_id,'period':period,'doc_id':doc}
        line = {**common, 'line_no':1,'description':description,'itc_category':category,
            'invoice_date':dt,'taxable_value':taxable,'seating_capacity':5,
            'unpaid_days':190 if i==18 else 0, **taxes}
        matched = i not in {12,32,52,72,92}
        bucket, ref = rule(line, profile, matched, as_of=end)
        header = {**common,'supplier_name':supplier+' — fictional','supplier_gstin':'SAMPLE-NOT-A-GSTIN',
            'invoice_no':number,'invoice_date':dt,'taxable_value':taxable,**taxes,
            'total':taxable+sum(taxes.values(),ZERO),'validation_status':'validated','validation_errors':[],
            'extraction_engine':'SYNTHETIC_FIXTURE_NOT_OCR','extracted_at':stamp}
        tables['bronze_document'].append({**common,'original_filename':number+'-SAMPLE',
            'uploaded_at':stamp,'source_channel':'SYNTHETIC_DEMO','sample':True,'stage':'In return'})
        tables['silver_invoice_header'].append(header)
        tables['silver_invoice_line'].append(line)
        entry = {**common,'line_no':1,'run_id':run,'invoice_no':number,'description':description,
            'reason_code':bucket,'rule_ref':ref,'computed_at':stamp,'non_gst':taxable if category=='fuel' else ZERO}
        for group in ['eligible','blocked','deferred','reversal']:
            for h in HEADS:
                entry[f'{group}_{h}'] = taxes[h] if bucket==group else ZERO
        for h in HEADS:
            booked[h] += taxes[h]
            eligible[h] += entry[f'eligible_{h}']
            restricted[h] += taxes[h] if matched else ZERO
        non_gst += entry['non_gst']
        tables['gold_itc_ledger'].append(entry)
        if category != 'fuel':
            tables['gold_gstr2b_match'].append({**common,'run_id':run,'invoice_no':number,
                'supplier_gstin':header['supplier_gstin'],'match_status':'matched' if matched else 'unmatched_books',
                'delta':ZERO,'computed_at':stamp})
            if matched:
                tables['silver_gstr2b_invoice'].append({**header,'sample':True})
    for i in range(13):
        value = amount(amount('180000' if i==12 else str(420000 + i*13500))*factor)
        tax = amount(value*amount('0.09' if i==12 else '0.06'))
        tables['silver_outward_invoice'].append({'client_id':client_id,'period':period,
            'invoice_no':f'RTX-SAMPLE-SALE-{i+1:03d}','invoice_date':period+f'-{i+1:02d}',
            'recipient_name':'Corporate account — fictional' if i==12 else 'Ride receipts — fictional',
            'recipient_gstin':'SAMPLE-NOT-A-GSTIN' if i==12 else '',
            'description':'Vehicle rental with operator — illustrative 18%' if i==12 else 'Passenger rides — illustrative 12% with ITC',
            'sac':'9966' if i==12 else '9964','taxable_value':value,
            'igst':ZERO,'cgst':tax,'sgst':tax,'cess':ZERO,'eco_9_5':False,'sample':True})
    output = {h:sum((r[h] for r in tables['silver_outward_invoice']),ZERO) for h in HEADS}
    eco = {h:ZERO for h in HEADS}
    settled = set_off(output,eligible,eco)
    tables['gold_filing_summary'] = [{'client_id':client_id,'period':period,'run_id':run,
        'computed_at':stamp,'input_by_head':booked,'eligible_by_head':eligible,'output_by_head':output,
        'eco_by_head':eco,'non_gst':non_gst,**settled,
        'as_booked':set_off(output,booked)['cash_required'],
        'restricted_2b':set_off(output,restricted)['cash_required'],
        'fully_compliant':settled['cash_required'],
        'if_late_file':set_off(output,{h:ZERO for h in HEADS})['cash_required']}]
    return {'profile':profile,'tables':tables,'notice':NOTICE,'sample':True}


def is_synthetic(row):
    return str(row.get('run_id') or '').startswith(('sample_', 'synthetic_', 'demo_'))


def use_sample(store):
    from app.config import get_settings
    profile = store.profile() or {}
    rows = store.rows('gold_filing_summary')
    genuine = any(not is_synthetic(r) for r in rows)
    red_taxi = str(profile.get('legal_name','')).strip().lower() == 'red taxi'
    return red_taxi and not genuine and (get_settings().demo_fallback or any(is_synthetic(r) for r in rows))


def sample_dashboard(store):
    from app.services.gst.dashboard import customer_dashboard
    from app.services.gst.mock_data import DemoStore
    fixture = generate(store.period, store.client_id, store.profile())
    result = customer_dashboard(DemoStore(fixture['tables'],fixture['profile'],store.period,'draft'))
    result.update(sample=True, mode='sample', demo_fallback=True, notice=NOTICE,
                  illustrative_rate='Illustrative rate: rides at 12% with ITC; corporate rental at 18%')
    result['deltas'] = comparison_deltas(fixture['tables']['gold_filing_summary'][0],
        generate(previous_period(store.period),store.client_id,store.profile())['tables']['gold_filing_summary'][0])
    return clean(result)


def previous_period(period):
    return (date.fromisoformat(period+'-01')-timedelta(days=1)).strftime('%Y-%m')


def comparison_deltas(current, previous):
    if not current or not previous:
        return {}
    def values(row):
        return {'Eligible ITC':sum((amount(row.get('eligible_by_head',{}).get(h)) for h in HEADS),ZERO),
            'Output tax':sum((amount(row.get(k,{}).get(h)) for k in ('output_by_head','eco_by_head') for h in HEADS),ZERO),
            'Estimated cash':amount(row.get('cash_required')),'Non-GST purchases':amount(row.get('non_gst'))}
    a,b = values(current),values(previous)
    return {k:str(amount((a[k]-b[k])/abs(b[k])*amount('100'))) for k in a if b[k]}


def sample_workspace(store):
    fixture = generate(store.period,store.client_id,store.profile())
    t = fixture['tables']
    docs = [{**r,'silver':t['silver_invoice_header'][i]} for i,r in enumerate(t['bronze_document'])]
    return clean({**sample_dashboard(store),'documents':docs,'ledger':t['gold_itc_ledger'],
        'matches':t['gold_gstr2b_match'],'counts':{'documents':120,'review':0,'posted':120,'failed':0},
        'pipeline':{'bronze':120,'silver':120,'gold':120},'has_silver':True,'outward_count':13})
