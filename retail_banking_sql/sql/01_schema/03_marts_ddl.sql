-- =====================================================================
-- 03 | MARTS LAYER: STAR SCHEMA
-- Dimensions and facts with primary keys, foreign keys and CHECK
-- constraints. The transaction fact is range-partitioned by month.
-- =====================================================================
CREATE SCHEMA staging;
CREATE SCHEMA marts;
CREATE SCHEMA dq;
CREATE SCHEMA analytics;

-- Every analysis is run "as of" this date (the last day of the data).
CREATE FUNCTION marts.as_of() RETURNS date
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT DATE '2025-12-31' $$;

-- Whole calendar months between two dates (2025-03-xx minus 2025-01-xx = 2).
CREATE FUNCTION marts.months_between(later date, earlier date) RETURNS integer
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$
    SELECT ((EXTRACT(YEAR FROM later) - EXTRACT(YEAR FROM earlier)) * 12
          + (EXTRACT(MONTH FROM later) - EXTRACT(MONTH FROM earlier)))::integer
$$;

CREATE TABLE marts.dim_date (
    date_key      date PRIMARY KEY,
    year          smallint NOT NULL,
    quarter       smallint NOT NULL,
    month         smallint NOT NULL,
    month_start   date NOT NULL,
    month_name    text NOT NULL,
    day_of_week   smallint NOT NULL,          -- 1 = Monday ... 7 = Sunday
    is_weekend    boolean NOT NULL,
    is_month_end  boolean NOT NULL
);

CREATE TABLE marts.dim_branch (
    branch_id    integer PRIMARY KEY,
    branch_name  text NOT NULL,
    town         text NOT NULL,
    county       text NOT NULL
);

CREATE TABLE marts.dim_product (
    product_id      integer PRIMARY KEY,
    product_name    text NOT NULL UNIQUE,
    product_family  text NOT NULL
);

CREATE TABLE marts.dim_customer (
    customer_id    integer PRIMARY KEY,
    customer_type  text NOT NULL CHECK (customer_type IN ('personal', 'business')),
    segment        text NOT NULL CHECK (segment IN ('mass', 'affluent', 'private', 'sme')),
    birth_date     date,
    age_band       text NOT NULL,
    join_date      date NOT NULL,
    branch_id      integer NOT NULL REFERENCES marts.dim_branch,
    county         text NOT NULL,
    risk_rating    char(1) NOT NULL CHECK (risk_rating IN ('A', 'B', 'C', 'D', 'E')),
    closed_date    date,
    is_closed      boolean NOT NULL,
    CHECK (closed_date IS NULL OR closed_date >= join_date)
);

CREATE TABLE marts.dim_account (
    account_id    integer PRIMARY KEY,
    customer_id   integer NOT NULL REFERENCES marts.dim_customer,
    account_type  text NOT NULL CHECK (account_type IN ('current', 'savings')),
    open_date     date NOT NULL,
    close_date    date,
    status        text NOT NULL CHECK (status IN ('open', 'closed'))
);

CREATE TABLE marts.fact_product_holdings (
    holding_id   integer PRIMARY KEY,
    customer_id  integer NOT NULL REFERENCES marts.dim_customer,
    product_id   integer NOT NULL REFERENCES marts.dim_product,
    open_date    date NOT NULL,
    close_date   date
);

CREATE TABLE marts.fact_transactions (
    txn_id                   bigint NOT NULL,
    account_id               integer NOT NULL REFERENCES marts.dim_account,
    customer_id              integer NOT NULL REFERENCES marts.dim_customer,
    txn_ts                   timestamp NOT NULL,
    txn_date                 date NOT NULL REFERENCES marts.dim_date,
    amount                   numeric(14, 2) NOT NULL CHECK (amount > 0),
    direction                char(1) NOT NULL CHECK (direction IN ('C', 'D')),
    signed_amount            numeric(14, 2) NOT NULL,     -- credits positive, debits negative
    channel                  text NOT NULL,
    counterparty_account_id  integer,
    merchant_category        text,
    PRIMARY KEY (txn_id, txn_ts)                          -- must include the partition key
) PARTITION BY RANGE (txn_ts);

-- One partition per month of data, created dynamically.
DO $$
DECLARE
    month_start date;
BEGIN
    FOR month_start IN
        SELECT generate_series(TIMESTAMP '2024-01-01', TIMESTAMP '2025-12-01', INTERVAL '1 month')::date
    LOOP
        EXECUTE format(
            'CREATE TABLE marts.fact_transactions_%s PARTITION OF marts.fact_transactions
                 FOR VALUES FROM (%L) TO (%L)',
            to_char(month_start, 'YYYY_MM'),
            month_start,
            (month_start + INTERVAL '1 month')::date);
    END LOOP;
END $$;

CREATE TABLE marts.fact_loans (
    loan_id           integer PRIMARY KEY,
    customer_id       integer NOT NULL REFERENCES marts.dim_customer,
    product_id        integer NOT NULL REFERENCES marts.dim_product,
    origination_date  date NOT NULL,
    principal         numeric(14, 2) NOT NULL CHECK (principal > 0),
    annual_rate_pct   numeric(5, 2) NOT NULL,
    term_months       smallint NOT NULL,
    instalment        numeric(14, 2) NOT NULL,
    status            text NOT NULL CHECK (status IN ('active', 'paid_off', 'charged_off')),
    end_date          date
);

CREATE TABLE marts.fact_loan_payments (
    loan_id              integer NOT NULL REFERENCES marts.fact_loans,
    instalment_no        smallint NOT NULL,
    due_date             date NOT NULL,
    due_amount           numeric(14, 2) NOT NULL,
    principal_component  numeric(14, 2) NOT NULL,
    interest_component   numeric(14, 2) NOT NULL,
    paid_date            date,
    paid_amount          numeric(14, 2),
    PRIMARY KEY (loan_id, instalment_no)
);

-- Cases confirmed by (simulated) AML investigators; used only to score
-- the detection rules in module 06.
CREATE TABLE marts.aml_case_labels (
    case_id       integer PRIMARY KEY,
    typology      text NOT NULL,
    account_id    integer NOT NULL REFERENCES marts.dim_account,
    customer_id   integer NOT NULL REFERENCES marts.dim_customer,
    first_txn_ts  timestamp NOT NULL,
    last_txn_ts   timestamp NOT NULL
);
