from decimal import Decimal
from uuid import uuid4


def post_entry(
    repo, *, entry_date, reference, description, amount, debit_account_id, credit_account_id, source="manual"
):
    if amount <= 0 or debit_account_id == credit_account_id:
        raise ValueError("Entry must have a positive amount and different accounts.")
    eid = str(uuid4())
    repo.bq.insert(
        "journal_entries",
        {
            "id": eid,
            "entry_date": entry_date.isoformat(),
            "reference": reference,
            "description": description,
            "source": source,
            "status": "posted",
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        },
        eid,
    )
    for aid, debit, credit in [(debit_account_id, amount, Decimal(0)), (credit_account_id, Decimal(0), amount)]:
        repo.bq.insert(
            "journal_lines",
            {
                "id": str(uuid4()),
                "journal_entry_id": eid,
                "account_id": str(aid),
                "debit": str(debit),
                "credit": str(credit),
            },
            str(uuid4()),
        )
    return eid
