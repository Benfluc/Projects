-- =====================================================================
-- AML 4 | ALERT QUEUE AND DETECTION SCORECARD
-- A rule is only useful if it finds the real cases without burying the
-- investigators in false alarms. This compares every alert with the
-- cases confirmed by investigators (marts.aml_case_labels):
--   precision = share of alerts that are real cases
--   recall    = share of real cases that raised an alert
-- Techniques: UNION ALL into one alert queue, unnest of an array,
--             EXISTS semi-joins with time-overlap logic.
-- =====================================================================

-- One queue with every alert at account level. Materialized so that the
-- three detection rules run once, not once per comparison below.
CREATE MATERIALIZED VIEW analytics.aml_alerts AS
SELECT 'structuring' AS typology, account_id, first_txn_ts, last_txn_ts,
       format('%s cash deposits, EUR %s in total', deposits, to_char(total_amount, 'FM999,999,990'))
           AS detail
FROM analytics.aml_structuring_alerts
UNION ALL
SELECT 'velocity', account_id, first_txn_ts, last_txn_ts,
       format('%s card payments within one hour', peak_txns_in_one_hour)
FROM analytics.aml_velocity_alerts
UNION ALL
SELECT DISTINCT 'circular_flow', member.account_id, r.first_txn_ts, r.last_txn_ts,
       format('ring of %s accounts, EUR %s sent', r.hops, to_char(r.amount_sent, 'FM999,999,990'))
FROM analytics.aml_circular_flow_alerts AS r
CROSS JOIN LATERAL unnest(r.path[1:r.hops]) AS member (account_id);

CREATE INDEX ix_aml_alerts ON analytics.aml_alerts (typology, account_id);

CREATE VIEW analytics.aml_detection_scorecard AS
WITH alerts AS (
    SELECT a.typology,
           EXISTS (SELECT 1 FROM marts.aml_case_labels AS l
                   WHERE l.typology = a.typology
                     AND l.account_id = a.account_id
                     AND l.first_txn_ts <= a.last_txn_ts
                     AND l.last_txn_ts  >= a.first_txn_ts) AS is_true_positive
    FROM analytics.aml_alerts AS a
),
cases AS (
    SELECT l.typology,
           EXISTS (SELECT 1 FROM analytics.aml_alerts AS a
                   WHERE a.typology = l.typology
                     AND a.account_id = l.account_id
                     AND l.first_txn_ts <= a.last_txn_ts
                     AND l.last_txn_ts  >= a.first_txn_ts) AS was_detected
    FROM marts.aml_case_labels AS l
),
alert_stats AS (
    SELECT typology, COUNT(*) AS alerts,
           COUNT(*) FILTER (WHERE is_true_positive)     AS true_positives,
           COUNT(*) FILTER (WHERE NOT is_true_positive) AS false_positives
    FROM alerts GROUP BY typology
),
case_stats AS (
    SELECT typology, COUNT(*) AS confirmed_cases,
           COUNT(*) FILTER (WHERE NOT was_detected) AS missed_cases
    FROM cases GROUP BY typology
)
SELECT typology, c.confirmed_cases, a.alerts, a.true_positives, a.false_positives,
       c.missed_cases,
       ROUND(100.0 * a.true_positives / a.alerts, 1)                              AS precision_pct,
       ROUND(100.0 * (c.confirmed_cases - c.missed_cases) / c.confirmed_cases, 1) AS recall_pct
FROM case_stats AS c
JOIN alert_stats AS a USING (typology)
ORDER BY typology;
