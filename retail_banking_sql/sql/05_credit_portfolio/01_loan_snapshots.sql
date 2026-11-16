-- =====================================================================
-- CREDIT 1 | MONTH-END LOAN SNAPSHOTS
-- The repayment schedule only says when each instalment was due and
-- when it was paid. Credit-risk reporting needs the state of every loan
-- at every month-end: days past due, delinquency bucket and balance.
-- Techniques: date-dimension join to generate the snapshots, LATERAL
--             subquery, FILTER, materialized view.
-- =====================================================================
CREATE MATERIALIZED VIEW analytics.loan_monthly_snapshot AS
SELECT l.loan_id, l.customer_id, l.product_id, l.origination_date,
       m.date_key                                             AS snapshot_date,
       marts.months_between(m.date_key, l.origination_date)   AS months_on_book,
       COALESCE(m.date_key - arrears.oldest_unpaid_due, 0)    AS days_past_due,
       l.principal - arrears.principal_repaid                 AS outstanding_balance,
       CASE
           WHEN l.status = 'charged_off' AND m.date_key >= l.end_date THEN 'Charged off'
           WHEN l.status = 'paid_off'    AND m.date_key >= l.end_date THEN 'Paid off'
           WHEN arrears.oldest_unpaid_due IS NULL                     THEN 'Current'
           WHEN m.date_key - arrears.oldest_unpaid_due <= 30          THEN '1-30 days'
           WHEN m.date_key - arrears.oldest_unpaid_due <= 60          THEN '31-60 days'
           WHEN m.date_key - arrears.oldest_unpaid_due <= 90          THEN '61-90 days'
           ELSE '90+ days'
       END AS bucket
FROM marts.fact_loans AS l
JOIN marts.dim_date AS m
  ON m.is_month_end
 AND m.date_key > l.origination_date
 -- closed loans get one final snapshot in the month they end
 AND m.date_key <= COALESCE(
        (date_trunc('month', l.end_date) + INTERVAL '1 month - 1 day')::date, marts.as_of())
CROSS JOIN LATERAL (
    SELECT -- oldest instalment that was due but still unpaid on the snapshot date
           MIN(p.due_date) FILTER (
               WHERE p.due_date < m.date_key
                 AND (p.paid_date IS NULL OR p.paid_date > m.date_key)) AS oldest_unpaid_due,
           COALESCE(SUM(p.principal_component) FILTER (
               WHERE p.paid_date <= m.date_key), 0)                     AS principal_repaid
    FROM marts.fact_loan_payments AS p
    WHERE p.loan_id = l.loan_id
) AS arrears;

CREATE UNIQUE INDEX ux_loan_snapshot ON analytics.loan_monthly_snapshot (loan_id, snapshot_date);
CREATE INDEX ix_loan_snapshot_date ON analytics.loan_monthly_snapshot (snapshot_date);

-- Display order for the delinquency buckets.
CREATE VIEW analytics.bucket_order AS
SELECT * FROM (VALUES ('Current', 1), ('1-30 days', 2), ('31-60 days', 3), ('61-90 days', 4),
                      ('90+ days', 5), ('Charged off', 6), ('Paid off', 7)) AS b (bucket, sort_no);
