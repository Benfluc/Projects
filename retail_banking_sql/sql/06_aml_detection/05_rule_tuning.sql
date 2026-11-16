-- =====================================================================
-- AML 5 | TUNING THE STRUCTURING RULE
-- Business question: the rule misses launderers who keep their deposits
-- further below the threshold. What does it cost to catch them?
-- The same rule is run with different lower bounds and scored each time.
-- Techniques: LATERAL join to a set-returning function over a list of
--             parameter values, EXISTS, conditional aggregation.
-- =====================================================================
CREATE VIEW analytics.aml_structuring_rule_tuning AS
WITH settings (min_amount) AS (
    VALUES (9000), (8000), (7000), (6500), (6000), (5000)
),
alerts AS (
    SELECT s.min_amount, e.account_id, e.first_txn_ts, e.last_txn_ts,
           EXISTS (SELECT 1 FROM marts.aml_case_labels AS l
                   WHERE l.typology = 'structuring'
                     AND l.account_id = e.account_id
                     AND l.first_txn_ts <= e.last_txn_ts
                     AND l.last_txn_ts  >= e.first_txn_ts) AS is_true_positive
    FROM settings AS s
    CROSS JOIN LATERAL analytics.structuring_episodes(s.min_amount, 3) AS e
),
detected AS (
    SELECT s.min_amount, COUNT(*) AS cases_detected
    FROM settings AS s
    JOIN marts.aml_case_labels AS l ON l.typology = 'structuring'
    WHERE EXISTS (SELECT 1 FROM alerts AS a
                  WHERE a.min_amount = s.min_amount
                    AND a.account_id = l.account_id
                    AND l.first_txn_ts <= a.last_txn_ts
                    AND l.last_txn_ts  >= a.first_txn_ts)
    GROUP BY s.min_amount
)
SELECT a.min_amount                                             AS deposits_from_eur,
       COUNT(*)                                                 AS alerts,
       COUNT(*) FILTER (WHERE NOT a.is_true_positive)           AS false_alarms,
       ROUND(100.0 * COUNT(*) FILTER (WHERE a.is_true_positive) / COUNT(*), 1) AS precision_pct,
       ROUND(100.0 * d.cases_detected
             / (SELECT COUNT(*) FROM marts.aml_case_labels WHERE typology = 'structuring'), 1)
                                                                AS recall_pct
FROM alerts AS a
JOIN detected AS d USING (min_amount)
GROUP BY a.min_amount, d.cases_detected
ORDER BY a.min_amount DESC;
