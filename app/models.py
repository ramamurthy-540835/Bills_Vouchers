from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Role(str, Enum): ADMIN="admin"; ACCOUNTANT="accountant"; VIEWER="viewer"
class AccountType(str, Enum): ASSET="asset"; LIABILITY="liability"; EQUITY="equity"; INCOME="income"; EXPENSE="expense"
class DocumentType(str, Enum): BILL="bill"; VOUCHER="voucher"; INVOICE="invoice"; RECEIPT="receipt"
class DocumentStatus(str, Enum): UPLOADED="uploaded"; PROCESSING="processing"; OCR_COMPLETED="ocr_completed"; NEEDS_REVIEW="needs_review"; APPROVED="approved"; POSTED="posted"; REJECTED="rejected"; FAILED="failed"

class User(Base):
    __tablename__="users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SqlEnum(Role), default=Role.ADMIN)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Account(Base):
    __tablename__="accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    account_type: Mapped[AccountType] = mapped_column(SqlEnum(AccountType))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class JournalEntry(Base):
    __tablename__="journal_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    status: Mapped[str] = mapped_column(String(20), default="posted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    lines: Mapped[list["JournalLine"]] = relationship(back_populates="entry", cascade="all, delete-orphan")

class JournalLine(Base):
    __tablename__="journal_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    journal_entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(18,2), default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(18,2), default=Decimal("0"))
    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
    account: Mapped[Account] = relationship()
    __table_args__=(UniqueConstraint("journal_entry_id", "account_id", name="uq_entry_account"),)

class Document(Base):
    __tablename__="documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_type: Mapped[DocumentType] = mapped_column(SqlEnum(DocumentType))
    status: Mapped[DocumentStatus] = mapped_column(SqlEnum(DocumentStatus), default=DocumentStatus.UPLOADED, index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column()
    checksum_sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    bucket_name: Mapped[str] = mapped_column(String(255))
    object_path: Mapped[str] = mapped_column(String(512), unique=True)
    gcs_uri: Mapped[str] = mapped_column(String(768), unique=True)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[User] = relationship()
    extraction: Mapped["DocumentExtraction | None"] = relationship(back_populates="document", cascade="all, delete-orphan")

class DocumentExtraction(Base):
    __tablename__="document_extractions"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), unique=True, index=True)
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    vendor_address: Mapped[str | None] = mapped_column(Text)
    invoice_number: Mapped[str | None] = mapped_column(String(150))
    invoice_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    gstin: Mapped[str | None] = mapped_column(String(30))
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    cgst: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    sgst: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    igst: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    currency: Mapped[str | None] = mapped_column(String(10))
    payment_method: Mapped[str | None] = mapped_column(String(50))
    ocr_text: Mapped[str | None] = mapped_column(Text)
    ocr_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5,4))
    document: Mapped[Document] = relationship(back_populates="extraction")
    line_items: Mapped[list["DocumentLineItem"]] = relationship(back_populates="extraction", cascade="all, delete-orphan")

class DocumentLineItem(Base):
    __tablename__="document_line_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_id: Mapped[int] = mapped_column(ForeignKey("document_extractions.id"), index=True)
    item_name: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18,3))
    unit: Mapped[str | None] = mapped_column(String(50))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    tax: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    discount: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    total: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    extraction: Mapped[DocumentExtraction] = relationship(back_populates="line_items")

class RazorpayPayment(Base):
    __tablename__="razorpay_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    razorpay_payment_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(100), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2))
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    status: Mapped[str] = mapped_column(String(50), index=True)
    method: Mapped[str | None] = mapped_column(String(50))
    customer_name: Mapped[str | None] = mapped_column(String(255))
    customer_email: Mapped[str | None] = mapped_column(String(255))
    customer_phone: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    fee: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    tax: Mapped[Decimal | None] = mapped_column(Numeric(18,2))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class RazorpayEvent(Base):
    __tablename__="razorpay_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity: Mapped[str] = mapped_column(String(100), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), index=True)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    user: Mapped[User | None] = relationship()
