from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import Account, AccountType
from app.services.accounting import account_balance, post_entry

@pytest.fixture
def db():
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session=sessionmaker(bind=engine)()
    session.add_all([Account(code="1000",name="Cash",account_type=AccountType.ASSET),Account(code="4000",name="Sales",account_type=AccountType.INCOME)])
    session.commit()
    yield session
    session.close()

def test_balanced_journal_entry_updates_account_balances(db):
    cash,sales=db.query(Account).order_by(Account.code).all()
    entry=post_entry(db,entry_date=date.today(),reference="TEST-1",description="Sale",debit_account_id=cash.id,credit_account_id=sales.id,amount=Decimal("1500.00"))
    assert sum(line.debit for line in entry.lines)==sum(line.credit for line in entry.lines)==Decimal("1500.00")
    assert account_balance(db,cash)==Decimal("1500.00")
    assert account_balance(db,sales)==Decimal("1500.00")

def test_unbalanced_input_is_rejected(db):
    cash,sales=db.query(Account).order_by(Account.code).all()
    with pytest.raises(ValueError,match="greater than zero"):
        post_entry(db,entry_date=date.today(),reference="TEST-2",description="Bad",debit_account_id=cash.id,credit_account_id=sales.id,amount=Decimal("0"))

def test_duplicate_reference_is_rejected(db):
    cash,sales=db.query(Account).order_by(Account.code).all()
    args=dict(entry_date=date.today(),reference="TEST-3",description="Sale",debit_account_id=cash.id,credit_account_id=sales.id,amount=Decimal("1"))
    post_entry(db,**args)
    with pytest.raises(ValueError,match="Reference"):
        post_entry(db,**args)
