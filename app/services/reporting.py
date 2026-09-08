from datetime import date
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..models import Account, AccountType, JournalEntry, JournalLine

ZERO=Decimal("0")
def balances(db: Session, start: date | None=None, end: date | None=None) -> dict[AccountType,list[tuple[Account,Decimal]]]:
    query=select(Account,func.coalesce(func.sum(JournalLine.debit),0),func.coalesce(func.sum(JournalLine.credit),0)).outerjoin(JournalLine,JournalLine.account_id==Account.id).outerjoin(JournalEntry,JournalEntry.id==JournalLine.journal_entry_id)
    if start: query=query.where((JournalEntry.entry_date>=start)|(JournalEntry.entry_date.is_(None)))
    if end: query=query.where((JournalEntry.entry_date<=end)|(JournalEntry.entry_date.is_(None)))
    query=query.group_by(Account.id)
    output={t:[] for t in AccountType}
    for account,debit,credit in db.execute(query):
        amount=Decimal(debit-credit) if account.account_type in (AccountType.ASSET,AccountType.EXPENSE) else Decimal(credit-debit)
        output[account.account_type].append((account,amount))
    return output

def profit_and_loss(db: Session,start: date|None,end:date|None):
    data=balances(db,start,end); revenue=sum((v for _,v in data[AccountType.INCOME]),ZERO); expenses=sum((v for _,v in data[AccountType.EXPENSE]),ZERO)
    return data,revenue,expenses,revenue-expenses

def cash_flow(db: Session,start:date|None,end:date|None):
    data=balances(db,start,end); cash=sum((v for a,v in data[AccountType.ASSET] if a.name in {"Cash","Petty Cash","Main Bank Account"}),ZERO)
    return {"opening_cash":ZERO,"inflow":sum((v for _,v in data[AccountType.INCOME]),ZERO),"outflow":sum((v for _,v in data[AccountType.EXPENSE]),ZERO),"closing_cash":cash}
