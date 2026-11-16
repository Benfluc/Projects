-- =====================================================================
-- CUSTOMERS 3 | ACTIVITY STREAKS AND CHURN EARLY WARNING
-- Business question: who is going quiet, and does going quiet really
-- predict that the customer will leave?
-- Techniques: gaps-and-islands, LEAD, a set-returning SQL function with
--             a date parameter, FILTER, and a back-test of the rule.
-- =====================================================================

-- Gaps and islands: consecutive active months collapse into one streak.
-- month index minus row number is constant inside an unbroken run.
CREATE VIEW analytics.activity_streaks AS
WITH numbered AS (
    SELECT customer_id, activity_month,
           marts.months_between(activity_month, DATE '2024-01-01')
             - ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY activity_month) AS island_id
    FROM marts.customer_monthly_activity
),
streaks AS (
    SELECT customer_id,
           MIN(activity_month) AS streak_start,
           MAX(activity_month) AS streak_end,
           COUNT(*)            AS months_active
    FROM numbered
    GROUP BY customer_id, island_id
)
SELECT customer_id, streak_start, streak_end, months_active,
       -- silent months before the customer became active again (NULL = last streak)
       marts.months_between(
           LEAD(streak_start) OVER (PARTITION BY customer_id ORDER BY streak_start),
           streak_end) - 1 AS silent_months_after
FROM streaks;

-- Early-warning rule, parameterised by date so it can be back-tested:
-- a customer is flagged when activity in the last 90 days fell by 60% or
-- more against their own average of the two previous 90-day periods.
CREATE FUNCTION analytics.churn_watchlist(as_of_date date)
RETURNS TABLE (
    customer_id      integer,
    segment          text,
    last_txn_date    date,
    days_silent      integer,
    baseline_txns    numeric,
    recent_txns      bigint,
    activity_drop_pct numeric
)
LANGUAGE sql STABLE
AS $$
    WITH activity AS (
        SELECT c.customer_id, c.segment,
               MAX(t.txn_date) AS last_txn_date,
               COUNT(*) FILTER (WHERE t.txn_date >  as_of_date - 90) AS recent_txns,
               COUNT(*) FILTER (WHERE t.txn_date <= as_of_date - 90) / 2.0 AS baseline_txns
        FROM marts.dim_customer AS c
        JOIN marts.fact_transactions AS t USING (customer_id)
        WHERE c.join_date <= as_of_date - 270                       -- enough history
          AND (c.closed_date IS NULL OR c.closed_date > as_of_date) -- still a customer
          AND t.txn_ts >  as_of_date - 270
          AND t.txn_ts <  as_of_date + 1
        GROUP BY c.customer_id, c.segment
    )
    SELECT customer_id, segment, last_txn_date,
           as_of_date - last_txn_date,
           baseline_txns, recent_txns,
           ROUND(100.0 * (1 - recent_txns / baseline_txns), 1)
    FROM activity
    WHERE baseline_txns >= 3
      AND recent_txns <= 0.4 * baseline_txns
$$;

-- Today's watchlist, most valuable segments first.
CREATE VIEW analytics.churn_watchlist_today AS
SELECT w.*
FROM analytics.churn_watchlist(marts.as_of()) AS w
ORDER BY CASE w.segment WHEN 'private' THEN 1 WHEN 'affluent' THEN 2
                        WHEN 'sme' THEN 3 ELSE 4 END,
         w.activity_drop_pct DESC;

-- Back-test: apply the rule as of 30 June 2025 and check who actually
-- closed their relationship in the following six months.
CREATE VIEW analytics.churn_rule_backtest AS
WITH population AS (
    SELECT c.customer_id,
           w.customer_id IS NOT NULL AS flagged,
           -- closed_date is NULL for customers who stayed, hence the COALESCE
           COALESCE(c.closed_date BETWEEN DATE '2025-07-01' AND DATE '2025-12-31', false)
               AS left_within_6m
    FROM marts.dim_customer AS c
    LEFT JOIN analytics.churn_watchlist(DATE '2025-06-30') AS w USING (customer_id)
    WHERE c.join_date <= DATE '2025-06-30' - 270
      AND (c.closed_date IS NULL OR c.closed_date > DATE '2025-06-30')
)
SELECT CASE WHEN flagged THEN 'Flagged by the rule' ELSE 'Not flagged' END AS customer_group,
       COUNT(*)                                             AS customers,
       COUNT(*) FILTER (WHERE left_within_6m)               AS left_within_6m,
       ROUND(100.0 * COUNT(*) FILTER (WHERE left_within_6m) / COUNT(*), 1) AS closure_rate_pct,
       -- closure rate of the group divided by the closure rate of everyone
       ROUND((COUNT(*) FILTER (WHERE left_within_6m)::numeric / COUNT(*))
             / (SUM(COUNT(*) FILTER (WHERE left_within_6m)) OVER () / SUM(COUNT(*)) OVER ()), 1)
           AS lift_vs_all_customers,
       ROUND(100.0 * COUNT(*) FILTER (WHERE left_within_6m)
             / SUM(COUNT(*) FILTER (WHERE left_within_6m)) OVER (), 1) AS pct_of_all_leavers
FROM population
GROUP BY flagged
ORDER BY flagged DESC;
