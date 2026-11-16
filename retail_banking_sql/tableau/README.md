# Tableau data

Results of the SQL analyses, exported by [sql/09_export_for_tableau.sql](../sql/09_export_for_tableau.sql) for use in
Tableau Public. All files are tidy: one row per observation, no pivoted columns. All data is synthetic.

| File | One row per | Used for |
|---|---|---|
| `kpis.csv` | headline metric | KPI tiles |
| `monthly_transactions.csv` | month, channel and direction | transaction volume over time |
| `cohort_retention.csv` | joining cohort and month since joining | retention heatmap |
| `rfm_customers.csv` | customer | RFM segments, filters by segment, county, age band |
| `churn_backtest.csv` | flagged / not flagged group | back-test of the churn rule |
| `product_affinity.csv` | ordered pair of products | cross-sell heatmap (lift, confidence) |
| `next_best_product.csv` | recommendation rule | campaign sizes |
| `vintage_default_curve.csv` | origination year and months on book | vintage curves |
| `roll_rates.csv` | from-bucket and to-bucket | roll-rate matrix (`from_sort` and `to_sort` give the display order) |
| `portfolio_trend.csv` | month-end | loan book and non-performing ratio over time |
| `portfolio_by_product_rating.csv` | product, risk rating and delinquency bucket | arrears by product and rating |
| `aml_scorecard.csv` | typology | precision and recall of each rule |
| `aml_rule_tuning.csv` | threshold setting | precision/recall trade-off of the structuring rule |
| `aml_alerts.csv` | alert | alert queue with outcome (confirmed case or false alarm) |
