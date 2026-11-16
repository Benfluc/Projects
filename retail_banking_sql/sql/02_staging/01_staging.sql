-- =====================================================================
-- STAGING LAYER
-- Types, cleans and de-duplicates the raw extracts. Bad transaction rows
-- are not silently dropped: each one is kept in a rejects table with the
-- reason, so the load can be reconciled row by row (see module 03).
-- =====================================================================

CREATE VIEW staging.stg_branches AS
SELECT branch_id::integer, TRIM(branch_name) AS branch_name, TRIM(town) AS town,
       INITCAP(TRIM(county)) AS county
FROM raw.branches;

CREATE VIEW staging.stg_products AS
SELECT product_id::integer, TRIM(product_name) AS product_name,
       TRIM(product_family) AS product_family
FROM raw.products;

-- Customers arrive with exact duplicate rows and inconsistent county text
-- ('CORK', 'cork', '  Cork '). ROW_NUMBER keeps one row per customer.
CREATE VIEW staging.stg_customers AS
WITH ranked AS (
    SELECT c.*,
           ROW_NUMBER() OVER (PARTITION BY c.customer_id ORDER BY c.join_date) AS row_no
    FROM raw.customers AS c
)
SELECT customer_id::integer,
       LOWER(TRIM(customer_type))        AS customer_type,
       LOWER(TRIM(segment))              AS segment,
       NULLIF(birth_date, '')::date      AS birth_date,
       join_date::date                   AS join_date,
       branch_id::integer                AS branch_id,
       INITCAP(TRIM(county))             AS county,
       UPPER(TRIM(risk_rating))::char(1) AS risk_rating,
       NULLIF(closed_date, '')::date     AS closed_date
FROM ranked
WHERE row_no = 1;

CREATE VIEW staging.stg_accounts AS
SELECT account_id::integer, customer_id::integer, LOWER(TRIM(account_type)) AS account_type,
       open_date::date AS open_date, NULLIF(close_date, '')::date AS close_date,
       LOWER(TRIM(status)) AS status
FROM raw.accounts;

CREATE VIEW staging.stg_customer_products AS
SELECT holding_id::integer, customer_id::integer, product_id::integer,
       open_date::date AS open_date, NULLIF(close_date, '')::date AS close_date
FROM raw.customer_products;

CREATE VIEW staging.stg_loans AS
SELECT loan_id::integer, customer_id::integer, product_id::integer,
       origination_date::date AS origination_date, principal::numeric(14, 2) AS principal,
       annual_rate_pct::numeric(5, 2) AS annual_rate_pct, term_months::smallint AS term_months,
       instalment::numeric(14, 2) AS instalment, LOWER(TRIM(status)) AS status,
       NULLIF(end_date, '')::date AS end_date
FROM raw.loans;

-- The repayment extract contains a few repeated rows.
CREATE VIEW staging.stg_loan_payments AS
SELECT DISTINCT
       loan_id::integer, instalment_no::smallint, due_date::date AS due_date,
       due_amount::numeric(14, 2) AS due_amount,
       principal_component::numeric(14, 2) AS principal_component,
       interest_component::numeric(14, 2) AS interest_component,
       NULLIF(paid_date, '')::date AS paid_date,
       NULLIF(paid_amount, '')::numeric(14, 2) AS paid_amount
FROM raw.loan_payments;

CREATE VIEW staging.stg_aml_case_labels AS
SELECT case_id::integer, typology, account_id::integer, customer_id::integer,
       first_txn_ts::timestamp AS first_txn_ts, last_txn_ts::timestamp AS last_txn_ts
FROM raw.aml_case_labels;

-- ---------------------------------------------------------------------
-- Transactions: classify every raw row as valid or rejected.
-- The CASE is ordered, so each row gets exactly one reason.
-- ---------------------------------------------------------------------
CREATE TABLE staging.transactions_classified AS
WITH typed AS (
    SELECT t.txn_id::bigint                              AS txn_id,
           t.account_id::integer                         AS account_id,
           NULLIF(t.txn_ts, '')::timestamp               AS txn_ts,
           t.amount::numeric(14, 2)                      AS amount,
           UPPER(TRIM(t.direction))::char(1)             AS direction,
           LOWER(TRIM(t.channel))                        AS channel,
           NULLIF(t.counterparty_account_id, '')::integer AS counterparty_account_id,
           NULLIF(t.merchant_category, '')               AS merchant_category,
           ROW_NUMBER() OVER (PARTITION BY t.txn_id ORDER BY t.txn_ts) AS copy_no
    FROM raw.transactions AS t
)
SELECT typed.txn_id, typed.account_id, a.customer_id, typed.txn_ts, typed.amount,
       typed.direction, typed.channel, typed.counterparty_account_id,
       typed.merchant_category,
       CASE
           WHEN typed.copy_no > 1       THEN 'duplicate_row'
           WHEN typed.txn_ts IS NULL    THEN 'missing_timestamp'
           WHEN typed.amount <= 0       THEN 'non_positive_amount'
           WHEN a.account_id IS NULL    THEN 'unknown_account'
       END AS reject_reason
FROM typed
LEFT JOIN staging.stg_accounts AS a ON a.account_id = typed.account_id;

CREATE VIEW staging.stg_transactions AS
SELECT txn_id, account_id, customer_id, txn_ts, amount, direction, channel,
       counterparty_account_id, merchant_category
FROM staging.transactions_classified
WHERE reject_reason IS NULL;

CREATE VIEW staging.rejected_transactions AS
SELECT *
FROM staging.transactions_classified
WHERE reject_reason IS NOT NULL;
