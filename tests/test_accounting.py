from datetime import date
from decimal import Decimal
from app.services.accounting import post_entry
class BQ:
    def __init__(self): self.rows=[]
    def insert(self,table,row,row_id=None): self.rows.append((table,row))
class R: pass
def test_balanced_journal_entry_writes_two_lines():
    r=R(); r.bq=BQ(); eid=post_entry(r,entry_date=date.today(),reference='T-1',description='Sale',debit_account_id='cash',credit_account_id='sales',amount=Decimal('10'))
    lines=[x for table,x in r.bq.rows if table=='journal_lines']
    assert eid and len(lines)==2 and lines[0]['debit']=='10' and lines[1]['credit']=='10'
def test_invalid_entry_is_rejected():
    import pytest
    r=R(); r.bq=BQ()
    with pytest.raises(ValueError): post_entry(r,entry_date=date.today(),reference='T-2',description='Bad',debit_account_id='a',credit_account_id='a',amount=Decimal('1'))
