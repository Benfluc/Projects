-- =====================================================================
-- CREDIT 3 | ROLL RATES
-- Business question: once a loan falls behind, how likely is it to
-- recover, and how likely to get worse?
-- A transition matrix: where loans in each delinquency bucket are one
-- month later.
-- Techniques: LEAD to pair each month with the next, share within group
--             with SUM() OVER (PARTITION BY), pivot with FILTER.
-- =====================================================================
CREATE VIEW analytics.roll_rate_transitions AS
WITH transitions AS (
    SELECT bucket AS from_bucket,
           LEAD(bucket) OVER (PARTITION BY loan_id ORDER BY snapshot_date) AS to_bucket
    FROM analytics.loan_monthly_snapshot
)
SELECT from_bucket, to_bucket,
       COUNT(*) AS loan_months,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY from_bucket), 1) AS pct
FROM transitions
WHERE to_bucket IS NOT NULL
  AND from_bucket NOT IN ('Charged off', 'Paid off')
GROUP BY from_bucket, to_bucket;

CREATE VIEW analytics.roll_rate_matrix AS
SELECT t.from_bucket,
       SUM(t.loan_months)                                              AS loan_months,
       COALESCE(MAX(t.pct) FILTER (WHERE t.to_bucket = 'Current'), 0)     AS to_current,
       COALESCE(MAX(t.pct) FILTER (WHERE t.to_bucket = '1-30 days'), 0)   AS to_1_30,
       COALESCE(MAX(t.pct) FILTER (WHERE t.to_bucket = '31-60 days'), 0)  AS to_31_60,
       COALESCE(MAX(t.pct) FILTER (WHERE t.to_bucket = '61-90 days'), 0)  AS to_61_90,
       COALESCE(MAX(t.pct) FILTER (WHERE t.to_bucket = '90+ days'), 0)    AS to_90_plus,
       COALESCE(MAX(t.pct) FILTER (WHERE t.to_bucket = 'Charged off'), 0) AS to_charged_off,
       COALESCE(MAX(t.pct) FILTER (WHERE t.to_bucket = 'Paid off'), 0)    AS to_paid_off
FROM analytics.roll_rate_transitions AS t
JOIN analytics.bucket_order AS o ON o.bucket = t.from_bucket
GROUP BY t.from_bucket, o.sort_no
ORDER BY o.sort_no;
