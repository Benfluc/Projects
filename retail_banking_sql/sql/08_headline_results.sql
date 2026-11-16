-- =====================================================================
-- HEADLINE RESULTS
-- Prints the main output of every module. Each block is a plain SELECT
-- on a view, so the same views can feed Power BI or Tableau directly.
-- =====================================================================
\pset pager off
\echo
\echo '########## DATA QUALITY ##########'
\echo '--- Raw rows vs loaded rows'
SELECT * FROM dq.load_reconciliation;
\echo '--- Rejected transactions by reason'
SELECT * FROM dq.rejected_transactions_summary;
\echo '--- Automated tests (expected: 0 failing rows everywhere)'
SELECT * FROM dq.test_results;

\echo
\echo '########## CUSTOMERS ##########'
\echo '--- Retention of 2024 joiners (% still transacting N months after joining)'
SELECT * FROM analytics.cohort_retention_matrix;
\echo '--- RFM segments'
SELECT * FROM analytics.rfm_segment_summary;
\echo '--- Churn early-warning rule, back-tested as of 30 June 2025'
SELECT * FROM analytics.churn_rule_backtest;
\echo '--- Customers on the watchlist today, by segment'
SELECT segment, COUNT(*) AS customers, ROUND(AVG(days_silent)) AS avg_days_silent
FROM analytics.churn_watchlist_today GROUP BY segment ORDER BY customers DESC;
\echo '--- Strongest product affinities'
SELECT if_customer_holds, then_also_holds, customers_with_both, confidence_pct, lift
FROM analytics.product_affinity ORDER BY lift DESC, confidence_pct DESC LIMIT 6;
\echo '--- Next best product: campaign sizes'
SELECT * FROM analytics.next_best_product_summary;

\echo
\echo '########## CREDIT PORTFOLIO ##########'
\echo '--- Vintage analysis: cumulative % of loans reaching 90+ days past due'
SELECT * FROM analytics.vintage_default_matrix;
\echo '--- Roll rates: where loans in each bucket are one month later (%)'
SELECT * FROM analytics.roll_rate_matrix;
\echo '--- Loan book, last 6 month-ends'
SELECT * FROM analytics.portfolio_monthly_trend ORDER BY snapshot_date DESC LIMIT 6;
\echo '--- Loan book today by product and risk rating'
SELECT product, risk_rating, live_loans, outstanding_eur_m, in_arrears_pct, npl_ratio_pct
FROM analytics.portfolio_by_product_and_rating;

\echo
\echo '########## AML DETECTION ##########'
\echo '--- Detection scorecard against investigator-confirmed cases'
SELECT * FROM analytics.aml_detection_scorecard;
\echo '--- Tuning the structuring rule: lower bound of the deposit band'
SELECT * FROM analytics.aml_structuring_rule_tuning;
\echo '--- Largest circular flows'
SELECT origin_account, path, hops, amount_sent, amount_returned, duration
FROM analytics.aml_circular_flow_alerts ORDER BY amount_sent DESC LIMIT 5;
