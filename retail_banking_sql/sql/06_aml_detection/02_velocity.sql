-- =====================================================================
-- AML 2 | TRANSACTION VELOCITY
-- Typology: a burst of card payments in a very short time, typical of a
-- compromised account or of rapid cash-out through a merchant.
-- Rule: 10 or more card payments on the same account within 60 minutes.
-- Techniques: time-based sliding window with a RANGE frame
--             (RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND CURRENT ROW),
--             named WINDOW clause, then sessionisation of flagged rows.
-- =====================================================================
CREATE VIEW analytics.aml_velocity_alerts AS
WITH sliding AS (
    SELECT account_id, customer_id, txn_ts, amount,
           COUNT(*)    OVER one_hour AS txns_last_hour,
           SUM(amount) OVER one_hour AS amount_last_hour
    FROM marts.fact_transactions
    WHERE channel = 'card'
    WINDOW one_hour AS (PARTITION BY account_id ORDER BY txn_ts
                        RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND CURRENT ROW)
),
flagged AS (
    SELECT *,
           txn_ts - LAG(txn_ts) OVER (PARTITION BY account_id ORDER BY txn_ts) AS gap
    FROM sliding
    WHERE txns_last_hour >= 10
),
bursts AS (
    SELECT *,
           SUM(CASE WHEN gap IS NULL OR gap > INTERVAL '1 hour' THEN 1 ELSE 0 END)
               OVER (PARTITION BY account_id ORDER BY txn_ts) AS burst_no
    FROM flagged
)
SELECT account_id, customer_id,
       MIN(txn_ts) - INTERVAL '1 hour' AS first_txn_ts,   -- start of the first full window
       MAX(txn_ts)                     AS last_txn_ts,
       MAX(txns_last_hour)             AS peak_txns_in_one_hour,
       MAX(amount_last_hour)           AS peak_amount_in_one_hour
FROM bursts
GROUP BY account_id, customer_id, burst_no;
