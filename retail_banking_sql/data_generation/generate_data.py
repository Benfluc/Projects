"""
Synthetic data generator for the "Retail Banking Analytics in SQL" project.

Creates the raw CSV extracts of a fictional Irish retail bank ("Liffey Bank"):
branches, customers, accounts, products, product holdings, transactions,
loans, loan repayment schedules and a file of investigator-confirmed AML cases.

Everything is simulated. No real customer or bank data is used.

The generator deliberately plants:
  * behaviour that the SQL analyses must find (churn run-off, dormant customers,
    product affinities, a weak 2023 loan vintage, three money-laundering
    typologies), and
  * data-quality problems that the staging layer must fix (duplicates, orphan
    rows, inconsistent text, sign errors, missing timestamps).

Usage:
    python data_generation/generate_data.py                # 20,000 customers
    python data_generation/generate_data.py --scale 0.25   # smaller, faster
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

OBS_START = np.datetime64("2024-01-01")   # first day with transactions
OBS_END = np.datetime64("2025-12-31")     # "today" for every analysis
FIRST_JOIN = np.datetime64("2018-01-01")
LAST_JOIN = np.datetime64("2025-10-31")
FIRST_LOAN = np.datetime64("2021-01-01")
LAST_LOAN = np.datetime64("2025-09-30")

BRANCHES = [
    # (branch_name, town, county, weight)
    ("College Green", "Dublin", "Dublin", 10),
    ("Rathmines", "Dublin", "Dublin", 7),
    ("Swords", "Swords", "Dublin", 6),
    ("Dun Laoghaire", "Dun Laoghaire", "Dublin", 6),
    ("Tallaght", "Tallaght", "Dublin", 6),
    ("Patrick Street", "Cork", "Cork", 8),
    ("Ballincollig", "Ballincollig", "Cork", 4),
    ("Eyre Square", "Galway", "Galway", 6),
    ("O'Connell Street", "Limerick", "Limerick", 5),
    ("The Quay", "Waterford", "Waterford", 4),
    ("High Street", "Kilkenny", "Kilkenny", 3),
    ("Stephen Street", "Sligo", "Sligo", 3),
    ("Church Street", "Athlone", "Westmeath", 3),
    ("Clanbrassil Street", "Dundalk", "Louth", 3),
    ("West Street", "Drogheda", "Louth", 3),
    ("The Mall", "Tralee", "Kerry", 3),
    ("Main Street", "Letterkenny", "Donegal", 3),
    ("North Main Street", "Wexford", "Wexford", 3),
    ("Abbey Street", "Ennis", "Clare", 3),
    ("Poplar Square", "Naas", "Kildare", 4),
]

PRODUCTS = [
    # (product_id, product_name, product_family)
    (1, "Current Account", "Daily banking"),
    (2, "Savings Account", "Savings"),
    (3, "Credit Card", "Lending"),
    (4, "Personal Loan", "Lending"),
    (5, "Mortgage", "Lending"),
    (6, "Business Loan", "Lending"),
    (7, "Home Insurance", "Insurance"),
    (8, "Pension Plan", "Investments"),
    (9, "Investment Fund", "Investments"),
]

MERCHANT_CATEGORIES = ["groceries", "fuel", "restaurants", "retail", "travel",
                       "utilities", "entertainment", "health"]

# Hour-of-day weights: most activity between 08:00 and 21:00.
HOUR_WEIGHTS = np.array([1, 1, 1, 1, 1, 2, 4, 7, 10, 11, 12, 12, 13, 12, 11,
                         11, 11, 12, 12, 10, 8, 5, 3, 2], dtype=float)
HOUR_WEIGHTS /= HOUR_WEIGHTS.sum()


def to_days(values) -> np.ndarray:
    return np.asarray(values, dtype="datetime64[D]")


def random_dates(rng, start, end, size) -> np.ndarray:
    span = int((end - start) / np.timedelta64(1, "D"))
    return start + rng.integers(0, span + 1, size).astype("timedelta64[D]")


def add_months(date: np.datetime64, months: int) -> np.datetime64:
    """Add calendar months, capping the day at 28 so every month is valid."""
    ts = pd.Timestamp(date)
    total = ts.year * 12 + (ts.month - 1) + months
    return np.datetime64(f"{total // 12:04d}-{total % 12 + 1:02d}-{min(ts.day, 28):02d}")


# --------------------------------------------------------------------------
# Customers and accounts
# --------------------------------------------------------------------------
def build_customers(rng, n: int) -> pd.DataFrame:
    is_business = rng.random(n) < 0.12
    segment = np.where(
        is_business, "sme",
        rng.choice(["mass", "affluent", "private"], n, p=[0.70, 0.24, 0.06]))
    join_date = random_dates(rng, FIRST_JOIN, LAST_JOIN, n)
    age_days = (rng.integers(18, 86, n) * 365.25).astype(int)
    birth_date = join_date - age_days.astype("timedelta64[D]")

    weights = np.array([b[3] for b in BRANCHES], dtype=float)
    branch_id = rng.choice(np.arange(1, len(BRANCHES) + 1), n, p=weights / weights.sum())
    risk_rating = rng.choice(list("ABCDE"), n, p=[0.25, 0.30, 0.25, 0.13, 0.07])

    # Roughly 10% of customers leave the bank during the observation window.
    earliest_close = np.maximum(join_date + np.timedelta64(180, "D"), np.datetime64("2024-04-01"))
    latest_close = np.datetime64("2025-12-15")
    can_close = earliest_close < latest_close
    closes = (rng.random(n) < 0.10) & can_close
    span = np.maximum((latest_close - earliest_close) / np.timedelta64(1, "D"), 1).astype(int)
    closed_date = earliest_close + (rng.random(n) * span).astype(int).astype("timedelta64[D]")
    closed_date = np.where(closes, closed_date, np.datetime64("NaT", "D"))

    # Another 4% simply stop using the bank without closing anything.
    earliest_dormant = np.maximum(join_date + np.timedelta64(120, "D"), np.datetime64("2024-06-01"))
    latest_dormant = np.datetime64("2025-09-30")
    can_go_dormant = (earliest_dormant < latest_dormant) & ~closes
    goes_dormant = (rng.random(n) < 0.04) & can_go_dormant
    span = np.maximum((latest_dormant - earliest_dormant) / np.timedelta64(1, "D"), 1).astype(int)
    dormant_from = earliest_dormant + (rng.random(n) * span).astype(int).astype("timedelta64[D]")
    dormant_from = np.where(goes_dormant, dormant_from, np.datetime64("NaT", "D"))

    return pd.DataFrame({
        "customer_id": np.arange(1, n + 1),
        "customer_type": np.where(is_business, "business", "personal"),
        "segment": segment,
        "birth_date": np.where(is_business, np.datetime64("NaT", "D"), birth_date),
        "join_date": join_date,
        "branch_id": branch_id,
        "risk_rating": risk_rating,
        "closed_date": closed_date,
        "_dormant_from": dormant_from,
    })


def build_accounts(rng, customers: pd.DataFrame) -> pd.DataFrame:
    n = len(customers)
    current = pd.DataFrame({
        "customer_id": customers["customer_id"].to_numpy(),
        "account_type": "current",
        "open_date": customers["join_date"].to_numpy(),
    })
    has_savings = rng.random(n) < 0.45
    savings_open = customers["join_date"].to_numpy() + rng.integers(0, 721, n).astype("timedelta64[D]")
    has_savings &= savings_open <= OBS_END
    closed = customers["closed_date"].to_numpy()
    has_savings &= np.isnat(closed) | (savings_open < closed)
    savings = pd.DataFrame({
        "customer_id": customers["customer_id"].to_numpy()[has_savings],
        "account_type": "savings",
        "open_date": savings_open[has_savings],
    })
    accounts = pd.concat([current, savings], ignore_index=True)
    accounts = accounts.merge(
        customers[["customer_id", "closed_date"]].rename(columns={"closed_date": "close_date"}),
        on="customer_id", how="left")
    accounts = accounts.sort_values(["open_date", "customer_id"]).reset_index(drop=True)
    accounts.insert(0, "account_id", np.arange(100001, 100001 + len(accounts)))
    accounts["status"] = np.where(accounts["close_date"].isna(), "open", "closed")
    return accounts


# --------------------------------------------------------------------------
# Everyday transactions
# --------------------------------------------------------------------------
def build_transactions(rng, customers: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    acc = accounts.merge(
        customers[["customer_id", "customer_type", "segment", "_dormant_from"]], on="customer_id")
    n_acc = len(acc)
    is_current = (acc["account_type"] == "current").to_numpy()
    is_business = (acc["customer_type"] == "business").to_numpy()
    open_date = to_days(acc["open_date"])
    close_date = to_days(acc["close_date"])
    dormant_from = to_days(acc["_dormant_from"])

    # Last day on which the account is used. Leavers go quiet 20-90 days
    # before the account is formally closed.
    quiet_days = rng.integers(20, 91, n_acc).astype("timedelta64[D]")
    last_activity = np.full(n_acc, OBS_END)
    leaving = ~np.isnat(close_date)
    last_activity[leaving] = close_date[leaving] - quiet_days[leaving]
    dormant = ~np.isnat(dormant_from)
    last_activity[dormant] = dormant_from[dormant]

    segment_factor = acc["segment"].map(
        {"mass": 1.0, "affluent": 1.3, "private": 1.5, "sme": 2.0}).to_numpy()
    monthly_rate = np.where(
        is_current, rng.gamma(2.0, 1.4, n_acc) * segment_factor, rng.gamma(2.0, 0.2, n_acc))

    month_starts = np.arange("2024-01", "2026-01", dtype="datetime64[M]")
    month_start_days = month_starts.astype("datetime64[D]")
    month_end_days = (month_starts + np.timedelta64(1, "M")).astype("datetime64[D]") - np.timedelta64(1, "D")
    month_lengths = ((month_end_days - month_start_days) / np.timedelta64(1, "D")).astype(int) + 1

    # Leavers and dormant customers wind their activity down over ~5 months.
    days_to_last = (last_activity[:, None] - month_start_days[None, :]) / np.timedelta64(1, "D")
    winding_down = (leaving | dormant)[:, None]
    decay = np.where(winding_down, np.clip(days_to_last / 150.0, 0.15, 1.0), 1.0)
    active = (month_end_days[None, :] >= open_date[:, None]) & (
        month_start_days[None, :] <= last_activity[:, None])
    counts = rng.poisson(monthly_rate[:, None] * decay) * active

    acc_idx, month_idx = np.nonzero(counts)
    repeats = counts[acc_idx, month_idx]
    acc_idx = np.repeat(acc_idx, repeats)
    month_idx = np.repeat(month_idx, repeats)
    n_txn = len(acc_idx)

    day_offset = (rng.random(n_txn) * month_lengths[month_idx]).astype(int)
    txn_day = month_start_days[month_idx] + day_offset.astype("timedelta64[D]")
    keep = (txn_day >= open_date[acc_idx]) & (txn_day <= last_activity[acc_idx])
    acc_idx, txn_day = acc_idx[keep], txn_day[keep]
    n_txn = len(acc_idx)

    seconds = (rng.choice(24, n_txn, p=HOUR_WEIGHTS) * 3600 + rng.integers(0, 3600, n_txn))
    txn_ts = txn_day.astype("datetime64[s]") + seconds.astype("timedelta64[s]")

    channels = np.array(["card", "direct_debit", "transfer_out", "transfer_in",
                         "salary", "cash_deposit", "cash_withdrawal"])
    p_personal = [0.56, 0.12, 0.09, 0.07, 0.05, 0.03, 0.08]
    p_business = [0.30, 0.12, 0.20, 0.22, 0.00, 0.12, 0.04]
    p_savings = [0.00, 0.00, 0.40, 0.60, 0.00, 0.00, 0.00]
    channel = np.empty(n_txn, dtype=object)
    txn_current, txn_business = is_current[acc_idx], is_business[acc_idx]
    for mask, probs in [(txn_current & ~txn_business, p_personal),
                        (txn_current & txn_business, p_business),
                        (~txn_current, p_savings)]:
        channel[mask] = rng.choice(channels, mask.sum(), p=probs)

    # Log-normal amounts: (mean of log, sigma of log) per channel.
    params = {"card": (3.3, 0.9), "direct_debit": (4.2, 0.7), "transfer_out": (5.3, 1.1),
              "transfer_in": (5.4, 1.1), "salary": (7.9, 0.35), "cash_deposit": (5.5, 0.9),
              "cash_withdrawal": (4.6, 0.7)}
    amount = np.zeros(n_txn)
    for name, (mu, sigma) in params.items():
        mask = channel == name
        amount[mask] = rng.lognormal(mu, sigma, mask.sum())
    amount[channel == "salary"] *= segment_factor[acc_idx][channel == "salary"]
    business_scaled = txn_business & np.isin(channel, ["transfer_out", "transfer_in", "cash_deposit"])
    amount[business_scaled] *= 3.0
    # Ordinary cash deposits stay well below the EUR 10,000 reporting threshold.
    cash = channel == "cash_deposit"
    amount[cash] = np.minimum(amount[cash], 7400 * rng.uniform(0.6, 1.0, cash.sum()))
    amount = np.maximum(np.round(amount, 2), 1.0)

    direction = np.where(np.isin(channel, ["transfer_in", "salary", "cash_deposit"]), "C", "D")
    merchant = np.where(channel == "card", rng.choice(MERCHANT_CATEGORIES, n_txn), None)

    # 30% of outgoing transfers go to another account held at the bank.
    account_ids = acc["account_id"].to_numpy()
    current_ids = account_ids[is_current]
    counterparty = np.full(n_txn, np.nan)
    internal = (channel == "transfer_out") & (rng.random(n_txn) < 0.30)
    counterparty[internal] = rng.choice(current_ids, internal.sum())
    same = internal & (counterparty == account_ids[acc_idx])
    counterparty[same] = np.nan

    return pd.DataFrame({
        "account_id": account_ids[acc_idx], "txn_ts": txn_ts, "amount": amount,
        "direction": direction, "channel": channel,
        "counterparty_account_id": counterparty, "merchant_category": merchant,
    })


# --------------------------------------------------------------------------
# Planted money-laundering typologies (with investigator labels)
# --------------------------------------------------------------------------
def random_ts(rng, start="2024-02-01", end="2025-11-30") -> np.datetime64:
    start, end = np.datetime64(start, "s"), np.datetime64(end, "s")
    span = int((end - start) / np.timedelta64(1, "s"))
    return start + np.timedelta64(int(rng.integers(0, span)), "s")


def txn_row(account_id, ts, amount, direction, channel, counterparty=np.nan, merchant=None):
    return {"account_id": account_id, "txn_ts": ts, "amount": round(float(amount), 2),
            "direction": direction, "channel": channel,
            "counterparty_account_id": counterparty, "merchant_category": merchant}


def plant_aml_patterns(rng, customers, accounts, scale):
    cust = customers.set_index("customer_id")
    current = accounts[accounts["account_type"] == "current"]
    stable_customers = cust.index[
        (cust["join_date"] < OBS_START) & cust["closed_date"].isna() & cust["_dormant_from"].isna()]
    stable = current[current["customer_id"].isin(stable_customers)]
    business = stable[stable["customer_id"].map(cust["customer_type"]) == "business"]

    n_structuring = max(4, int(60 * scale))
    n_velocity = max(4, int(50 * scale))
    n_rings = max(3, int(25 * scale))
    n_false_alarm = max(2, int(8 * scale))
    n_noise = max(10, int(150 * scale))

    pool = rng.permutation(stable["account_id"].to_numpy())
    owner = dict(zip(accounts["account_id"], accounts["customer_id"]))
    rows, labels = [], []
    cursor = 0

    def take(k):
        nonlocal cursor
        chosen = pool[cursor:cursor + k]
        cursor += k
        return [int(a) for a in chosen]

    # 1) Structuring ("smurfing"): several cash deposits just below EUR 10,000
    #    within a few days, so no single deposit triggers a report.
    for account_id in take(n_structuring):
        for _ in range(int(rng.integers(1, 3))):
            start = random_ts(rng)
            offsets = np.sort(rng.integers(0, 5 * 24 * 3600, int(rng.integers(4, 8))))
            stamps = [start + np.timedelta64(int(o), "s") for o in offsets]
            # Some launderers stay further below the threshold to avoid the
            # obvious "just under 10,000" band: harder for a rule to catch.
            low, high = (6500, 7900) if rng.random() < 0.15 else (8000, 9950)
            for ts in stamps:
                rows.append(txn_row(account_id, ts, rng.uniform(low, high), "C", "cash_deposit"))
            labels.append(("structuring", account_id, owner[account_id], stamps[0], stamps[-1]))

    # 2) Velocity: a burst of card payments in under an hour (account takeover
    #    or rapid cash-out through a merchant).
    for account_id in take(n_velocity):
        start = random_ts(rng)
        # Most bursts last under 45 minutes; a few are spread over three hours.
        if rng.random() < 0.15:
            offsets = np.sort(rng.integers(0, 3 * 3600, int(rng.integers(12, 17))))
        else:
            offsets = np.sort(rng.integers(0, 45 * 60, int(rng.integers(12, 26))))
        stamps = [start + np.timedelta64(int(o), "s") for o in offsets]
        for ts in stamps:
            rows.append(txn_row(account_id, ts, rng.uniform(20, 400), "D", "card",
                                merchant=str(rng.choice(["retail", "travel", "entertainment"]))))
        labels.append(("velocity", account_id, owner[account_id], stamps[0], stamps[-1]))

    # 3) Circular flows ("round-tripping"): money leaves an account, passes
    #    through 2-4 others and returns to the origin within days, slightly
    #    reduced at each hop.
    for _ in range(n_rings):
        ring = take(int(rng.integers(3, 6)))
        ts = random_ts(rng)
        amount = rng.uniform(8000, 45000)
        first_ts = ts
        # A patient ring lets the money rest for 4-6 days before one of the hops.
        slow_hop = int(rng.integers(0, len(ring) - 1)) if rng.random() < 0.15 else -1
        for i, source in enumerate(ring):
            target = ring[(i + 1) % len(ring)]
            rows.append(txn_row(source, ts, amount, "D", "transfer_out", counterparty=target))
            last_ts = ts
            wait_hours = rng.integers(96, 144) if i == slow_hop else rng.integers(2, 30)
            ts = ts + np.timedelta64(int(wait_hours) * 3600 + int(rng.integers(0, 3600)), "s")
            amount *= rng.uniform(0.97, 0.995)
        for account_id in ring:
            labels.append(("circular_flow", account_id, owner[account_id], first_ts, last_ts))

    # Legitimate look-alikes, NOT labelled: cash-heavy businesses that
    # occasionally bank large takings. They create realistic false positives.
    business_ids = business["account_id"].to_numpy()
    for account_id in rng.choice(business_ids, n_false_alarm, replace=False):
        start = random_ts(rng)
        for o in np.sort(rng.integers(0, 6 * 24 * 3600, 3)):
            rows.append(txn_row(int(account_id), start + np.timedelta64(int(o), "s"),
                                rng.uniform(8000, 9900), "C", "cash_deposit"))
    for account_id in rng.choice(business_ids, n_noise):
        rows.append(txn_row(int(account_id), random_ts(rng), rng.uniform(8000, 9900),
                            "C", "cash_deposit"))

    # Cash-heavy but legitimate businesses (shops, pubs, market traders) that
    # bank their takings every few days. Their deposits sit well below the
    # reporting threshold, but a rule with a wide amount band will flag them.
    for account_id in rng.choice(business_ids, max(3, int(40 * scale)), replace=False):
        ts = np.datetime64("2024-01-02T09:00:00") + np.timedelta64(int(rng.integers(0, 86400 * 3)), "s")
        while ts < np.datetime64("2025-12-30T00:00:00"):
            takings = float(np.clip(rng.normal(4800, 1300), 1500, 7900))
            rows.append(txn_row(int(account_id), ts, takings, "C", "cash_deposit"))
            ts = ts + np.timedelta64(int(rng.integers(2 * 86400, 4 * 86400)), "s")

    labels = pd.DataFrame(labels, columns=["typology", "account_id", "customer_id",
                                           "first_txn_ts", "last_txn_ts"])
    labels.insert(0, "case_id", np.arange(1, len(labels) + 1))
    return pd.DataFrame(rows), labels


# --------------------------------------------------------------------------
# Loans and repayment schedules
# --------------------------------------------------------------------------
def build_loans(rng, customers: pd.DataFrame, n_loans: int):
    eligible = customers[customers["join_date"] <= np.datetime64("2025-08-01")]
    picked = eligible.sample(n=n_loans, replace=True, random_state=int(rng.integers(0, 2**31)))
    loans, payments = [], []
    base_miss = {"A": 0.004, "B": 0.008, "C": 0.016, "D": 0.032, "E": 0.060}
    cure_prob = {1: 0.35, 2: 0.22, 3: 0.12}
    obs_end = pd.Timestamp(OBS_END)

    for loan_id, row in enumerate(picked.itertuples(index=False), start=500001):
        join = np.datetime64(row.join_date, "D")
        earliest = max(join + np.timedelta64(30, "D"), FIRST_LOAN)
        origination = random_dates(rng, earliest, LAST_LOAN, 1)[0]
        closed = row.closed_date
        if pd.notna(closed) and origination >= np.datetime64(closed, "D"):
            continue

        if row.customer_type == "business":
            product_id = 6
            principal = float(np.clip(rng.lognormal(10.5, 0.7), 5000, 250000))
            term = int(rng.choice([24, 36, 60, 84]))
            annual_rate = rng.uniform(5.0, 9.0)
        elif rng.random() < 0.18:
            product_id = 5
            principal = float(np.clip(rng.lognormal(12.4, 0.35), 100000, 600000))
            term = int(rng.choice([240, 300, 360]))
            annual_rate = rng.uniform(3.2, 4.8)
        else:
            product_id = 4
            principal = float(np.clip(rng.lognormal(9.2, 0.6), 2000, 60000))
            term = int(rng.choice([12, 24, 36, 48, 60]))
            annual_rate = rng.uniform(6.5, 12.5)
        principal = round(principal, -2)
        annual_rate = round(annual_rate + "ABCDE".index(row.risk_rating) * 0.4, 2)

        monthly_rate = annual_rate / 1200.0
        instalment = round(principal * monthly_rate / (1 - (1 + monthly_rate) ** -term), 2)

        # The 2023 vintage was underwritten loosely: it misses far more payments.
        year = pd.Timestamp(origination).year
        p_miss = base_miss[row.risk_rating] * {2022: 1.2, 2023: 1.9}.get(year, 1.0)
        p_miss *= {5: 0.5, 6: 1.2}.get(product_id, 1.0)

        balance = principal
        unpaid = []                    # indexes of overdue instalments (oldest first)
        status, end_date = "active", None
        schedule = []
        for k in range(1, term + 1):
            due = add_months(origination, k)
            if pd.Timestamp(due) > obs_end:
                break
            interest = round(balance * monthly_rate, 2)
            principal_part = round(instalment - interest, 2) if k < term else round(balance, 2)
            balance = round(balance - principal_part, 2)
            schedule.append([loan_id, k, due, round(principal_part + interest, 2),
                             principal_part, interest, None, None])
            idx = len(schedule) - 1
            unpaid.append(idx)

            behind = len(unpaid) - 1   # instalments already overdue before this one
            if behind == 0:
                to_pay = [] if rng.random() < p_miss else [unpaid[0]]
                delay = int(rng.integers(0, 4))
            else:
                draw = rng.random()
                cure = cure_prob.get(behind, 0.05)
                if draw < cure:
                    to_pay = list(unpaid)              # clears all arrears
                elif draw < cure + 0.30:
                    to_pay = [unpaid[0]]               # pays the oldest instalment only
                else:
                    to_pay = []                        # misses again
                delay = int(rng.integers(0, 6))
            paid_date = pd.Timestamp(due) + pd.Timedelta(days=delay)
            if paid_date <= obs_end:
                for i in to_pay:
                    schedule[i][6] = paid_date.date()
                    schedule[i][7] = schedule[i][3]
                    unpaid.remove(i)

            if len(unpaid) >= 6:       # six instalments overdue: the loan is written off
                status, end_date = "charged_off", due
                break
        else:
            if not unpaid:
                status, end_date = "paid_off", schedule[-1][6]

        payments.extend(schedule)
        loans.append([loan_id, row.customer_id, product_id, origination, principal,
                      annual_rate, term, instalment, status, end_date])

    loans = pd.DataFrame(loans, columns=[
        "loan_id", "customer_id", "product_id", "origination_date", "principal",
        "annual_rate_pct", "term_months", "instalment", "status", "end_date"])
    payments = pd.DataFrame(payments, columns=[
        "loan_id", "instalment_no", "due_date", "due_amount", "principal_component",
        "interest_component", "paid_date", "paid_amount"])
    return loans, payments


# --------------------------------------------------------------------------
# Product holdings (with planted cross-sell affinities)
# --------------------------------------------------------------------------
def build_holdings(rng, customers, accounts, loans) -> pd.DataFrame:
    n = len(customers)
    cid = customers["customer_id"].to_numpy()
    join = to_days(customers["join_date"])
    closed = to_days(customers["closed_date"])
    segment = customers["segment"].to_numpy()
    is_business = (customers["customer_type"] == "business").to_numpy()
    wealthy = np.isin(segment, ["affluent", "private"])

    frames = [pd.DataFrame({
        "customer_id": accounts["customer_id"],
        "product_id": np.where(accounts["account_type"] == "current", 1, 2),
        "open_date": accounts["open_date"]})]
    frames.append(pd.DataFrame({
        "customer_id": loans["customer_id"], "product_id": loans["product_id"],
        "open_date": loans["origination_date"], "close_date": loans["end_date"]}))

    def later(max_days):
        return join + rng.integers(0, max_days + 1, n).astype("timedelta64[D]")

    has_mortgage = np.isin(cid, loans.loc[loans["product_id"] == 5, "customer_id"])
    p_card = np.where(is_business, 0.50, np.where(wealthy, 0.55, 0.38))
    p_insurance = np.where(has_mortgage, 0.70, 0.12)
    p_pension = np.where(is_business, 0.0, np.select(
        [segment == "private", segment == "affluent"], [0.40, 0.25], 0.06))
    has_pension = rng.random(n) < p_pension
    p_fund = np.where(has_pension, 0.45, 0.04) + np.where(segment == "private", 0.20, 0.0)

    for product_id, mask in [(3, rng.random(n) < p_card), (7, rng.random(n) < p_insurance),
                             (8, has_pension), (9, rng.random(n) < p_fund)]:
        opened = later(900)
        mask = mask & (opened <= OBS_END) & (np.isnat(closed) | (opened < closed))
        frames.append(pd.DataFrame({
            "customer_id": cid[mask], "product_id": product_id, "open_date": opened[mask]}))

    holdings = pd.concat(frames, ignore_index=True)
    holdings = holdings.merge(
        customers[["customer_id", "closed_date"]], on="customer_id", how="left")
    holdings["close_date"] = pd.to_datetime(holdings["close_date"]).fillna(
        pd.to_datetime(holdings["closed_date"]))
    holdings = holdings.drop(columns="closed_date").sort_values(
        ["customer_id", "product_id", "open_date"]).reset_index(drop=True)
    holdings.insert(0, "holding_id", np.arange(1, len(holdings) + 1))
    return holdings


# --------------------------------------------------------------------------
# Data-quality problems for the staging layer to fix
# --------------------------------------------------------------------------
def dirty_customers(rng, customers: pd.DataFrame, branches: pd.DataFrame) -> pd.DataFrame:
    out = customers.drop(columns="_dormant_from").merge(
        branches[["branch_id", "county"]], on="branch_id")
    out = out.sort_values("customer_id").reset_index(drop=True)
    county = out["county"].to_numpy(dtype=object)
    messy = rng.random(len(out)) < 0.03
    style = rng.integers(0, 3, len(out))
    county[messy & (style == 0)] = [c.upper() for c in county[messy & (style == 0)]]
    county[messy & (style == 1)] = [c.lower() for c in county[messy & (style == 1)]]
    county[messy & (style == 2)] = [f"  {c} " for c in county[messy & (style == 2)]]
    out["county"] = county
    duplicates = out.sample(n=max(5, len(out) // 130), random_state=7)
    return pd.concat([out, duplicates], ignore_index=True).sample(frac=1, random_state=11)


def dirty_transactions(rng, txns: pd.DataFrame) -> pd.DataFrame:
    txns = txns.sort_values("txn_ts").reset_index(drop=True)
    txns.insert(0, "txn_id", np.arange(1, len(txns) + 1))
    n = len(txns)
    next_id = n + 1

    def junk(k, **changes):
        nonlocal next_id
        sample = txns.sample(n=k, random_state=int(rng.integers(0, 2**31))).copy()
        sample["txn_id"] = np.arange(next_id, next_id + k)
        next_id += k
        for column, value in changes.items():
            sample[column] = value(sample) if callable(value) else value
        return sample

    orphan_ids = lambda s: 9_000_000 + np.arange(len(s))
    extra = [
        txns.sample(n=max(10, n // 1000), random_state=3),                # exact duplicates
        junk(max(10, n // 4000), account_id=orphan_ids),                  # unknown accounts
        junk(max(10, n // 6000), amount=lambda s: -s["amount"]),          # sign errors
        junk(max(10, n // 12000), txn_ts=pd.NaT),                         # missing timestamp
    ]
    return pd.concat([txns] + extra, ignore_index=True).sample(frac=1, random_state=5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scale", type=float, default=1.0,
                        help="1.0 = 20,000 customers and about 1.3 million transactions")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    n_customers = max(500, int(20000 * args.scale))

    branches = pd.DataFrame(
        [(i + 1, f"Liffey Bank {name}", town, county)
         for i, (name, town, county, _) in enumerate(BRANCHES)],
        columns=["branch_id", "branch_name", "town", "county"])
    products = pd.DataFrame(PRODUCTS, columns=["product_id", "product_name", "product_family"])

    customers = build_customers(rng, n_customers)
    accounts = build_accounts(rng, customers)
    txns = build_transactions(rng, customers, accounts)
    planted, labels = plant_aml_patterns(rng, customers, accounts, args.scale)
    txns = pd.concat([txns, planted], ignore_index=True)
    loans, payments = build_loans(rng, customers, int(n_customers * 0.3))
    holdings = build_holdings(rng, customers, accounts, loans)

    raw_customers = dirty_customers(rng, customers, branches)
    raw_txns = dirty_transactions(rng, txns)
    raw_payments = pd.concat(
        [payments, payments.sample(n=max(5, len(payments) // 3000), random_state=9)],
        ignore_index=True)

    for frame, column in [(raw_txns, "counterparty_account_id")]:
        frame[column] = frame[column].astype("Int64")

    outputs = {
        "branches": branches, "products": products, "customers": raw_customers,
        "accounts": accounts, "customer_products": holdings, "transactions": raw_txns,
        "loans": loans, "loan_payments": raw_payments, "aml_case_labels": labels,
    }
    for name, frame in outputs.items():
        frame.to_csv(args.out / f"{name}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
        print(f"{name:<18} {len(frame):>10,} rows")


if __name__ == "__main__":
    main()
