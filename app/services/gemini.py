import json
from datetime import date
from .ocr import decimal_or_none
from ..models import ns
from google.cloud import bigquery
FIELDS=['vendor_name','vendor_address','invoice_number','invoice_date','due_date','gstin','subtotal','tax_amount','cgst','sgst','igst','discount_amount','total_amount','currency','payment_method','ocr_text']
SCHEMA={'type':'OBJECT','properties':{k:{'type':'STRING'} for k in FIELDS}}
SCHEMA['properties']['line_items']={'type':'ARRAY','items':{'type':'OBJECT','properties':{k:{'type':'STRING'} for k in ['item_name','description','quantity','unit','unit_price','tax','discount','total']}}}
def scan_document(document,payload):
    from google import genai
    from google.genai import types
    s=__import__('app.config',fromlist=['get_settings']).get_settings(); c=genai.Client(api_key=s.gemini_api_key) if s.gemini_api_key else genai.Client(vertexai=True,project=s.gcp_project_id,location=s.gcp_region)
    r=c.models.generate_content(model=s.gemini_model,contents=[types.Part.from_bytes(data=payload,mime_type=document.mime_type),'Extract this Indian GST bill or voucher. Return only JSON. Never invent missing values. Distinguish CGST+SGST from IGST and preserve original OCR text.'],config=types.GenerateContentConfig(response_mime_type='application/json',response_schema=SCHEMA,temperature=0))
    try: return json.loads(r.text)
    except Exception as exc: raise RuntimeError('Gemini returned invalid structured output.') from exc
def process_with_gemini(repo,document,payload):
    def update_status(set_sql):
        try: repo.bq.update('documents',set_sql,'id=@id',[bigquery.ScalarQueryParameter('id','STRING',document.id)])
        except Exception as exc:
            if 'streaming buffer' not in str(exc).lower(): raise
    update_status("status='processing', processing_error=NULL")
    try: data=scan_document(document,payload)
    except Exception as exc:
        try: repo.bq.update('documents',"status='failed', processing_error=@err",'id=@id',[bigquery.ScalarQueryParameter('id','STRING',document.id),bigquery.ScalarQueryParameter('err','STRING',str(exc)[:2000])])
        except Exception as update_exc:
            if 'streaming buffer' not in str(update_exc).lower(): raise
        raise
    def dt(x):
        try: return date.fromisoformat(str(x)[:10]).isoformat() if x else None
        except ValueError: return None
    def numeric(value):
        parsed=decimal_or_none(value)
        return str(parsed) if parsed is not None else None
    row={'id':document.id,'document_id':document.id,**{k:data.get(k) for k in ['vendor_name','vendor_address','invoice_number','gstin','currency','payment_method','ocr_text']},'invoice_date':dt(data.get('invoice_date')),'due_date':dt(data.get('due_date')),'subtotal':numeric(data.get('subtotal')),'tax_amount':numeric(data.get('tax_amount')),'cgst':numeric(data.get('cgst')),'sgst':numeric(data.get('sgst')),'igst':numeric(data.get('igst')),'discount_amount':numeric(data.get('discount_amount')),'total_amount':numeric(data.get('total_amount')),'ocr_confidence':None,'created_at':str(document.uploaded_at)}
    repo.bq.query(f'DELETE FROM `{repo.bq.table("document_extractions")}` WHERE document_id=@id',[bigquery.ScalarQueryParameter('id','STRING',document.id)]); repo.bq.insert('document_extractions',row,document.id)
    repo.bq.query(f'DELETE FROM `{repo.bq.table("document_line_items")}` WHERE extraction_id=@id',[bigquery.ScalarQueryParameter('id','STRING',document.id)])
    for i,x in enumerate(data.get('line_items') or []): repo.bq.insert('document_line_items',{'id':f'{document.id}-{i}','extraction_id':document.id,'line_number':i,**{k:x.get(k) for k in ['item_name','description','unit']},'quantity':numeric(x.get('quantity')),'unit_price':numeric(x.get('unit_price')),'tax':numeric(x.get('tax')),'discount':numeric(x.get('discount')),'total':numeric(x.get('total'))},f'{document.id}-{i}')
    update_status("status='needs_review', processing_error=NULL")
    return repo.extraction(document.id)
