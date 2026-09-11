-- Phase 1 CA-firm GST compliance foundation. All additions are backward-compatible.
CREATE TABLE IF NOT EXISTS `PROJECT_ID.finance_analytics.client_gst_profiles` (
  client_id STRING NOT NULL,
  trade_name STRING,
  pan STRING,
  state STRING,
  registration_type STRING,
  filing_frequency STRING,
  financial_year STRING,
  contact_person STRING,
  phone STRING,
  email STRING,
  assigned_staff_id STRING,
  partner_id STRING,
  client_status STRING,
  updated_at TIMESTAMP
) PARTITION BY DATE(updated_at) CLUSTER BY client_id;

CREATE TABLE IF NOT EXISTS `PROJECT_ID.finance_analytics.gst_returns` (
  id STRING NOT NULL,
  client_id STRING NOT NULL,
  return_type STRING NOT NULL,
  period DATE NOT NULL,
  due_date DATE,
  status STRING NOT NULL,
  prepared_by_id STRING,
  reviewed_by_id STRING,
  tax_liability NUMERIC,
  itc NUMERIC,
  cash_payable NUMERIC,
  filed_date DATE,
  arn STRING,
  workflow_step STRING,
  client_approval_status STRING,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) PARTITION BY period CLUSTER BY client_id, status;

CREATE TABLE IF NOT EXISTS `PROJECT_ID.finance_analytics.gst_tasks` (
  id STRING NOT NULL,
  client_id STRING NOT NULL,
  return_id STRING,
  task STRING NOT NULL,
  assigned_staff_id STRING,
  due_date DATE,
  priority STRING,
  status STRING,
  remarks STRING,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY client_id, status;

CREATE TABLE IF NOT EXISTS `PROJECT_ID.finance_analytics.client_preferences` (
  id STRING NOT NULL,
  user_id STRING NOT NULL,
  client_id STRING NOT NULL,
  is_favorite BOOL,
  last_used_at TIMESTAMP,
  created_at TIMESTAMP
) PARTITION BY DATE(created_at) CLUSTER BY client_id, user_id;
