"""Deterministic synthetic medallion records. No database, storage or network writes."""
from calendar import monthrange
from copy import deepcopy
from datetime import date
from random import Random

from .dashboard import customer_dashboard
from .medallion import clean, period_value
from .rules import HEADS, ZERO, amount, common_reversal, rule, set_off

SCENARIOS = {
    'redtaxi': 'Red Taxi Coimbatore — September auditor demonstration',
    'mixed': 'All major invoice and credit states',
    'ready': 'Validated purchases and eligible credit',
    'empty': 'No records for this period',
    'review': 'Invoices awaiting human review',
    'failed': 'Failed extraction and unreadable evidence',
    'unmatched': 'Supplier invoices missing from GSTR-2B',
    'mismatch': 'GSTR-2B amount differences',
    'blocked': 'Blocked credit decisions',
    'reversal': 'Unpaid invoices beyond 180 days',
    'common': 'Common-input and capital-credit adjustments',
    'fuel': 'Non-GST fuel purchases',
    'eco': 'ECO cash-only output liability',
    'rate_restricted': 'Rate-condition restrictions on credit',
    'locked': 'Locked filing period',
    'large': '120 invoices for pagination and search',
}


class DemoStore:
    def __init__(self, tables, profile, period, state):
        self.tables, self._profile, self.period, self.state = tables, profile, period, state
        self.client_id = profile['client_id']

    def rows(self, table, *args, **kwargs):
        if not table.startswith('gold_'):
            raise ValueError('Dashboard may only read synthetic Gold tables')
        return deepcopy(self.tables.get(table, []))

    def profile(self):
        return deepcopy(self._profile)

    def status(self):
        return {'state': self.state}


