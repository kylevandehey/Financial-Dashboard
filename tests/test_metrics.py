import pandas as pd

from src.metrics import PeriodTotals, build_cash_flow_chart_data, expense_category_pressure, summarize_accounts, summarize_cash_flow


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
