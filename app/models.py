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
