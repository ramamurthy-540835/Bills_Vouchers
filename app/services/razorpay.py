import hashlib, hmac, json
from datetime import date
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Account, RazorpayEvent, RazorpayPayment
from .accounting import post_entry

def verify_signature(raw_body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not secret: return False
    expected=hmac.new(secret.encode(),raw_body,hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected,signature)

def record_event(db: Session, raw_body: bytes) -> RazorpayPayment | None:
    payload=json.loads(raw_body)
    event_id=payload.get("event_id") or payload.get("id")
    event_type=payload.get("event")
    if not event_id or not event_type: raise HTTPException(400,"Webhook event id and type are required.")
    if db.scalar(select(RazorpayEvent).where(RazorpayEvent.event_id==event_id)): return None
    db.add(RazorpayEvent(event_id=event_id,event_type=event_type,payload=raw_body.decode("utf-8")))
    entity=payload.get("payload",{}).get("payment",{}).get("entity",{})
    payment_id=entity.get("id")
    if not payment_id: db.commit(); return None
    payment=db.scalar(select(RazorpayPayment).where(RazorpayPayment.razorpay_payment_id==payment_id))
    if not payment:
        payment=RazorpayPayment(razorpay_payment_id=payment_id,razorpay_order_id=entity.get("order_id"),amount=Decimal(entity.get("amount",0))/100,currency=entity.get("currency","INR"),status=entity.get("status","unknown"),method=entity.get("method"),customer_email=entity.get("email"),customer_phone=entity.get("contact"),description=entity.get("description"),fee=Decimal(entity["fee"])/100 if entity.get("fee") is not None else None,tax=Decimal(entity["tax"])/100 if entity.get("tax") is not None else None)
        db.add(payment); db.flush()
        if event_type=="payment.captured" and payment.status=="captured":
            clearing=db.scalar(select(Account).where(Account.name=="Razorpay Clearing")); revenue=db.scalar(select(Account).where(Account.name=="Sales Revenue"))
            if not clearing or not revenue: raise RuntimeError("Required Razorpay accounts are missing.")
            entry=post_entry(db,entry_date=date.today(),reference=f"RZP-{payment_id}",description=f"Razorpay payment {payment_id}",debit_account_id=clearing.id,credit_account_id=revenue.id,amount=payment.amount,source="razorpay")
            payment.journal_entry_id=entry.id
    db.commit(); return payment
