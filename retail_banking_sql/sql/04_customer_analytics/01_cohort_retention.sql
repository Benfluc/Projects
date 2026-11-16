-- =====================================================================
-- CUSTOMERS 1 | COHORT RETENTION
-- Business question: of the customers who joined in a given month, how
-- many are still transacting 1, 3, 6 and 12 months later?
-- Techniques: cohort assignment, month arithmetic, window functions,
--             conditional aggregation (FILTER) to pivot.
-- =====================================================================

-- Long format: one row per cohort and month since joining.
CREATE VIEW analytics.cohort_retention AS
WITH cohort AS (
    SELECT customer_id,
           date_trunc('month', join_date)::date AS cohort_month
    FROM marts.dim_customer
    WHERE join_date >= DATE '2024-01-01'
      AND join_date <  DATE '2025-01-01'       -- 2024 joiners: 12+ months of history
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS customers
    FROM cohort
    GROUP BY cohort_month
),
activity AS (
    SELECT c.cohort_month,
           marts.months_between(a.activity_month, c.cohort_month) AS months_since_join,
           COUNT(*) AS active_customers
    FROM cohort AS c
    JOIN marts.customer_monthly_activity AS a USING (customer_id)
    GROUP BY c.cohort_month, marts.months_between(a.activity_month, c.cohort_month)
)
SELECT a.cohort_month,
       s.customers AS cohort_size,
       a.months_since_join,
       a.active_customers,
       ROUND(100.0 * a.active_customers / s.customers, 1) AS retention_pct,
       -- change against the previous month of the same cohort
       ROUND(100.0 * (a.active_customers
                      - LAG(a.active_customers) OVER (
                            PARTITION BY a.cohort_month ORDER BY a.months_since_join))
             / s.customers, 1) AS change_pp
FROM activity AS a
JOIN cohort_size AS s USING (cohort_month);

-- Classic retention triangle: one row per cohort.
CREATE VIEW analytics.cohort_retention_matrix AS
SELECT cohort_month,
       cohort_size,
       MAX(retention_pct) FILTER (WHERE months_since_join = 1)  AS month_1,
       MAX(retention_pct) FILTER (WHERE months_since_join = 3)  AS month_3,
       MAX(retention_pct) FILTER (WHERE months_since_join = 6)  AS month_6,
       MAX(retention_pct) FILTER (WHERE months_since_join = 9)  AS month_9,
       MAX(retention_pct) FILTER (WHERE months_since_join = 12) AS month_12
FROM analytics.cohort_retention
GROUP BY cohort_month, cohort_size
ORDER BY cohort_month;