def generate_mock_data(scenario='mixed', period='2026-09', seed=42):
    if scenario == 'redtaxi':
        from .redtaxi_mock import generate_redtaxi_mock_data
        return generate_redtaxi_mock_data(period, seed)
    period_value(period)
    if scenario not in SCENARIOS:
        raise ValueError('Unknown demo scenario')
    rng = Random(seed)
    year, month = map(int, period.split('-'))
    as_of = date(year, month, monthrange(year, month)[1])
    stamp = period + '-20T10:00:00+00:00'
    tenant = 'demo-transport'
    profile = {'client_id': tenant, 'legal_name': 'Demo Mobility — Synthetic Company', 'gstin': '',
               'state_code': '33', 'business_nature': 'eco_operator' if scenario == 'eco' else 'passenger_transport',
               'is_eco_9_5': scenario == 'eco', 'itc_rate_restricted': scenario == 'rate_restricted',
               'itc_rule_flags': {'turnover_total': '100000', 'turnover_exempt': '20000'}}
    count = 0 if scenario == 'empty' else 120 if scenario == 'large' else 26 if scenario == 'mixed' else 8
    documents, lines, ledger, matches = [], [], [], []
    booked, eligible, output, eco = ({h: ZERO for h in HEADS} for _ in range(4))
    non_gst = ZERO
    run_id = f'demo_{period}_{scenario}_{seed}'
    cases = ['ready', 'review', 'failed', 'unmatched', 'mismatch', 'blocked', 'reversal', 'fuel', 'common', 'ready', 'ready', 'ready', 'ready']
    vendors = ['Metro Fleet Services', 'Harbour Insurance', 'City Office Supplies', 'Northwind Software', 'Demo Fuel Station']
    for i in range(count):
        case = cases[i % len(cases)] if scenario == 'mixed' else scenario
        doc_id = f'demo-{scenario}-{i+1:03d}'
        value = amount(rng.randint(500, 20000))
        taxes = {h: ZERO for h in HEADS}
        if case != 'fuel':
            if i % 2:
                taxes['igst'] = amount(value * amount('0.18'))
            else:
                taxes['cgst'] = taxes['sgst'] = amount(value * amount('0.09'))
        status = 'needs_review' if case == 'review' else 'failed' if case == 'failed' else 'validated'
        category = 'fuel' if case == 'fuel' else 'vehicle' if i % 5 == 0 else 'insurance_repair' if i % 5 == 1 else 'services'
        description = 'Diesel fuel — non-GST' if case == 'fuel' else ['Passenger vehicle service', 'Fleet insurance', 'Office equipment', 'Dispatch software subscription', 'Vehicle repairs'][i % 5]
        line = {'client_id': tenant, 'period': period, 'doc_id': doc_id, 'line_no': 1,
                'description': description, 'taxable_value': value, 'itc_category': category,
                'invoice_date': period + f'-{i%20+1:02d}', **taxes}
        if case == 'blocked':
            line['blocked_clause'] = '17(5)-DEMO-BLOCKED'
            line['itc_category'] = 'other'
        if case == 'reversal':
            line['unpaid_days'] = 181
        if case == 'common':
            line.update(common_credit=True, capital_goods=bool(i % 2))
        header = {'supplier_name': vendors[i % len(vendors)], 'supplier_gstin': f'DEMO-SUPPLIER-{i%5+1}',
                  'invoice_no': f'MOCK-{month:02d}-{i+1:03d}', 'invoice_date': line['invoice_date'],
                  'taxable_value': value, 'total': value + sum(taxes.values(), ZERO), **taxes,
                  'validation_status': status, 'validation_errors': ['Synthetic review example'] if status == 'needs_review' else ['Synthetic unreadable invoice'] if status == 'failed' else []}
        documents.append({'client_id': tenant, 'period': period, 'doc_id': doc_id,
                          'original_filename': f'MOCK-{i+1:03d}-{case}.pdf', 'uploaded_at': stamp,
                          'stage': 'In ledger' if status == 'validated' else 'Extracted' if status == 'needs_review' else 'Failed',
                          'silver': header, 'scenario': case, 'sample': True})
        documents[-1]['search_text'] = description + ' ' + case
        lines.append(line)
        if status != 'validated':
            continue
        match = 'unmatched_books' if case == 'unmatched' else 'amount_mismatch' if case == 'mismatch' else 'matched'
        matches.append({'client_id': tenant, 'period': period, 'doc_id': doc_id, 'invoice_no': header['invoice_no'],
                        'match_status': match, 'delta': '12.50' if case == 'mismatch' else '0.00', 'run_id': run_id})
        bucket, ref = rule(line, profile, match == 'matched', as_of=as_of)
        entry = {'client_id': tenant, 'period': period, 'doc_id': doc_id, 'line_no': 1, 'run_id': run_id,
                 'invoice_no': header['invoice_no'], 'description': description, 'reason_code': bucket, 'rule_ref': ref,
                 'computed_at': stamp, 'non_gst': value if bucket == 'non_gst' else ZERO}
        for group in ('eligible', 'blocked', 'deferred', 'reversal'):
            for head in HEADS:
                entry[f'{group}_{head}'] = taxes[head] if bucket == group else ZERO
        if bucket == 'eligible':
            reversals, reversal_ref = common_reversal(line, profile, taxes)
            if reversal_ref:
                entry['rule_ref'] = reversal_ref
                for head in HEADS:
                    entry[f'eligible_{head}'] -= reversals[head]
                    entry[f'reversal_{head}'] += reversals[head]
        for head in HEADS:
            booked[head] += taxes[head]
            eligible[head] += entry[f'eligible_{head}']
        non_gst += entry['non_gst']
        ledger.append(entry)
    summary = None
    if ledger:
        output.update(igst=amount('25000'), cgst=amount('18000'), sgst=amount('18000'))
        if scenario == 'eco':
            eco.update(cgst=amount('5000'), sgst=amount('5000'))
        settled = set_off(output, eligible, eco)
        summary = {'client_id': tenant, 'period': period, 'run_id': run_id, 'computed_at': stamp,
                   'input_by_head': booked, 'eligible_by_head': eligible, 'output_by_head': output,
                   'eco_by_head': eco, 'non_gst': non_gst, **settled}
    tables = {'gold_filing_summary': [summary] if summary else [], 'gold_itc_ledger': ledger, 'gold_gstr2b_match': matches}
    dashboard = customer_dashboard(DemoStore(tables, profile, period, 'locked' if scenario == 'locked' else 'draft'))
    dashboard.update(sample=True, demo_fallback=True, scenario=scenario)
    return clean({'sample': True, 'scenario': scenario, 'description': SCENARIOS[scenario], 'seed': seed,
                  'period': period, 'profile': profile, 'dashboard': dashboard, 'documents': documents,
                  'lines': lines, 'ledger': ledger, 'matches': matches, 'gold_tables': tables,
                  'coverage': list(SCENARIOS), 'notice': 'Synthetic examples only. Not customer records or filing data.'})
