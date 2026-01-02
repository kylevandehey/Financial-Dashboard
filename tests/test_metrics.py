import pandas as pd

from src.metrics import (
    PeriodTotals,
    build_balance_breakdowns,
    build_cash_flow_chart_data,
    build_category_breakdown,
    build_monthly_cash_flow,
    expense_category_pressure,
    summarize_accounts,
    summarize_cash_flow,
)


def test_summarize_accounts_handles_signed_balances():
    accounts = pd.DataFrame(
        {
            "signed_balance": [25000, -10000, 1500],
            "is_asset": [True, False, True],
            "is_liability": [False, True, False],
        }
    )

    summary = summarize_accounts(accounts)

    assert summary["total_assets"] == 26500
    assert summary["total_liabilities"] == -10000
    assert summary["net_worth"] == 16500


def test_summarize_cash_flow_filters_by_range():
    transactions = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-03-10", "2024-03-15"]),
            "amount": [5000, -1200, -800],
            "is_income": [True, False, False],
            "is_expense": [False, True, True],
        }
    )

    totals = summarize_cash_flow(transactions, (pd.Timestamp("2024-03-01"), pd.Timestamp("2024-03-31")))
    assert totals.income == 0
    assert totals.expenses == -2000


def test_summarize_cash_flow_honors_prefiltered_input():
    transactions = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-04-01", "2024-04-15"]),
            "amount": [1000, -200],
            "is_income": [True, False],
            "is_expense": [False, True],
        }
    )
    totals = summarize_cash_flow(transactions, None)
    assert totals.income == 1000
    assert totals.expenses == -200


def test_category_pressure_orders_by_abs_spend():
    transactions = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "category": ["Rent", "Dining", "Dining"],
            "amount": [-2000, -50, -75],
            "is_income": [False, False, False],
            "is_expense": [True, True, True],
        }
    )

    top = expense_category_pressure(transactions, (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31")))
    assert list(top["category"]) == ["Rent", "Dining"]
    assert list(top["total_amount"]) == [-2000, -125]


def test_category_pressure_accepts_prefiltered_transactions():
    transactions = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-02-01", "2024-02-02"]),
            "category": ["Dining", "Dining"],
            "amount": [-50, -25],
            "is_income": [False, False],
            "is_expense": [True, True],
        }
    )
    top = expense_category_pressure(transactions, None)
    assert list(top["total_amount"]) == [-75]


def test_cash_flow_chart_formats_accounting():
    totals = PeriodTotals(income=3000, expenses=-1500)

    chart_df = build_cash_flow_chart_data(totals)
    assert set(chart_df["label"]) == {"Income", "Expenses"}
    assert "$1,500.00" in chart_df["formatted"].iloc[1]


def test_category_breakdown_groups_other_bucket():
    transactions = pd.DataFrame(
        {
            "category": ["Salary", "Rent", "Dining", "Dining", "Bonus", "Utilities"],
            "amount": [5000, -2000, -50, -25, 500, -120],
            "is_income": [True, False, False, False, True, False],
            "is_expense": [False, True, True, True, False, True],
        }
    )

    breakdown = build_category_breakdown(transactions, top_n=2)
    assert "Income: Salary" in breakdown["label"].values
    assert "Expense: Rent" in breakdown["label"].values
    assert "Other" in breakdown["label"].values
    assert breakdown.loc[breakdown["label"] == "Other", "amount"].iloc[0] == 695


def test_monthly_cash_flow_returns_zero_months():
    transactions = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-15", "2024-03-20"]),
            "amount": [1000, -300],
            "is_income": [True, False],
            "is_expense": [False, True],
        }
    )

    monthly = build_monthly_cash_flow(transactions, (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-03-31")))
    income_jan = monthly[(monthly["period_label"] == "Jan 2024") & (monthly["flow"] == "Income")]["amount"].iloc[0]
    expense_feb = monthly[(monthly["period_label"] == "Feb 2024") & (monthly["flow"] == "Expenses")]["amount"].iloc[0]
    expense_mar = monthly[(monthly["period_label"] == "Mar 2024") & (monthly["flow"] == "Expenses")]["amount"].iloc[0]

    assert income_jan == 1000
    assert expense_feb == 0
    assert expense_mar == 300


def test_balance_breakdowns_classify_assets_and_liabilities():
    accounts = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-03-31"] * 5),
            "account": ["Checking", "Brokerage", "401k", "Visa", "Home Loan"],
            "type": ["Asset", "Asset", "Asset", "Credit", "Liability"],
            "subtype": ["Checking", "Investment", "Retirement", "Credit Card", "Mortgage"],
            "balance": [5000, 12000, 8000, -3000, -250000],
            "signed_balance": [5000, 12000, 8000, -3000, -250000],
            "is_asset": [True, True, True, False, False],
            "is_liability": [False, False, False, True, True],
        }
    )

    asset_breakdown, liability_breakdown, net = build_balance_breakdowns(accounts)

    assert "Cash" in asset_breakdown["label"].values
    assert "Investments (Taxable)" in asset_breakdown["label"].values
    assert "Retirement" in asset_breakdown["label"].values
    assert "Credit Cards" in liability_breakdown["label"].values
    assert "Mortgage" in liability_breakdown["label"].values
    assert set(net["label"]) == {"Assets", "Liabilities"}
