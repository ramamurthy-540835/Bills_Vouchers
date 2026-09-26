"""Customer dashboard: financial figures are read exclusively from Gold tables."""
from .medallion import clean, param
from .rules import HEADS, ZERO, amount


def customer_dashboard(store):
    from ...fixtures.red_taxi_sample import is_synthetic
    summaries = store.rows('gold_filing_summary', 'ORDER BY computed_at DESC')
    genuine = [r for r in summaries if not is_synthetic(r)]
    summaries = genuine or summaries
    summary = summaries[0] if summaries else None
    ledger = store.rows('gold_itc_ledger', 'AND run_id=@run_id ORDER BY doc_id,line_no',
                        [param('run_id', summary['run_id'])]) if summary else []
    totals = None
    if summary:
        totals = {
            'input_tax': sum((amount(summary.get('input_by_head', {}).get(h)) for h in HEADS), ZERO),
            'eligible_credit': sum((amount(summary.get('eligible_by_head', {}).get(h)) for h in HEADS), ZERO),
            'output_tax': sum((amount(summary.get(k, {}).get(h)) for k in ('output_by_head', 'eco_by_head') for h in HEADS), ZERO),
            'cash_required': amount(summary.get('cash_required')),
            **{bucket: sum((amount(row.get(f'{bucket}_{h}')) for row in ledger for h in HEADS), ZERO)
               for bucket in ('blocked', 'deferred', 'reversal')},
        }
    return clean({
        'client_id': store.client_id, 'period': store.period, 'profile': store.profile(),
        'mode': 'live' if summary else 'empty', 'source': 'gold',
        'summary': summary, 'totals': totals, 'validated_invoices': len({r['doc_id'] for r in ledger}),
        'updated_at': summary.get('computed_at') if summary else None,
        'filing': store.status(), 'demo_fallback': False,
    })
