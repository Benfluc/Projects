-- =====================================================================
-- CREDIT 2 | VINTAGE ANALYSIS
-- Business question: are the loans granted in some years going bad
-- faster than others?
-- For each origination year: the share of loans that had reached 90+
-- days past due by 6, 12, 18 and 24 months on book. Loans too young to
-- have reached a checkpoint are excluded from it, so young vintages are
-- not flattered.
-- Techniques: MIN ... FILTER for "first time", generate_series as a
--             checkpoint grid, censoring logic, pivot with FILTER.
-- =====================================================================
CREATE VIEW analytics.vintage_default_curve AS
WITH first_default AS (
    SELECT loan_id,
           MIN(months_on_book) FILTER (
               WHERE bucket IN ('90+ days', 'Charged off')) AS first_90dpd_month
    FROM analytics.loan_monthly_snapshot
    GROUP BY loan_id
),
checkpoints AS (
    SELECT generate_series(3, 36, 3) AS months_on_book
)
SELECT EXTRACT(YEAR FROM l.origination_date)::integer AS vintage,
       c.months_on_book,
       COUNT(*)                                        AS loans_observed,
       COUNT(*) FILTER (WHERE d.first_90dpd_month <= c.months_on_book) AS loans_defaulted,
       ROUND(100.0 * COUNT(*) FILTER (WHERE d.first_90dpd_month <= c.months_on_book)
             / COUNT(*), 2)                            AS cumulative_default_pct
FROM marts.fact_loans AS l
JOIN first_default AS d USING (loan_id)
CROSS JOIN checkpoints AS c
-- only loans old enough to have been observed at this checkpoint
WHERE marts.months_between(marts.as_of(), l.origination_date) >= c.months_on_book
GROUP BY EXTRACT(YEAR FROM l.origination_date), c.months_on_book;

CREATE VIEW analytics.vintage_default_matrix AS
SELECT vintage,
       MAX(loans_observed)         FILTER (WHERE months_on_book = 6)  AS loans,
       MAX(cumulative_default_pct) FILTER (WHERE months_on_book = 6)  AS by_month_6,
       MAX(cumulative_default_pct) FILTER (WHERE months_on_book = 12) AS by_month_12,
       MAX(cumulative_default_pct) FILTER (WHERE months_on_book = 18) AS by_month_18,
       MAX(cumulative_default_pct) FILTER (WHERE months_on_book = 24) AS by_month_24
FROM analytics.vintage_default_curve
GROUP BY vintage
ORDER BY vintage;
