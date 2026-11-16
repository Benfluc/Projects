-- =====================================================================
-- EXPORT FOR TABLEAU PUBLIC
-- Tableau Public reads files, not databases, so the results are exported
-- as tidy CSV files (one row per observation, no pivoted columns) into
-- tableau/data. Run from the project root after sql/run_all.sql:
--     psql -d retail_bank -f sql/09_export_for_tableau.sql
-- =====================================================================
\set ON_ERROR_STOP on
SET client_min_messages = warning;

DROP SCHEMA IF EXISTS tableau CASCADE;
CREATE SCHEMA tableau;

-- Headline numbers for the KPI tiles.
CREATE VIEW tableau.kpis AS
SELECT 1 AS sort_no, 'Customers' AS metric, COUNT(*)::numeric AS value, 'count' AS unit
FROM marts.dim_customer
UNION ALL
SELECT 2, 'Transactions analysed', COUNT(*), 'count' FROM marts.fact_transactions
UNION ALL
SELECT 3, 'Live loan book (EUR m)', outstanding_eur_m, 'EUR m'
FROM analytics.portfolio_monthly_trend WHERE snapshot_date = marts.as_of()
UNION ALL
SELECT 4, 'Non-performing loans (% of book)', npl_ratio_pct, '%'
FROM analytics.portfolio_monthly_trend WHERE snapshot_date = marts.as_of()
UNION ALL
SELECT 5, 'Customers on churn watchlist', COUNT(*), 'count' FROM analytics.churn_watchlist_today
UNION ALL
SELECT 6, 'AML alerts raised', COUNT(*), 'count' FROM analytics.aml_alerts;

-- Monthly transaction volume by channel.
CREATE VIEW tableau.monthly_transactions AS
SELECT date_trunc('month', txn_ts)::date AS month,
       channel,
       CASE direction WHEN 'C' THEN 'Money in' ELSE 'Money out' END AS direction,
       COUNT(*)    AS transactions,
       SUM(amount) AS amount_eur
FROM marts.fact_transactions
GROUP BY 1, 2, 3;

CREATE VIEW tableau.cohort_retention AS
SELECT cohort_month, cohort_size, months_since_join, active_customers, retention_pct
FROM analytics.cohort_retention
-- month 0 is the partial month in which the customer joined, so it is left out
WHERE months_since_join BETWEEN 1 AND 12;

-- One row per customer, with the bank's own attributes for filtering.
CREATE VIEW tableau.rfm_customers AS
SELECT r.customer_id, c.customer_type, r.bank_segment, c.county, c.age_band, c.risk_rating,
       r.recency_days, r.frequency AS transactions_12m, r.monetary AS spend_12m_eur,
       r.r_score, r.f_score, r.m_score, r.rfm_segment,
       CASE WHEN w.customer_id IS NOT NULL THEN 'On watchlist' ELSE 'Not on watchlist' END
           AS churn_watchlist
FROM analytics.rfm_scores AS r
JOIN marts.dim_customer AS c USING (customer_id)
LEFT JOIN analytics.churn_watchlist_today AS w USING (customer_id);

CREATE VIEW tableau.churn_backtest AS
SELECT customer_group, customers, left_within_6m, closure_rate_pct,
       lift_vs_all_customers, pct_of_all_leavers
FROM analytics.churn_rule_backtest;

CREATE VIEW tableau.product_affinity AS
SELECT if_customer_holds, then_also_holds, customers_with_both,
       support_pct, confidence_pct, lift
FROM analytics.product_affinity;

CREATE VIEW tableau.next_best_product AS
SELECT recommended_product, because_customer_holds, customers_to_contact, confidence_pct, lift
FROM analytics.next_best_product_summary;

CREATE VIEW tableau.vintage_default_curve AS
SELECT vintage, months_on_book, loans_observed, loans_defaulted, cumulative_default_pct
FROM analytics.vintage_default_curve
WHERE months_on_book <= 24;

CREATE VIEW tableau.roll_rates AS
SELECT t.from_bucket, f.sort_no AS from_sort, t.to_bucket, o.sort_no AS to_sort,
       t.loan_months, t.pct
