# Findings

Results of a full run with the default settings (`--scale 1.0`, seed 42), as of **31 December 2025**, the last day of
the data. The complete output is in [sample_output.txt](sample_output.txt).

All data is synthetic. The numbers show what the SQL recovers from the generated data, not facts about a real bank.

| Dataset | Rows |
|---|---|
| Customers | 20,000 |
| Accounts | 28,121 |
| Transactions (24 monthly partitions) | 1,419,196 |
| Loans | 5,886 |
| Loan instalments | 109,553 |
| Month-end loan snapshots (derived) | 116,225 |

## 1. Data quality

The raw extracts were loaded as text and cleaned in staging. Nothing was dropped silently:

| Dataset | Raw rows | Loaded | Rejected | Why |
|---|---|---|---|---|
| Transactions | 1,421,323 | 1,419,196 | 2,127 | 1,419 duplicates, 354 unknown accounts, 236 negative amounts, 118 missing timestamps |
| Customers | 20,153 | 20,000 | 153 | exact duplicate rows |
| Loan instalments | 109,589 | 109,553 | 36 | exact duplicate rows |

Raw rows equal loaded plus rejected rows for every dataset. County names arrived in up to four spellings each
(`Dublin`, `DUBLIN`, `dublin`, padded with spaces) and were standardised. All 13 automated tests pass; the pipeline
raises an error and stops if any of them fails.

## 2. Customers

### Retention of new customers

"Retained" means at least one transaction in the month. For customers who joined in 2024, between 82% and 89% are
active one month after joining and between 73% and 84% twelve months after. Retention falls slowly rather than in a
cliff, so there is no single onboarding month where customers are lost.

### RFM segmentation (open customers, last 12 months)

| Segment | Customers | % of customers | % of spend |
|---|---|---|---|
| Champions | 3,573 | 20.1 | 49.3 |
| Loyal | 4,493 | 25.3 | 24.8 |
| At risk (high value) | 1,803 | 10.1 | 13.2 |
| Hibernating | 5,309 | 29.9 | 7.6 |
| Recent, low engagement | 1,485 | 8.4 | 2.9 |
| Needs attention | 1,114 | 6.3 | 2.2 |

One fifth of the customers generate half of the outgoing volume. The "At risk (high value)" group is the priority for
retention: 1,803 customers with high historical volume whose last transaction is, on average, 23 days old.

### Churn early warning

Rule: flag a customer when their activity in the last 90 days is at least 60% below their own average for the two
previous 90-day periods. The rule was applied as of 30 June 2025 and checked against what happened next.

| Group on 30 June 2025 | Customers | Left by 31 December | Closure rate | Share of all leavers |
|---|---|---|---|---|
| Flagged by the rule | 1,126 | 165 | 14.7% | 34.2% |
| Not flagged | 14,940 | 317 | 2.1% | 65.8% |

Flagged customers were 4.9 times more likely to leave than the average customer (3.0%). The rule is cheap and
selective, but it still misses two thirds of the leavers, most of whom reduce their activity only in the final weeks.
Applied today, it lists 848 customers, of whom 190 are affluent or private-banking clients.

### Cross-sell

| If the customer holds | They also hold | Confidence | Lift |
|---|---|---|---|
| Investment Fund | Pension Plan | 52.4% | 5.58 |
| Pension Plan | Investment Fund | 47.5% | 5.58 |
| Mortgage | Home Insurance | 61.0% | 4.84 |
| Home Insurance | Mortgage | 21.7% | 4.84 |

No other pair has a lift above 1.3. Using these four rules, 3,244 customers receive one specific recommendation: for
example, 292 mortgage holders without home insurance, and 893 pension holders without an investment fund.

## 3. Credit portfolio

### Vintage analysis

Cumulative share of loans that reached 90+ days past due, by months since origination:

| Granted in | Loans | By month 6 | By month 12 | By month 18 | By month 24 |
|---|---|---|---|---|---|
| 2021 | 533 | 0.75% | 3.00% | 5.63% | 7.32% |
| 2022 | 813 | 0.98% | 3.94% | 6.64% | 8.61% |
| 2023 | 1,074 | 1.21% | 4.66% | 8.19% | 11.73% |
| 2024 | 1,578 | 0.76% | 2.79% | 5.60% | not yet observable |
| 2025 | 1,094 | 1.01% | not yet observable | | |

