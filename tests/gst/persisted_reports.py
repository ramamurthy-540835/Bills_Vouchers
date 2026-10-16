"""Explicitly seeded SQLite evidence for local tests only; no cloud connection."""
import json
import sqlite3
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from reportlab.pdfgen import canvas
from app.gst.schemas.invoice import GstInvoice, LineItem, Totals, Extraction


def seed(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as db:
        db.executescript('DROP TABLE IF EXISTS invoices; DROP TABLE IF EXISTS statements; DROP TABLE IF EXISTS evidence; CREATE TABLE invoices(id TEXT PRIMARY KEY,client TEXT,payload TEXT); CREATE TABLE statements(client TEXT,period TEXT,payload TEXT); CREATE TABLE evidence(ref TEXT PRIMARY KEY,content BLOB);')
        for client in ('browser-client','browser-readonly'):
            for name,direction,status,hsn,amount in [('PURCHASE-ELIGIBLE','purchase','confirmed','9983',1000),('PURCHASE-BLOCKED','purchase','confirmed','8703',2000),('PURCHASE-MISMATCH','purchase','confirmed','9983',3000),('PURCHASE-MISSING','purchase','confirmed','9983',4000),('SALE','sale','confirmed','9983',5000),('CREDIT-NOTE','sale','confirmed','9983',500),('PENDING','purchase','needs_review','9983',600)]:
                amount=Decimal(amount if client=='browser-client' else amount*2)
                tax=amount*Decimal('.09')
                id=client+'-'+name
                ref='gs://local-synthetic/'+id+'.pdf'
                inv=GstInvoice(invoice_id=id,client_id=client,source_doc_id=id,invoice_number=name,invoice_date=date(2026,9,1),
                    supplier_gstin='33BCDEF2345G1Z0',supplier_legal_name='Synthetic Supplier '+client,recipient_gstin='33ABCDE1234F1Z5',recipient_legal_name='Synthetic Customer '+client,
                    direction=direction,status=status,invoice_type='credit_note' if name=='CREDIT-NOTE' else 'tax_invoice',
                    line_items=[LineItem(description='Synthetic service',hsn_sac=hsn,taxable_value=amount,gst_rate='18',cgst=tax,sgst=tax)],
                    totals=Totals(taxable_value=amount,cgst=tax,sgst=tax,invoice_total=amount+tax*2),
                    extraction=Extraction(raw_ref=ref,confidence='0.92'),review_reasons=['Check supplier details'] if name=='PENDING' else [])
                db.execute('INSERT INTO invoices VALUES(?,?,?)',(id,client,inv.model_dump_json()))
                stream=BytesIO();pdf=canvas.Canvas(stream);pdf.drawString(40,800,'SYNTHETIC LOCAL TEST EVIDENCE: '+id);pdf.save()
                db.execute('INSERT INTO evidence VALUES(?,?)',(ref,stream.getvalue()))
                if name in {'PURCHASE-ELIGIBLE','PURCHASE-BLOCKED','PURCHASE-MISMATCH'}:
                    row={'supplier_gstin':inv.supplier_gstin,'invoice_number':name,'invoice_date':'2026-09-01','itc_available':True,
                         **{key:str(getattr(inv.totals,key)) for key in ('taxable_value','cgst','sgst','igst','cess')}}
                    if name=='PURCHASE-MISMATCH':row['cgst']='1.00'
                    db.execute('INSERT INTO statements VALUES(?,?,?)',(client,'2026-09',json.dumps(row)))
            db.execute('INSERT INTO statements VALUES(?,?,?)',(client,'2026-09',json.dumps({'supplier_gstin':'33BCDEF2345G1Z0','invoice_number':'STATEMENT-ONLY','invoice_date':'2026-09-02','taxable_value':'700','cgst':'63','sgst':'63','igst':'0','cess':'0','itc_available':True})))


def invoices(path,client):
    with sqlite3.connect(path) as db:
        return [GstInvoice.model_validate_json(row[0]) for row in db.execute('SELECT payload FROM invoices WHERE client=? ORDER BY id',(client,))]


def statements(path,client,period):
    with sqlite3.connect(path) as db:
        return [json.loads(row[0]) for row in db.execute('SELECT payload FROM statements WHERE client=? AND period=?',(client,period))]


def original(path,ref):
    with sqlite3.connect(path) as db:
        row=db.execute('SELECT content FROM evidence WHERE ref=?',(ref,)).fetchone()
        return row[0] if row else None
