-- =====================================================================
-- PERFORMANCE 1 | MEASURING THE DESIGN DECISIONS
-- Three experiments with EXPLAIN ANALYZE. Each one runs the same query
-- twice: without and with the optimisation.
-- Timings depend on the machine; what matters is the change in plan.
-- =====================================================================
\pset pager off

\echo
\echo '=== EXPERIMENT 1: composite index on (account_id, txn_ts) ==='
\echo '--- Query: one account, last six months of transactions'
\echo '--- 1a. WITHOUT the index (dropped inside a transaction, then rolled back)'
BEGIN;
DROP INDEX marts.ix_txn_account_ts;
DROP INDEX marts.ix_txn_internal_transfers;
DROP INDEX marts.ix_txn_cash_deposits;
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, BUFFERS)
SELECT txn_ts, channel, signed_amount
FROM marts.fact_transactions
WHERE account_id = 100079
  AND txn_ts >= TIMESTAMP '2025-07-01'
ORDER BY txn_ts;
ROLLBACK;

\echo '--- 1b. WITH the index'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, BUFFERS)
SELECT txn_ts, channel, signed_amount
FROM marts.fact_transactions
WHERE account_id = 100079
  AND txn_ts >= TIMESTAMP '2025-07-01'
ORDER BY txn_ts;

\echo
\echo '=== EXPERIMENT 2: partition pruning ==='
\echo '--- Query: totals by channel for November 2025'
\echo '--- 2a. Pruning switched OFF: all 24 monthly partitions are scanned'
SET enable_partition_pruning = off;
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, BUFFERS)
SELECT channel, COUNT(*), SUM(amount)
FROM marts.fact_transactions
WHERE txn_ts >= TIMESTAMP '2025-11-01' AND txn_ts < TIMESTAMP '2025-12-01'
GROUP BY channel;

\echo '--- 2b. Pruning ON (the default): only the November partition is read'
RESET enable_partition_pruning;
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, BUFFERS)
SELECT channel, COUNT(*), SUM(amount)
FROM marts.fact_transactions
WHERE txn_ts >= TIMESTAMP '2025-11-01' AND txn_ts < TIMESTAMP '2025-12-01'
GROUP BY channel;

\echo
\echo '=== EXPERIMENT 3: materialized view for monthly activity ==='
\echo '--- Query: active customers per month'
\echo '--- 3a. From the transaction fact (1.4 million rows)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, BUFFERS)
SELECT date_trunc('month', txn_ts)::date AS activity_month,
       COUNT(DISTINCT customer_id)       AS active_customers
FROM marts.fact_transactions
GROUP BY 1;

\echo '--- 3b. From marts.customer_monthly_activity'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, BUFFERS)
SELECT activity_month, COUNT(*) AS active_customers
FROM marts.customer_monthly_activity
GROUP BY activity_month;
