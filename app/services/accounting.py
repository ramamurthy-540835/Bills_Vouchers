from datetime import date
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..models import Account, AccountType, JournalEntry, JournalLine

DEFAULT_ACCOUNTS = [("1000","Cash",AccountType.ASSET),("1010","Petty Cash",AccountType.ASSET),("1100","Main Bank Account",AccountType.ASSET),("1200","Razorpay Clearing",AccountType.ASSET),("1300","Accounts Receivable",AccountType.ASSET),("2000","Accounts Payable",AccountType.LIABILITY),("4000","Sales Revenue",AccountType.INCOME),("4100","Other Income",AccountType.INCOME),("5000","Office Expenses",AccountType.EXPENSE),("5100","Travel Expenses",AccountType.EXPENSE),("5200","Food Expenses",AccountType.EXPENSE),("5300","Grocery Expenses",AccountType.EXPENSE),("5400","Marketing Expenses",AccountType.EXPENSE),("5500","Salary Expenses",AccountType.EXPENSE),("5600","Internet Expenses",AccountType.EXPENSE),("5700","Electricity Expenses",AccountType.EXPENSE),("5800","Software Expenses",AccountType.EXPENSE),("5900","Miscellaneous Expenses",AccountType.EXPENSE)]

def seed_accounts(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Account)): return
    db.add_all([Account(code=c,name=n,account_type=t) for c,n,t in DEFAULT_ACCOUNTS]); db.commit()

def post_entry(db: Session, *, entry_date: date, reference: str, description: str, debit_account_id: int, credit_account_id: int, amount: Decimal, source: str="manual") -> JournalEntry:
    if amount <= 0: raise ValueError("Amount must be greater than zero.")
    if debit_account_id == credit_account_id: raise ValueError("Debit and credit accounts must differ.")
    if db.scalar(select(JournalEntry).where(JournalEntry.reference == reference)): raise ValueError("Reference already exists.")
    accounts = db.scalars(select(Account).where(Account.id.in_([debit_account_id, credit_account_id]), Account.is_active.is_(True))).all()
    if len(accounts) != 2: raise ValueError("Select two active accounts.")
    entry = JournalEntry(entry_date=entry_date, reference=reference, description=description, source=source)
    entry.lines = [JournalLine(account_id=debit_account_id, debit=amount, credit=Decimal("0")), JournalLine(account_id=credit_account_id, debit=Decimal("0"), credit=amount)]
    if sum(line.debit for line in entry.lines) != sum(line.credit for line in entry.lines): raise ValueError("Journal entry is not balanced.")
    db.add(entry); db.commit(); db.refresh(entry); return entry

def account_balance(db: Session, account: Account) -> Decimal:
    debit, credit = db.execute(select(func.coalesce(func.sum(JournalLine.debit),0),func.coalesce(func.sum(JournalLine.credit),0)).where(JournalLine.account_id==account.id)).one()
    return Decimal(debit-credit) if account.account_type in (AccountType.ASSET,AccountType.EXPENSE) else Decimal(credit-debit)
