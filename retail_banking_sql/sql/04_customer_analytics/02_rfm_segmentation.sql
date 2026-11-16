-- =====================================================================
-- CUSTOMERS 2 | RFM SEGMENTATION
-- Business question: which customers are the most valuable, and which
-- valuable customers are drifting away?
-- Recency  = days since the last transaction
-- Frequency = transactions in the last 12 months
-- Monetary  = amount spent (debits) in the last 12 months
-- Techniques: NTILE quintiles, named segments with CASE, share of total
--             with SUM() OVER ().
-- =====================================================================

CREATE VIEW analytics.rfm_scores AS
WITH last_12_months AS (
    SELECT c.customer_id, c.segment AS bank_segment,
           marts.as_of() - MAX(a.last_txn_date)   AS recency_days,
           SUM(a.txn_count)                       AS frequency,
           COALESCE(SUM(a.debit_amount), 0)       AS monetary
    FROM marts.dim_customer AS c
    JOIN marts.customer_monthly_activity AS a USING (customer_id)
    WHERE NOT c.is_closed
      AND a.activity_month >= date_trunc('month', marts.as_of())::date - INTERVAL '11 months'
    GROUP BY c.customer_id, c.segment
),
scored AS (
    SELECT *,
           -- customer_id breaks ties, so the quintiles are identical on every run
           NTILE(5) OVER (ORDER BY recency_days DESC, customer_id) AS r_score,  -- 5 = most recent
           NTILE(5) OVER (ORDER BY frequency, customer_id)         AS f_score,  -- 5 = most frequent
           NTILE(5) OVER (ORDER BY monetary, customer_id)          AS m_score   -- 5 = highest spend
    FROM last_12_months
)
SELECT *,
       CASE
           WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
           WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal'
           WHEN r_score <= 2 AND (f_score >= 4 OR m_score >= 4) THEN 'At risk (high value)'
           WHEN r_score <= 2                                   THEN 'Hibernating'
           WHEN r_score >= 4                                   THEN 'Recent, low engagement'
           ELSE 'Needs attention'
       END AS rfm_segment
FROM scored;

CREATE VIEW analytics.rfm_segment_summary AS
SELECT rfm_segment,
       COUNT(*)                                                  AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)        AS pct_of_customers,
       ROUND(AVG(recency_days))                                  AS avg_recency_days,
       ROUND(AVG(frequency), 1)                                  AS avg_txns_12m,
       ROUND(AVG(monetary))                                      AS avg_spend_12m,
       ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS pct_of_total_spend
FROM analytics.rfm_scores
GROUP BY rfm_segment
ORDER BY pct_of_total_spend DESC;
