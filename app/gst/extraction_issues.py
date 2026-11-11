"""Safe processing diagnostics; provider errors never become invented invoices."""


def issue_for(error, stage='extraction'):
    from app.services.model_access import ModelAccessDenied
    code = getattr(error, 'code', None) or getattr(error, 'status_code', None)
    name = type(error).__name__.lower()
    if isinstance(error, ModelAccessDenied):
        return {'code':'reading_not_authorized','message':'Automatic document reading is not enabled for this business under the current AI data-location policy. Your original is retained. Contact support or use the supported spreadsheet template.', 'retryable':False}
    if stage == 'evidence':
        return {'code':'original_unavailable','message':'The saved original could not be opened. Other files can continue. Retry this upload; contact support if its original remains unavailable.', 'retryable':True}
    if code == 429 or 'resourceexhausted' in name:
        return {'code':'reading_rate_limited','message':'Document reading reached the provider limit. Your original is saved; retry extraction shortly.', 'retryable':True}
    if code in {400,401,403,404}:
        return {'code':'reading_provider_configuration','message':'The document-reading service is unavailable or not authorized. Your original is saved. Contact support; this is not an invoice validation error.', 'retryable':False}
    if isinstance(error, TimeoutError) or 'timeout' in name:
        return {'code':'reading_timeout','message':'Document reading timed out. Your original is saved. Retry extraction; do not upload the same bill again.', 'retryable':True}
    if getattr(error, 'code', None) == 'invalid_extraction_response':
        return {'code':'invalid_extraction_response','message':'The reading service returned incomplete or invalid invoice data. No invoice was created. Retry extraction or use a clearer original.', 'retryable':True}
    if isinstance(error, ValueError):
        # Do not show raw errors: they can contain model responses or private data.
        return {'code':'document_reading_failed','message':'This document could not be interpreted as an invoice. Your original is retained. Check document quality and format, or use the supported spreadsheet template.', 'retryable':False}
    return {'code':'reading_service_failed','message':'The document-reading service failed. Your original is saved; other files continue. Retry extraction shortly.', 'retryable':True}


def legacy_failure(entry):
    return str(entry.get('reason','')).startswith('We could not read all the details.')


def retryable_file(entry):
    return entry.get('status') == 'needs_attention' and bool(entry.get('extraction_issue',{}).get('retryable'))


def clear_reviewed_fields(flags, body, reviewed):
    """An authorized edit must explicitly supply each reviewed evidence value."""
    from fastapi import HTTPException
    known={f.split(':',2)[2] for f in flags if f.startswith('field_issue:')}
    for path in reviewed:
        replacement=path=='line_items' and any(p.startswith('line_items.') for p in known)
        if path not in known and not replacement:
            raise HTTPException(422,'This field is not awaiting extraction review.')
        value=body
        try:
            for part in path.split('.'):
                value=value[int(part)] if isinstance(value,list) else value[part]
        except (KeyError,IndexError,ValueError,TypeError):
            raise HTTPException(422,'Supply the reviewed field value before marking it checked.') from None
        if value is None or (isinstance(value,str) and not value.strip()) or value==[] or value=={}:
            raise HTTPException(422,'Complete the highlighted field before marking it checked.')
    return [f for f in flags if not (f.startswith('field_issue:') and (f.split(':',2)[2] in reviewed
        or ('line_items' in reviewed and f.split(':',2)[2].startswith('line_items.'))))]
