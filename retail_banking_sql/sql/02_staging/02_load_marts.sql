-- =====================================================================
-- LOAD THE STAR SCHEMA FROM STAGING
-- =====================================================================

INSERT INTO marts.dim_date
SELECT d::date,
       EXTRACT(YEAR FROM d),
       EXTRACT(QUARTER FROM d),
       EXTRACT(MONTH FROM d),
       date_trunc('month', d)::date,
       to_char(d, 'Mon YYYY'),
       EXTRACT(ISODOW FROM d),
       EXTRACT(ISODOW FROM d) IN (6, 7),
       d::date = (date_trunc('month', d) + INTERVAL '1 month - 1 day')::date
-- TIMESTAMP (not DATE) bounds keep the series free of daylight-saving shifts,
-- whatever the session time zone is.
FROM generate_series(TIMESTAMP '2018-01-01', marts.as_of()::timestamp, INTERVAL '1 day') AS d;

INSERT INTO marts.dim_branch  SELECT * FROM staging.stg_branches;
INSERT INTO marts.dim_product SELECT * FROM staging.stg_products;

INSERT INTO marts.dim_customer
SELECT c.customer_id, c.customer_type, c.segment, c.birth_date,
       CASE
           WHEN c.birth_date IS NULL THEN 'n/a (business)'
           WHEN age.years < 25 THEN '18-24'
           WHEN age.years < 35 THEN '25-34'
           WHEN age.years < 50 THEN '35-49'
           WHEN age.years < 65 THEN '50-64'
           ELSE '65+'
       END,
       c.join_date, c.branch_id, b.county, c.risk_rating, c.closed_date,
       c.closed_date IS NOT NULL
FROM staging.stg_customers AS c
JOIN staging.stg_branches AS b USING (branch_id)
CROSS JOIN LATERAL (
    SELECT EXTRACT(YEAR FROM age(marts.as_of(), c.birth_date)) AS years
) AS age;

INSERT INTO marts.dim_account           SELECT * FROM staging.stg_accounts;
INSERT INTO marts.fact_product_holdings SELECT * FROM staging.stg_customer_products;
INSERT INTO marts.fact_loans            SELECT * FROM staging.stg_loans;
INSERT INTO marts.fact_loan_payments    SELECT * FROM staging.stg_loan_payments;
INSERT INTO marts.aml_case_labels       SELECT * FROM staging.stg_aml_case_labels;

-- Rows are routed to the right monthly partition automatically.
INSERT INTO marts.fact_transactions
SELECT txn_id, account_id, customer_id, txn_ts, txn_ts::date, amount, direction,
       CASE direction WHEN 'C' THEN amount ELSE -amount END,
       channel, counterparty_account_id, merchant_category
FROM staging.stg_transactions;

-- ---------------------------------------------------------------------
-- Indexes (created after the bulk load, which is faster)
-- ---------------------------------------------------------------------
CREATE INDEX ix_txn_account_ts  ON marts.fact_transactions (account_id, txn_ts);
CREATE INDEX ix_txn_customer_ts ON marts.fact_transactions (customer_id, txn_ts);
-- Partial indexes: small, and tailored to the AML rules in module 06.
CREATE INDEX ix_txn_cash_deposits ON marts.fact_transactions (account_id, txn_ts)
    WHERE channel = 'cash_deposit';
CREATE INDEX ix_txn_internal_transfers ON marts.fact_transactions (account_id, txn_ts)
    WHERE counterparty_account_id IS NOT NULL;

CREATE INDEX ix_account_customer  ON marts.dim_account (customer_id);
CREATE INDEX ix_holdings_customer ON marts.fact_product_holdings (customer_id, product_id);
CREATE INDEX ix_loans_customer    ON marts.fact_loans (customer_id);
CREATE INDEX ix_payments_due      ON marts.fact_loan_payments (loan_id, due_date);

-- ---------------------------------------------------------------------
-- Pre-aggregated monthly activity per customer. Cohort, RFM and churn
-- queries read this instead of scanning 1.4 million transactions.
-- The unique index allows REFRESH ... CONCURRENTLY (see module 07).
-- ---------------------------------------------------------------------
CREATE MATERIALIZED VIEW marts.customer_monthly_activity AS
SELECT customer_id,
       date_trunc('month', txn_ts)::date                AS activity_month,
       COUNT(*)                                         AS txn_count,
       SUM(amount) FILTER (WHERE direction = 'D')       AS debit_amount,
       SUM(amount) FILTER (WHERE direction = 'C')       AS credit_amount,
       MAX(txn_ts)::date                                AS last_txn_date
FROM marts.fact_transactions
GROUP BY customer_id, date_trunc('month', txn_ts);

CREATE UNIQUE INDEX ux_customer_monthly_activity
    ON marts.customer_monthly_activity (customer_id, activity_month);

ANALYZE;
