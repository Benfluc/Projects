-- =====================================================================
-- 01 | RAW LAYER
-- Landing tables for the CSV extracts. Every column is TEXT on purpose:
-- nothing is rejected at load time, and all typing, cleaning and
-- validation happens in the staging layer where it can be audited.
-- =====================================================================
DROP SCHEMA IF EXISTS analytics CASCADE;
DROP SCHEMA IF EXISTS dq CASCADE;
DROP SCHEMA IF EXISTS marts CASCADE;
DROP SCHEMA IF EXISTS staging CASCADE;
DROP SCHEMA IF EXISTS raw CASCADE;

CREATE SCHEMA raw;

CREATE TABLE raw.branches (
    branch_id TEXT, branch_name TEXT, town TEXT, county TEXT
);

CREATE TABLE raw.products (
    product_id TEXT, product_name TEXT, product_family TEXT
);

CREATE TABLE raw.customers (
    customer_id TEXT, customer_type TEXT, segment TEXT, birth_date TEXT,
    join_date TEXT, branch_id TEXT, risk_rating TEXT, closed_date TEXT, county TEXT
);

CREATE TABLE raw.accounts (
    account_id TEXT, customer_id TEXT, account_type TEXT,
    open_date TEXT, close_date TEXT, status TEXT
);

CREATE TABLE raw.customer_products (
    holding_id TEXT, customer_id TEXT, product_id TEXT, open_date TEXT, close_date TEXT
);

CREATE TABLE raw.transactions (
    txn_id TEXT, account_id TEXT, txn_ts TEXT, amount TEXT, direction TEXT,
    channel TEXT, counterparty_account_id TEXT, merchant_category TEXT
);

CREATE TABLE raw.loans (
    loan_id TEXT, customer_id TEXT, product_id TEXT, origination_date TEXT,
    principal TEXT, annual_rate_pct TEXT, term_months TEXT, instalment TEXT,
    status TEXT, end_date TEXT
);

CREATE TABLE raw.loan_payments (
    loan_id TEXT, instalment_no TEXT, due_date TEXT, due_amount TEXT,
    principal_component TEXT, interest_component TEXT, paid_date TEXT, paid_amount TEXT
);

CREATE TABLE raw.aml_case_labels (
    case_id TEXT, typology TEXT, account_id TEXT, customer_id TEXT,
    first_txn_ts TEXT, last_txn_ts TEXT
);
