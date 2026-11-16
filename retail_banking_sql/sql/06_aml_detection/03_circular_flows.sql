-- =====================================================================
-- AML 3 | CIRCULAR FLOWS ("ROUND-TRIPPING")
-- Typology: money leaves an account, hops through other accounts and
-- comes back to where it started, to disguise its origin.
-- Rule: a chain of 3 to 6 internal transfers of EUR 5,000 or more where
--       each hop happens within 3 days of the previous one, moves 90-100%
--       of the previous amount, and the last hop returns to the origin.
-- Techniques: recursive CTE walking a graph of transfers, an array to
--             record the path and prevent revisiting accounts.
-- =====================================================================
CREATE VIEW analytics.aml_circular_flow_alerts AS
WITH RECURSIVE transfers AS (
    SELECT account_id AS from_account, counterparty_account_id AS to_account,
           txn_ts, amount
    FROM marts.fact_transactions
    WHERE counterparty_account_id IS NOT NULL
      AND channel = 'transfer_out'
      AND amount >= 5000
),
chain AS (
    -- anchor: every large internal transfer may be the first hop of a ring
    SELECT from_account            AS origin_account,
           to_account              AS current_account,
           txn_ts                  AS first_txn_ts,
           txn_ts                  AS last_txn_ts,
           amount                  AS amount_sent,
           amount                  AS last_amount,
           ARRAY[from_account, to_account] AS path,
           1                       AS hops,
           false                   AS is_closed
    FROM transfers

    UNION ALL

    -- recursive step: follow the money one hop further
    SELECT c.origin_account, t.to_account, c.first_txn_ts, t.txn_ts,
           c.amount_sent, t.amount,
           c.path || t.to_account,
           c.hops + 1,
           t.to_account = c.origin_account
    FROM chain AS c
    JOIN transfers AS t
      ON t.from_account = c.current_account
     AND t.txn_ts >  c.last_txn_ts
     AND t.txn_ts <= c.last_txn_ts + INTERVAL '3 days'
     AND t.amount BETWEEN c.last_amount * 0.90 AND c.last_amount
    WHERE NOT c.is_closed
      AND c.hops < 6
      -- either the ring closes, or the next account has not been visited yet
      AND (t.to_account = c.origin_account OR t.to_account <> ALL (c.path))
)
SELECT origin_account,
       path,
       hops,
       first_txn_ts,
       last_txn_ts,
       amount_sent,
       last_amount                                          AS amount_returned,
       ROUND(100 * (1 - last_amount / amount_sent), 2)      AS pct_lost_on_the_way,
       last_txn_ts - first_txn_ts                           AS duration
FROM chain
WHERE is_closed
  AND hops >= 3;
