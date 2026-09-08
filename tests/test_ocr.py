from decimal import Decimal
from app.services.ocr import decimal_or_none
def test_money_parser(): assert decimal_or_none('₹1,250.00')==Decimal('1250.00')
def test_missing_money_is_null(): assert decimal_or_none('') is None