The 2023 vintage is worse than its predecessors at every checkpoint and ends 24 months at 11.7%. The 2024 vintage is
back in line with 2021 at 18 months. Loans too young to have reached a checkpoint are excluded from it.

### Roll rates

Where a loan in each bucket is one month later:

| From | To current | Stays or worsens | Notes |
|---|---|---|---|
| Current | 96.1% | 2.8% to 1-30 days | 1.1% paid off |
| 1-30 days | 54.7% | 24.8% to 31-60 days | more than half recover |
| 31-60 days | 21.8% | 48.4% to 61-90 days | |
| 61-90 days | 12.9% | 57.3% to 90+ days | the last realistic point to intervene |
| 90+ days | 2.6% | 81.7% stay, 15.1% charged off | recovery is rare |

The chance of recovery falls from 55% to 13% between the first and the third month of arrears, which is the argument
for contacting customers in the first 30 days.

### The book today

The live book is EUR 249.7 million across 4,423 loans, with 0.75% of the balance 90+ days past due and 3.39% in any
arrears. Mortgages are 85% of the balance and the healthiest product (0.60% non-performing). Personal loans are 9% of
the balance with 2.15% non-performing, and their arrears rise steadily with the risk rating, from 1.3% for rating A to
22.7% for rating E.

## 4. AML detection

Three rules, scored against the 228 account-level cases confirmed by the simulated investigators:

| Typology | Confirmed cases | Alerts | False alarms | Missed | Precision | Recall |
|---|---|---|---|---|---|---|
| Structuring | 84 | 79 | 8 | 13 | 89.9% | 84.5% |
| Velocity | 50 | 42 | 0 | 8 | 100.0% | 84.0% |
| Circular flows | 94 | 80 | 0 | 14 | 100.0% | 85.1% |

- **Structuring** alerts cover EUR 3.7 million of cash deposits. The 8 false alarms are cash-heavy businesses that
  banked three large takings in a week. The 13 missed cases kept every deposit between EUR 6,500 and EUR 7,900.
- **Velocity** misses the slower bursts, spread over up to three hours, which never reach ten payments in any single hour.
- **Circular flows**: the recursive query found 21 of the 25 rings (three to five accounts each). The four it missed
  let the money rest for four to six days before one hop, beyond the three-day limit.

### Tuning the structuring rule

| Deposits from | Alerts | False alarms | Precision | Recall |
|---|---|---|---|---|
| EUR 9,000 | 30 | 0 | 100.0% | 35.7% |
| EUR 8,000 (current) | 79 | 8 | 89.9% | 84.5% |
| EUR 7,000 | 92 | 12 | 87.0% | 95.2% |
| EUR 6,500 | 113 | 29 | 74.3% | 100.0% |
| EUR 6,000 | 212 | 128 | 39.6% | 100.0% |
| EUR 5,000 | 734 | 650 | 11.4% | 100.0% |

Moving the lower bound to EUR 7,000 is the best trade: recall rises from 84.5% to 95.2% for 13 extra alerts, only 4 of
them false. Below EUR 6,500 the rule starts flagging ordinary shops and pubs banking their takings, and at EUR 5,000
nine alerts in ten are false.

## 5. Performance

Measured with `EXPLAIN ANALYZE` on PostgreSQL 16 (2 CPU cores, warm cache). Timings vary between runs and machines.

| Experiment | Without | With | What changed in the plan |
|---|---|---|---|
| Composite index `(account_id, txn_ts)`: six months of one account | about 30 ms | about 0.1 ms | Parallel sequential scan of six partitions (4,482 pages) becomes six index scans |
| Partition pruning: one month of totals by channel | about 70 ms | about 12 ms | 24 partitions scanned (16,932 pages) becomes one (747 pages) |
| Materialized view: active customers per month | about 750 ms | about 33 ms | Sort and distinct over 1.4 million rows becomes a scan of the pre-aggregated view |

The full build, from empty database to results, takes about 40 seconds.
