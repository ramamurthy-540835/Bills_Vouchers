"""Canonical dashboard ranges. Monthly credits are never silently pooled."""
from collections import Counter
from decimal import Decimal
import json
from typing import Any

from fastapi import HTTPException

from app.services.gst.rules import HEADS, ZERO
from app.services.gst.medallion import param
from . import returns
from .reconciliation import compare
from .report import calculate
from .reports import periods, MAX_ROWS
from .schemas.invoice import GstInvoice


def read_range(store, selected, evidence=True):
    """One bounded query for all selected months, instead of per-month round trips."""
    parts = []
    params = []
    for index, month in enumerate(selected):
        name = f'month{index}'
        params.append(param(name, month))
        predicate = f'client_id=@client_id AND period=@{name}'
        digest = returns.fingerprint_sql(store).replace('@period', '@'+name)
        fields = f'''@{name} AS period, {digest} AS source_hash,
            TO_JSON_STRING(ARRAY(SELECT AS STRUCT state,version,source_hash
              FROM {store.table('ops','gst_return_current')} WHERE {predicate})) AS states'''
        if evidence:
            fields += f''',TO_JSON_STRING(ARRAY(SELECT payload FROM {store.table('gold','gst_invoice')}
                WHERE {predicate} ORDER BY invoice_id LIMIT {MAX_ROWS+1})) AS invoices,
                TO_JSON_STRING(ARRAY(SELECT payload FROM {store.table('silver','gst_bills_gstr2b')}
                WHERE {predicate} ORDER BY TO_JSON_STRING(payload) LIMIT {MAX_ROWS+1})) AS statements'''
        parts.append('SELECT '+fields)
    rows = store.query(' UNION ALL '.join(parts), params)
    result = {}
    for row in rows:
        states = json.loads(row['states'])
        if len(states) > 1:
            raise HTTPException(409, 'Conflicting return records require review.')
        value = {'source_hash': row['source_hash'], 'filing': states[0] if states else {'state': 'draft', 'version': 0}}
        if evidence:
            value['invoices'] = [GstInvoice.model_validate(inv) for inv in json.loads(row['invoices'])]
            value['statements'] = json.loads(row['statements'])
        result[row['period']] = value
    if set(result) != set(selected):
        raise HTTPException(503, 'Dashboard evidence is unavailable. Please retry.')
    return result


def build(store, period, scope_name, profile_for):
    selected = periods(period, scope_name)
    evidence = read_range(store, selected)
    hashes = {month: evidence[month]['source_hash'] for month in selected}
    profile = profile_for(period)
    monthly = []
    decisions: list[dict[str, Any]] = []
    count = 0
    line_count = 0
    statement_count = 0
    for month in selected:
        invoices = evidence[month]['invoices']
        if any(inv.client_id != store.client_id for inv in invoices):
            raise HTTPException(403, 'Dashboard evidence does not belong to this business.')
        count += len(invoices)
        line_count += sum(len(inv.line_items) for inv in invoices)
        if count > MAX_ROWS or line_count > MAX_ROWS:
            raise HTTPException(422, 'This dashboard range is too large. Select a shorter period.')
        statements = evidence[month]['statements']
        statement_count += len(statements)
        if statement_count > MAX_ROWS:
            raise HTTPException(422, 'This dashboard range is too large. Select a shorter period.')
        calculation = calculate(invoices, profile, statements)
        comparison = compare(invoices, statements)
        counts = comparison['counts']
        confirmed = [inv for inv in invoices if inv.status == 'confirmed' and not inv.sample]
        values = {direction: sum((inv.totals.invoice_total *
                  (Decimal('-1') if inv.invoice_type == 'credit_note' else Decimal('1'))
                  for inv in confirmed if inv.direction == direction), ZERO) for direction in ('sale', 'purchase')}
        state = evidence[month]['filing']
        monthly.append({
            'period': month, 'totals': calculation['totals'], 'heads': calculation['heads'],
            'scenarios': calculation['scenarios'], 'matches': calculation['matches'],
            'confirmed_count': len(confirmed), 'bill_count': len(invoices),
            'review_count': sum(inv.status in {'needs_review', 'extracted'} for inv in invoices),
            'confirmed_sales': values['sale'], 'confirmed_purchases': values['purchase'],
            'reconciliation_counts': counts,
            'unmatched_count': counts.get('missing_book', 0) + counts.get('missing_statement', 0),
            'mismatch_count': sum(value for key, value in counts.items()
                                  if key not in {'exact', 'missing_book', 'missing_statement'}),
            'filing': {'state': state['state'], 'version': state['version'],
                       'source_changed': bool(state.get('source_hash') and state['source_hash'] != hashes[month])},
            'utilisation': calculation['utilisation'],
        })
        decisions.extend({**row, 'period': month} for row in calculation['decisions'])
    refreshed = read_range(store, selected, False)
    if any(evidence[month]['source_hash'] != refreshed[month]['source_hash'] or
           evidence[month]['filing'] != refreshed[month]['filing'] for month in selected):
        raise HTTPException(409, 'Source evidence changed while loading the dashboard. Refresh to try again.')
    total_keys = ('eligible_credit', 'output_tax', 'cash_required', 'non_gst')
    counts = Counter()
    matches: Counter[str] = Counter()
    for row in monthly:
        counts.update(row['reconciliation_counts'])
        matches.update(row['matches'])
    return {
        'scope_name': scope_name, 'periods': selected, 'monthly': monthly, 'source_hashes': hashes, 'profile': profile,
        'totals': {key: sum((row['totals'][key] for row in monthly), ZERO) for key in total_keys},
        'heads': {kind: {head: sum((row['heads'][kind][head] for row in monthly), ZERO) for head in HEADS}
                  for kind in ('credit', 'output', 'cash')},
        'scenarios': {key: sum((row['scenarios'][key] for row in monthly), ZERO)
                      for key in ('recorded', 'matched', 'eligible', 'noCredit')},
        **{key: sum(row[key] for row in monthly) for key in
           ('confirmed_count', 'bill_count', 'review_count', 'confirmed_sales', 'confirmed_purchases',
            'unmatched_count', 'mismatch_count')},
        'matches': dict(matches), 'reconciliation_counts': dict(counts), 'decisions': decisions,
        'utilisation': monthly[0]['utilisation'] if len(monthly) == 1 else {},
        'aggregation_note': ('Range totals sum independent monthly estimates. Credits are not transferred between months. '
                             'Opening balances, carry-forward and final filing adjustments are not included.'),
    }
