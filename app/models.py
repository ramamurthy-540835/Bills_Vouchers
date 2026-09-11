from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


class AccountType(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class DocumentType(str, Enum):
    BILL = "bill"
    VOUCHER = "voucher"
    INVOICE = "invoice"
    RECEIPT = "receipt"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    SCANNING = "scanning"
    EXTRACTED = "extracted"
    PROCESSING = "processing"
    OCR_COMPLETED = "ocr_completed"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    POSTED = "posted"
    REJECTED = "rejected"
    FAILED = "failed"
    SCAN_FAILED = "scan_failed"


def ns(**kwargs):
    return type("Record", (), kwargs)()
