-- =====================================================================
-- DATA QUALITY 2 | AUTOMATED TESTS ON THE MARTS
-- Each test counts the rows that break a rule; the expected result is 0.
-- The DO block at the end stops the pipeline if any test fails, in the
-- same spirit as dbt tests.
-- =====================================================================
CREATE VIEW dq.test_results AS
SELECT 'load reconciles: raw = loaded + rejected' AS test_name,
       (SELECT COUNT(*) FROM dq.load_reconciliation
        WHERE raw_rows <> loaded_rows + rejected_rows) AS failing_rows
UNION ALL
SELECT 'transaction ids are unique',
       (SELECT COUNT(*) FROM (
            SELECT txn_id FROM marts.fact_transactions GROUP BY txn_id HAVING COUNT(*) > 1) AS d)
UNION ALL
SELECT 'transactions fall inside the account lifetime',
       (SELECT COUNT(*)
        FROM marts.fact_transactions AS t
        JOIN marts.dim_account AS a USING (account_id)
        WHERE t.txn_date < a.open_date
           OR t.txn_date > COALESCE(a.close_date, marts.as_of()))
UNION ALL
SELECT 'transaction customer matches the account owner',
       (SELECT COUNT(*)
        FROM marts.fact_transactions AS t
        JOIN marts.dim_account AS a USING (account_id)
        WHERE t.customer_id <> a.customer_id)
UNION ALL
SELECT 'internal counterparties are known accounts',
       (SELECT COUNT(*)
        FROM marts.fact_transactions AS t
        WHERE t.counterparty_account_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM marts.dim_account AS a
                          WHERE a.account_id = t.counterparty_account_id))
UNION ALL
SELECT 'every customer has a current account',
       (SELECT COUNT(*)
        FROM marts.dim_customer AS c
        WHERE NOT EXISTS (SELECT 1 FROM marts.dim_account AS a
                          WHERE a.customer_id = c.customer_id AND a.account_type = 'current'))
UNION ALL
SELECT 'closed customers have no open accounts',
       (SELECT COUNT(*)
        FROM marts.dim_customer AS c
        JOIN marts.dim_account AS a USING (customer_id)
        WHERE c.is_closed AND a.status = 'open')
UNION ALL
SELECT 'holdings close on or after they open',
       (SELECT COUNT(*) FROM marts.fact_product_holdings WHERE close_date < open_date)
UNION ALL
SELECT 'instalment numbers are contiguous per loan',
       (SELECT COUNT(*) FROM (
            SELECT loan_id FROM marts.fact_loan_payments
            GROUP BY loan_id HAVING MAX(instalment_no) <> COUNT(*)) AS d)
UNION ALL
SELECT 'instalment = principal + interest',
       (SELECT COUNT(*) FROM marts.fact_loan_payments
        WHERE due_amount <> principal_component + interest_component)
UNION ALL
SELECT 'paid instalments are paid in full',
       (SELECT COUNT(*) FROM marts.fact_loan_payments
        WHERE (paid_date IS NULL) <> (paid_amount IS NULL)
           OR paid_amount <> due_amount)
UNION ALL
SELECT 'paid-off loans repaid exactly the principal',
       (SELECT COUNT(*)
        FROM marts.fact_loans AS l
        JOIN (SELECT loan_id, SUM(principal_component) AS repaid
              FROM marts.fact_loan_payments WHERE paid_date IS NOT NULL
              GROUP BY loan_id) AS p USING (loan_id)
        WHERE l.status = 'paid_off' AND ABS(p.repaid - l.principal) > 0.01)
UNION ALL
SELECT 'monthly activity view matches the transaction fact',
       (SELECT ABS((SELECT SUM(txn_count) FROM marts.customer_monthly_activity)
                 - (SELECT COUNT(*) FROM marts.fact_transactions)))::bigint;

DO $$
DECLARE
    failed integer;
BEGIN
    SELECT COUNT(*) INTO failed FROM dq.test_results WHERE failing_rows <> 0;
    IF failed > 0 THEN
        RAISE EXCEPTION '% data-quality test(s) failed. Run: SELECT * FROM dq.test_results;', failed;
    END IF;
    RAISE NOTICE 'All data-quality tests passed.';
END $$;
