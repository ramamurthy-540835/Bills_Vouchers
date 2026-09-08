from decimal import Decimal,InvalidOperation
def decimal_or_none(value):
    if value is None or value=='': return None
    try: return Decimal(str(value).replace(',','').replace('₹','').strip())
    except (InvalidOperation,AttributeError): return None