FROM analytics.roll_rate_transitions AS t
JOIN analytics.bucket_order AS f ON f.bucket = t.from_bucket
JOIN analytics.bucket_order AS o ON o.bucket = t.to_bucket;

CREATE VIEW tableau.portfolio_trend AS
SELECT snapshot_date, live_loans, outstanding_eur_m, npl_ratio_pct, npl_ratio_3m_avg
FROM analytics.portfolio_monthly_trend
WHERE snapshot_date >= DATE '2022-01-31';

-- Detail rows only: Tableau computes its own subtotals.
CREATE VIEW tableau.portfolio_by_product_rating AS
SELECT p.product_name AS product, c.risk_rating, s.bucket,
       COUNT(*) AS live_loans, SUM(s.outstanding_balance) AS outstanding_eur
FROM analytics.loan_monthly_snapshot AS s
JOIN marts.dim_product  AS p USING (product_id)
JOIN marts.dim_customer AS c USING (customer_id)
WHERE s.snapshot_date = marts.as_of()
  AND s.bucket NOT IN ('Charged off', 'Paid off')
GROUP BY p.product_name, c.risk_rating, s.bucket;

CREATE VIEW tableau.aml_scorecard AS
SELECT INITCAP(REPLACE(typology, '_', ' ')) AS typology, confirmed_cases, alerts,
       true_positives, false_positives, missed_cases, precision_pct, recall_pct
FROM analytics.aml_detection_scorecard;

CREATE VIEW tableau.aml_rule_tuning AS
SELECT deposits_from_eur, alerts, false_alarms, alerts - false_alarms AS true_alerts,
       precision_pct, recall_pct,
       CASE WHEN deposits_from_eur = 8000 THEN 'Current rule' ELSE 'Alternative' END AS rule_status
FROM analytics.aml_structuring_rule_tuning;

CREATE VIEW tableau.aml_alerts AS
SELECT INITCAP(REPLACE(a.typology, '_', ' ')) AS typology, a.account_id,
       a.first_txn_ts, a.last_txn_ts, date_trunc('month', a.first_txn_ts)::date AS alert_month,
       a.detail,
       CASE WHEN EXISTS (SELECT 1 FROM marts.aml_case_labels AS l
                         WHERE l.typology = a.typology AND l.account_id = a.account_id
                           AND l.first_txn_ts <= a.last_txn_ts
                           AND l.last_txn_ts  >= a.first_txn_ts)
            THEN 'Confirmed case' ELSE 'False alarm' END AS outcome
FROM analytics.aml_alerts AS a;

\copy (SELECT * FROM tableau.kpis ORDER BY sort_no) TO 'tableau/data/kpis.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.monthly_transactions ORDER BY 1, 2, 3) TO 'tableau/data/monthly_transactions.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.cohort_retention ORDER BY 1, 3) TO 'tableau/data/cohort_retention.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.rfm_customers ORDER BY 1) TO 'tableau/data/rfm_customers.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.churn_backtest ORDER BY 1) TO 'tableau/data/churn_backtest.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.product_affinity ORDER BY 1, 2) TO 'tableau/data/product_affinity.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.next_best_product ORDER BY 3 DESC) TO 'tableau/data/next_best_product.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.vintage_default_curve ORDER BY 1, 2) TO 'tableau/data/vintage_default_curve.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.roll_rates ORDER BY 2, 4) TO 'tableau/data/roll_rates.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.portfolio_trend ORDER BY 1) TO 'tableau/data/portfolio_trend.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.portfolio_by_product_rating ORDER BY 1, 2, 3) TO 'tableau/data/portfolio_by_product_rating.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.aml_scorecard ORDER BY 1) TO 'tableau/data/aml_scorecard.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.aml_rule_tuning ORDER BY 1 DESC) TO 'tableau/data/aml_rule_tuning.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM tableau.aml_alerts ORDER BY 3, 2) TO 'tableau/data/aml_alerts.csv' WITH (FORMAT csv, HEADER true)

\echo 'Exported 14 CSV files to tableau/data'
