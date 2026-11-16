-- =====================================================================
-- PERFORMANCE 2 | KEEPING THE MATERIALIZED VIEWS FRESH
-- Run after each new load of transactions or repayments.
-- CONCURRENTLY rebuilds the view without blocking the dashboards that
-- read it; it requires a unique index, which both views have.
-- =====================================================================
REFRESH MATERIALIZED VIEW CONCURRENTLY marts.customer_monthly_activity;
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.loan_monthly_snapshot;
-- The alert queue has no natural unique key, so it is rebuilt in place.
REFRESH MATERIALIZED VIEW analytics.aml_alerts;
ANALYZE marts.customer_monthly_activity;
ANALYZE analytics.loan_monthly_snapshot;
