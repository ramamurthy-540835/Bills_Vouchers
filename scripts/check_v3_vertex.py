"""Exercise real Vertex schema without saving generated/test bills anywhere."""
import json
import os
import subprocess
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from google import genai
from google.oauth2.credentials import Credentials
from PIL import Image, ImageDraw
from app.config import get_settings
from app.gst.extract import extract

cloud_env = {k: v for k, v in os.environ.items() if k.upper() != 'PYTHONPATH'}
token = subprocess.check_output(['gcloud.cmd', 'auth', 'print-access-token'], env=cloud_env, text=True).strip()
os.environ.update(GCP_PROJECT_ID='aidirac-503309', GCP_REGION='asia-south1', GEMINI_MODEL='gemini-2.5-flash', GEMINI_ENABLED='true')
get_settings.cache_clear()
image = Image.new('RGB', (1000, 600), 'white')
ImageDraw.Draw(image).multiline_text((30,30), 'SCHEMA CHECK ONLY - NOT A CUSTOMER BILL\nInvoice: CHECK-001\nDate: 01-09-2026\nSupplier: Test supplier\nRecipient: Test business\nGSTIN not supplied\nDescription: Office software\nSAC: 998313\nTaxable value: 1000.00\nCGST: 90.00\nSGST: 90.00\nIGST: 0.00\nCess: 0.00\nTotal: 1180.00\nPlace of supply: 33', fill='black', spacing=8, font_size=22)
buffer=BytesIO();image.save(buffer,format='PNG')
client=genai.Client(vertexai=True,project='aidirac-503309',location='asia-south1',credentials=Credentials(token))
usage=[]
with patch('app.gst.extract.genai.Client', return_value=client):
    results=extract(buffer.getvalue(),'schema-check.png','schema-check','schema-check',{},'memory://schema-check',lambda a,b:usage.append({'input':a,'output':b}))
assert len(results)==1 and results[0].invoice_number=='CHECK-001'
assert str(results[0].totals.invoice_total)=='1180.00'
Path('artifacts/v3').mkdir(parents=True,exist_ok=True)
Path('artifacts/v3/vertex-schema.json').write_text(json.dumps({'passed':True,'persisted_records':0,'usage':usage},indent=2))
print('PASS real Vertex image extraction/schema; no records or source files persisted.')
