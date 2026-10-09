"""Confirmed canonical bills only; four independent Decimal cash scenarios."""
from decimal import Decimal

from app.services.gst.rules import HEADS, ZERO, rule, set_off
from app.services.gst.validation import normalize_invoice_number


def line_eligibility(line, profile, invoice=None):
    if line.gst_rate == 0:
        return 'non_gst', 'NON-GST'
    category = 'vehicle' if line.hsn_sac.startswith('87') else 'insurance_repair' if line.hsn_sac.startswith(('9971', '9987')) else 'other'
    facts = {'itc_category': category}
    if invoice and invoice.invoice_date:
        facts['invoice_date'] = invoice.invoice_date.isoformat()
    return rule(facts, profile)


def calculate(invoices, profile, two_b):
    confirmed = [i for i in invoices if i.status == 'confirmed' and not i.sample]
    pools = {name: {h: ZERO for h in HEADS} for name in ('recorded', 'matched', 'eligible', 'noCredit')}
    output = {h: ZERO for h in HEADS}
    eco = {h: ZERO for h in HEADS}
    non_gst = ZERO
    decisions = []
    matches = {'matched': 0, 'unmatched': 0, 'amount_mismatch': 0}
    index = {(r['supplier_gstin'], normalize_invoice_number(r['invoice_number'])): r for r in two_b}
    for inv in confirmed:
        sign = Decimal('-1') if inv.invoice_type == 'credit_note' else Decimal('1')
        if inv.direction == 'sale':
            target = eco if profile.get('is_eco_9_5') else output
            for h in HEADS:
                target[h] += sign * getattr(inv.totals, h)
            continue
        row = index.get((inv.supplier_gstin, normalize_invoice_number(inv.invoice_number)))
        match = 'unmatched' if row is None else 'matched' if all(abs(Decimal(str(row.get(h, '0'))) - getattr(inv.totals, h)) <= Decimal('1') for h in ('taxable_value', *HEADS)) else 'amount_mismatch'
        matches[match] += 1
        for line in inv.line_items:
            bucket, reason = line_eligibility(line, profile, inv)
            if bucket != 'eligible':
                non_gst += sign * (line.taxable_value + sum((getattr(line, h) for h in HEADS), ZERO))
            for h in HEADS:
                amount = sign * getattr(line, h)
                pools['recorded'][h] += amount
                # Supplier credit notes reduce claimed credit even before matching.
                if sign < 0 or (match == 'matched' and row.get('itc_available', True)):
                    pools['matched'][h] += amount
                    if bucket == 'eligible':
                        pools['eligible'][h] += amount
            decisions.append({'invoice_id': inv.invoice_id, 'invoice_number': inv.invoice_number,
                'supplier_name': inv.supplier_legal_name, 'description': line.description,
                'matching': match, 'eligibility': bucket, 'rule': reason,
                'tax': sum((getattr(line, h) for h in HEADS), ZERO) * sign})
    # A net credit-note balance is carried forward rather than converted into cash.
    output = {h: max(ZERO, value) for h, value in output.items()}
    eco = {h: max(ZERO, value) for h, value in eco.items()}
    scenarios = {name: set_off(output, {h: max(ZERO, v) for h, v in credit.items()}, eco) for name, credit in pools.items()}
    chosen = scenarios['eligible']
    return {'totals': {'eligible_credit': sum((max(ZERO, v) for v in pools['eligible'].values()), ZERO),
                'output_tax': sum(output.values(), ZERO) + sum(eco.values(), ZERO),
                'cash_required': chosen['cash_required'], 'non_gst': non_gst},
            'heads': {'credit': {h: max(ZERO, v) for h, v in pools['eligible'].items()},
                      'output': {h: output[h] + eco[h] for h in HEADS}, 'cash': chosen['cash_by_head']},
            'scenarios': {key: value['cash_required'] for key, value in scenarios.items()},
            'utilisation': chosen['utilisation'], 'matches': matches, 'decisions': decisions,
            'confirmed_count': len(confirmed)}
