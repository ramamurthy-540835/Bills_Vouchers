from datetime import date
from decimal import Decimal
from app.models import Account
from app.services.accounting import post_entry
from app.services.reporting import profit_and_loss

def test_profit_and_loss_reports_revenue(db):
    cash,sales=db.query(Account).order_by(Account.code).all()
    post_entry(db,entry_date=date.today(),reference="R-1",description="Sale",debit_account_id=cash.id,credit_account_id=sales.id,amount=Decimal("99"))
    _,revenue,expenses,profit=profit_and_loss(db,None,None)
    assert revenue==Decimal("99") and expenses==0 and profit==Decimal("99")
