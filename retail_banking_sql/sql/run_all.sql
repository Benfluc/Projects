-- =====================================================================
-- Builds the whole project from the CSV files, in order.
-- Run from the project root:
--     psql -d retail_bank -f sql/run_all.sql
-- =====================================================================
\set ON_ERROR_STOP on
\set QUIET on
SET client_min_messages = warning;

\echo '[1/7] Schema and raw load'
\i sql/01_schema/01_raw_tables.sql
\i sql/01_schema/02_load_raw.sql
\i sql/01_schema/03_marts_ddl.sql

\echo '[2/7] Staging and star schema'
\i sql/02_staging/01_staging.sql
\i sql/02_staging/02_load_marts.sql

\echo '[3/7] Data quality'
\i sql/03_data_quality/01_load_reconciliation.sql
\i sql/03_data_quality/02_tests.sql

\echo '[4/7] Customer analytics'
\i sql/04_customer_analytics/01_cohort_retention.sql
\i sql/04_customer_analytics/02_rfm_segmentation.sql
\i sql/04_customer_analytics/03_inactivity_and_churn.sql
\i sql/04_customer_analytics/04_cross_sell.sql

\echo '[5/7] Credit portfolio'
\i sql/05_credit_portfolio/01_loan_snapshots.sql
\i sql/05_credit_portfolio/02_vintage_analysis.sql
\i sql/05_credit_portfolio/03_roll_rates.sql
\i sql/05_credit_portfolio/04_portfolio_quality.sql

\echo '[6/7] AML detection'
\i sql/06_aml_detection/01_structuring.sql
\i sql/06_aml_detection/02_velocity.sql
\i sql/06_aml_detection/03_circular_flows.sql
\i sql/06_aml_detection/04_detection_scorecard.sql
\i sql/06_aml_detection/05_rule_tuning.sql

\echo '[7/7] Headline results'
\i sql/08_headline_results.sql

\echo
\echo 'Done. Performance experiments: psql -d retail_bank -f sql/07_performance/01_query_tuning.sql'
