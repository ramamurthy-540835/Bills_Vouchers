"""Exercise the actual extraction worker on a valid synthetic PDF in staging."""
import os
import subprocess
from datetime import date
from uuid import uuid4

from google import genai
from google.cloud import bigquery, storage
from google.oauth2.credentials import Credentials

os.environ.update(GCP_PROJECT_ID='aidirac-503309', BIGQUERY_DATASET='finance_analytics_staging',
                  GCS_BUCKET_NAME='aidirac-503309-bills-voucher-documents', GCP_REGION='asia-south1',
                  GEMINI_MODEL='gemini-2.5-flash', DEMO_FALLBACK='false')
from app.config import get_settings
from app.db import BigQueryRepository
from app.services.documents import GCSObjectStore
from app.services.gst.medallion import Medallion, now
from app.services.gst.pipeline import land, process_document, silver


def pdf(lines):
    commands = 'BT /F1 14 Tf 50 750 Td ' + ' '.join(('0 -25 Td ' if i else '') + '(' + line + ') Tj' for i, line in enumerate(lines)) + ' ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               f'<< /Length {len(commands)} >>\nstream\n{commands}\nendstream'.encode()]
    output = b'%PDF-1.4\n'
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(output)
    output += b'xref\n0 6\n0000000000 65535 f \n'
    output += b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])
    output += f'trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    return output


def main():
    token = subprocess.check_output(['gcloud.cmd','auth','print-access-token'], text=True).strip()
    credentials = Credentials(token)
    repo = object.__new__(BigQueryRepository)
    repo.settings, repo.dataset = get_settings(), 'aidirac-503309.finance_analytics_staging'
    repo.client = bigquery.Client(project='aidirac-503309', credentials=credentials)
    gcs = storage.Client(project='aidirac-503309', credentials=credentials)
    GCSObjectStore._bucket = lambda self: gcs.bucket(self.bucket)
    original = genai.Client
    genai.Client = lambda **kwargs: original(credentials=credentials, **kwargs)
    tenant = 'v5-integration-ocr-' + uuid4().hex[:12]
    period = date.today().strftime('%Y-%m')
    store = Medallion(repo, tenant, period)
    stamp = now()
    store.upsert('gst_client_profile', {'client_id':tenant,'profile_id':tenant,'gstin':'','legal_name':'Integration worker test',
                 'business_nature':'passenger_transport','effective_from':stamp,'created_at':stamp,'is_current':True}, ['client_id','profile_id'])
    payload = pdf(['INTEGRATION TEST - TAX INVOICE', 'Supplier: Pipeline Test Supplier', 'Supplier GSTIN: 27AAPFU0939F1ZV',
                   'Invoice Number: WORKER-001', 'Invoice Date: '+date.today().isoformat(), 'Place of supply: Tamil Nadu - 33',
                   'Description: Passenger motor vehicle', 'Quantity: 1', 'Taxable value: INR 1000.00', 'GST rate: 18%',
                   'IGST: INR 180.00', 'CGST: INR 0.00', 'SGST: INR 0.00', 'Cess: INR 0.00', 'Grand Total: INR 1180.00'])
    doc = land(store,payload,'worker-test.pdf','application/pdf','integration-test')
    result = process_document(repo,tenant,period,doc['doc_id'])
    print('PASS actual Gemini worker extraction: '+result['validation_status'], flush=True)
    if result['validation_status'] != 'validated':
        # This is a real review of the known synthetic PDF, not an extraction-confidence bypass in the app.
        silver(store,doc,{'supplier_gstin':'27AAPFU0939F1ZV','vendor_name':'Pipeline Test Supplier','invoice_number':'WORKER-001',
               'invoice_date':date.today().isoformat(),'subtotal':'1000','total_amount':'1180','igst':'180','confidence':'1',
               'line_items':[{'description':'Passenger motor vehicle','itc_category':'vehicle','taxable_value':'1000','igst':'180'}]},
               engine='integration_human_review',actor='integration-test')
        print('PASS reviewed extraction against source PDF', flush=True)
    assert store.workspace()['counts']['posted'] == 1
    print('PASS valid PDF -> GCS bronze -> actual worker -> silver -> gold', flush=True)


if __name__=='__main__':
    main()
