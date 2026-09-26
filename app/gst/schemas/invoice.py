from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def decimal_input(value):
    if isinstance(value, float):
        raise ValueError('Use a decimal string, not a float.')
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('Amount must be finite.')
    return result


Money = Annotated[Decimal, BeforeValidator(decimal_input), Field(max_digits=18, decimal_places=2)]
Number = Annotated[Decimal, BeforeValidator(decimal_input)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', validate_assignment=True)


class LineItem(Model):
    description: str = ''
    hsn_sac: str = ''
    quantity: Number = Decimal('1')
    unit: str = 'NOS'
    taxable_value: Money = Decimal('0')
    gst_rate: Number = Decimal('0')
    cgst: Money = Decimal('0')
    sgst: Money = Decimal('0')
    igst: Money = Decimal('0')
    cess: Money = Decimal('0')


class Totals(Model):
    taxable_value: Money = Decimal('0')
    cgst: Money = Decimal('0')
    sgst: Money = Decimal('0')
    igst: Money = Decimal('0')
    cess: Money = Decimal('0')
    invoice_total: Money = Decimal('0')


class Itc(Model):
    eligibility: Literal['eligible', 'blocked_17_5', 'ineligible_non_gst', 'pending_review'] = 'pending_review'
    blocked_reason: str = ''


class Extraction(Model):
    method: Literal['gemini', 'xlsx_template', 'csv', 'manual'] = 'manual'
    confidence: Annotated[Number, Field(ge=0, le=1)] = Decimal('1')
    raw_ref: str = ''


class GstInvoice(Model):
    invoice_id: str = Field(default_factory=lambda: str(uuid4()))
    client_id: str
    source_doc_id: str
    direction: Literal['purchase', 'sale'] = 'purchase'
    supplier_gstin: str = ''
    supplier_legal_name: str = ''
    supplier_state_code: str = ''
    recipient_gstin: str = ''
    recipient_legal_name: str = ''
    supplier_address: str = ''
    recipient_address: str = ''
    recipient_state_code: str = ''
    invoice_number: str = ''
    invoice_date: date | None = None
    invoice_type: Literal['tax_invoice', 'bill_of_supply', 'debit_note', 'credit_note'] = 'tax_invoice'
    place_of_supply_state_code: str = ''
    reverse_charge: bool = False
    supply_type: Literal['intra', 'inter'] = 'intra'
    line_items: list[LineItem] = Field(default_factory=list, max_length=2000)
    totals: Totals = Field(default_factory=Totals)
    itc: Itc = Field(default_factory=Itc)
    extraction: Extraction = Field(default_factory=Extraction)
    status: Literal['extracted', 'needs_review', 'confirmed', 'rejected'] = 'extracted'
    review_reasons: list[str] = Field(default_factory=list)
    version: int = 1
    sample: bool = False
