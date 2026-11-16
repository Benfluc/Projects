-- =====================================================================
-- AML 1 | STRUCTURING ("SMURFING")
-- Typology: cash is paid in as several deposits just below the
-- EUR 10,000 threshold, close together, so that no single deposit stands
-- out.
-- Rule: 3 or more cash deposits of EUR 8,000-9,999.99 into the same
--       account, each no more than 7 days after the previous one.
-- Techniques: sessionisation (gaps-and-islands on timestamps): LAG to
--             find the gap, running SUM of "new episode" flags to number
--             the episodes, HAVING to keep the suspicious ones.
--             The rule is a SQL function so its thresholds can be tuned
--             (see 05_rule_tuning.sql).
-- =====================================================================
CREATE FUNCTION analytics.structuring_episodes(
    min_amount   numeric,
    min_deposits integer,
    max_gap      interval DEFAULT INTERVAL '7 days'
)
RETURNS TABLE (
    account_id    integer,
    customer_id   integer,
    first_txn_ts  timestamp,
    last_txn_ts   timestamp,
    deposits      bigint,
    total_amount  numeric,
    avg_deposit   numeric
)
LANGUAGE sql STABLE
AS $$
    WITH near_threshold AS (
        SELECT t.account_id, t.customer_id, t.txn_ts, t.amount,
               t.txn_ts - LAG(t.txn_ts) OVER (PARTITION BY t.account_id ORDER BY t.txn_ts) AS gap
        FROM marts.fact_transactions AS t
        WHERE t.channel = 'cash_deposit'
          AND t.amount >= min_amount AND t.amount < 10000
    ),
    episodes AS (
        SELECT *,
               -- a long gap (or the first deposit) starts a new episode
               SUM(CASE WHEN gap IS NULL OR gap > max_gap THEN 1 ELSE 0 END)
                   OVER (PARTITION BY account_id ORDER BY txn_ts) AS episode_no
        FROM near_threshold
    )
    SELECT account_id, customer_id, MIN(txn_ts), MAX(txn_ts), COUNT(*),
           SUM(amount), ROUND(AVG(amount), 2)
    FROM episodes
    GROUP BY account_id, customer_id, episode_no
    HAVING COUNT(*) >= min_deposits
$$;

-- The rule in production: EUR 8,000 or more, at least 3 deposits.
CREATE VIEW analytics.aml_structuring_alerts AS
SELECT * FROM analytics.structuring_episodes(8000, 3);
