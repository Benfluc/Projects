-- =====================================================================
-- DATA QUALITY 1 | WHAT WAS WRONG WITH THE RAW DATA?
-- A profile of the problems found and fixed in staging, and a
-- reconciliation proving that no row was lost on the way.
-- =====================================================================

-- Rejected transaction rows, by reason.
CREATE VIEW dq.rejected_transactions_summary AS
SELECT reject_reason,
       COUNT(*)                                             AS rows_rejected,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)   AS pct_of_rejects
FROM staging.rejected_transactions
GROUP BY reject_reason
ORDER BY rows_rejected DESC;

-- Raw rows = loaded rows + rejected rows, for every table that is cleaned.
CREATE VIEW dq.load_reconciliation AS
SELECT 'transactions' AS dataset,
       (SELECT COUNT(*) FROM raw.transactions)              AS raw_rows,
       (SELECT COUNT(*) FROM marts.fact_transactions)       AS loaded_rows,
       (SELECT COUNT(*) FROM staging.rejected_transactions) AS rejected_rows
UNION ALL
SELECT 'customers',
       (SELECT COUNT(*) FROM raw.customers),
       (SELECT COUNT(*) FROM marts.dim_customer),
       (SELECT COUNT(*) - COUNT(DISTINCT customer_id) FROM raw.customers)
UNION ALL
SELECT 'loan_payments',
       (SELECT COUNT(*) FROM raw.loan_payments),
       (SELECT COUNT(*) FROM marts.fact_loan_payments),
       (SELECT COUNT(*) FROM raw.loan_payments)
     - (SELECT COUNT(*) FROM (SELECT DISTINCT * FROM raw.loan_payments) AS d);

-- Inconsistent county spellings that staging standardised.
CREATE VIEW dq.county_spelling_variants AS
SELECT INITCAP(TRIM(county))                  AS clean_county,
       COUNT(DISTINCT county)                 AS raw_spellings,
       COUNT(*) FILTER (WHERE county <> INITCAP(TRIM(county))) AS rows_fixed
FROM raw.customers
GROUP BY INITCAP(TRIM(county))
HAVING COUNT(DISTINCT county) > 1
ORDER BY rows_fixed DESC;
