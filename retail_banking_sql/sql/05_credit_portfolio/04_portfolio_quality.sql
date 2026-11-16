-- =====================================================================
-- CREDIT 4 | PORTFOLIO QUALITY OVER TIME AND BY SEGMENT
-- Business question: how big is the loan book, how much of it is
-- non-performing (90+ days past due), and where is the problem?
-- Techniques: LAG for month-on-month change, moving average with a ROWS
--             frame, ROLLUP with GROUPING() for subtotals.
-- =====================================================================

-- Monthly trend of the live loan book.
CREATE VIEW analytics.portfolio_monthly_trend AS
WITH monthly AS (
    SELECT snapshot_date,
           COUNT(*)                                                  AS live_loans,
           SUM(outstanding_balance)                                  AS outstanding,
           SUM(outstanding_balance) FILTER (WHERE bucket = '90+ days') AS npl_balance
    FROM analytics.loan_monthly_snapshot
    WHERE bucket NOT IN ('Charged off', 'Paid off')
    GROUP BY snapshot_date
)
SELECT snapshot_date, live_loans,
       ROUND(outstanding / 1e6, 2)                             AS outstanding_eur_m,
       ROUND(100.0 * COALESCE(npl_balance, 0) / outstanding, 2) AS npl_ratio_pct,
       ROUND(100.0 * COALESCE(npl_balance, 0) / outstanding
           - LAG(100.0 * COALESCE(npl_balance, 0) / outstanding) OVER (ORDER BY snapshot_date), 2)
                                                               AS change_pp,
       ROUND(AVG(100.0 * COALESCE(npl_balance, 0) / outstanding) OVER (
                 ORDER BY snapshot_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)
                                                               AS npl_ratio_3m_avg
FROM monthly;

-- Today's book by product and risk rating, with subtotals and a grand total.
CREATE VIEW analytics.portfolio_by_product_and_rating AS
SELECT CASE WHEN GROUPING(p.product_name) = 1 THEN 'ALL PRODUCTS' ELSE p.product_name END AS product,
       CASE WHEN GROUPING(c.risk_rating) = 1 THEN 'all' ELSE c.risk_rating::text END      AS risk_rating,
       COUNT(*)                                                    AS live_loans,
       ROUND(SUM(s.outstanding_balance) / 1e6, 2)                  AS outstanding_eur_m,
       ROUND(100.0 * COALESCE(SUM(s.outstanding_balance) FILTER (WHERE s.bucket <> 'Current'), 0)
             / SUM(s.outstanding_balance), 2)                      AS in_arrears_pct,
       ROUND(100.0 * COALESCE(SUM(s.outstanding_balance) FILTER (WHERE s.bucket = '90+ days'), 0)
             / SUM(s.outstanding_balance), 2)                      AS npl_ratio_pct,
       GROUPING(p.product_name) AS is_grand_total,
       GROUPING(c.risk_rating)  AS is_subtotal
FROM analytics.loan_monthly_snapshot AS s
JOIN marts.dim_product  AS p USING (product_id)
JOIN marts.dim_customer AS c USING (customer_id)
WHERE s.snapshot_date = marts.as_of()
  AND s.bucket NOT IN ('Charged off', 'Paid off')
GROUP BY ROLLUP (p.product_name, c.risk_rating)
ORDER BY GROUPING(p.product_name), p.product_name, GROUPING(c.risk_rating), c.risk_rating;
