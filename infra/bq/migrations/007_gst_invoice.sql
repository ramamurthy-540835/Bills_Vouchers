CREATE SCHEMA IF NOT EXISTS `aidirac-503309.gold` OPTIONS(location='asia-south1');
CREATE SCHEMA IF NOT EXISTS `aidirac-503309.silver` OPTIONS(location='asia-south1');
CREATE SCHEMA IF NOT EXISTS `aidirac-503309.ops` OPTIONS(location='asia-south1');
CREATE TABLE IF NOT EXISTS `aidirac-503309.gold.gst_invoice` (
 client_id STRING NOT NULL, invoice_id STRING NOT NULL, source_doc_id STRING,
 invoice_date DATE, period STRING, financial_year INT64, supplier_gstin STRING,
 invoice_number STRING, direction STRING, status STRING, eligibility STRING,
 taxable_value NUMERIC(18,2), cgst NUMERIC(18,2), sgst NUMERIC(18,2), igst NUMERIC(18,2),
 cess NUMERIC(18,2), invoice_total NUMERIC(18,2), payload JSON, version INT64,
 created_at TIMESTAMP, updated_at TIMESTAMP
) PARTITION BY invoice_date CLUSTER BY client_id, status, supplier_gstin;
CREATE TABLE IF NOT EXISTS `aidirac-503309.silver.gst_invoice_line` (
 client_id STRING NOT NULL, invoice_id STRING NOT NULL, line_no INT64, invoice_date DATE,
 description STRING, hsn_sac STRING, quantity NUMERIC, unit STRING, gst_rate NUMERIC,
 taxable_value NUMERIC(18,2), cgst NUMERIC(18,2), sgst NUMERIC(18,2), igst NUMERIC(18,2), cess NUMERIC(18,2)
) PARTITION BY invoice_date CLUSTER BY client_id, invoice_id;
CREATE TABLE IF NOT EXISTS `aidirac-503309.ops.gst_bill_job` (
 client_id STRING NOT NULL, job_id STRING NOT NULL, payload JSON, updated_at TIMESTAMP
) CLUSTER BY client_id, job_id;
CREATE TABLE IF NOT EXISTS `aidirac-503309.ops.gst_bill_audit` (
 client_id STRING NOT NULL, invoice_id STRING, actor_id STRING, action STRING,
 before_payload JSON, after_payload JSON, created_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY client_id, invoice_id;
CREATE TABLE IF NOT EXISTS `aidirac-503309.ops.gst_bill_lock` (
 client_id STRING NOT NULL, touched_at TIMESTAMP
) CLUSTER BY client_id;
CREATE TABLE IF NOT EXISTS `aidirac-503309.ops.extraction_log` (
 client_id STRING NOT NULL, source_doc_id STRING, model STRING,
 input_tokens INT64, output_tokens INT64, created_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY client_id;
