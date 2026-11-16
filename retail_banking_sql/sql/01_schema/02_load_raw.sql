-- =====================================================================
-- 02 | LOAD THE CSV EXTRACTS
-- \copy runs on the client, so the paths are relative to the folder
-- psql is started from (the project root).
-- =====================================================================
\copy raw.branches          FROM 'data/raw/branches.csv'          WITH (FORMAT csv, HEADER true)
\copy raw.products          FROM 'data/raw/products.csv'          WITH (FORMAT csv, HEADER true)
\copy raw.customers         FROM 'data/raw/customers.csv'         WITH (FORMAT csv, HEADER true)
\copy raw.accounts          FROM 'data/raw/accounts.csv'          WITH (FORMAT csv, HEADER true)
\copy raw.customer_products FROM 'data/raw/customer_products.csv' WITH (FORMAT csv, HEADER true)
\copy raw.transactions      FROM 'data/raw/transactions.csv'      WITH (FORMAT csv, HEADER true)
\copy raw.loans             FROM 'data/raw/loans.csv'             WITH (FORMAT csv, HEADER true)
\copy raw.loan_payments     FROM 'data/raw/loan_payments.csv'     WITH (FORMAT csv, HEADER true)
\copy raw.aml_case_labels   FROM 'data/raw/aml_case_labels.csv'   WITH (FORMAT csv, HEADER true)
