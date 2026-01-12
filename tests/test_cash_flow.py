import pandas as pd

from src.cash_flow import compute_cash_flow


def test_refund_in_shopping_offsets_expenses_not_income():
    df = pd.DataFrame(
        [
            {"amount": -100.0, "category": "Shopping"},
            {"amount": 40.0, "category": "Shopping"},
        ]
    )
    result = compute_cash_flow(df)

    assert result.income == 0.0
    assert result.gross_expenses == 100.0
    assert result.expense_offsets == 40.0
    assert result.net_expenses == 60.0
    assert result.net_cash == -60.0


def test_income_category_counts_as_income():
    df = pd.DataFrame(
        [
            {"amount": 1500.0, "category": "Paycheck"},
            {"amount": -200.0, "category": "Shopping"},
        ]
    )
    result = compute_cash_flow(df)

    assert result.income == 1500.0
    assert result.gross_expenses == 200.0
    assert result.expense_offsets == 0.0
    assert result.net_expenses == 200.0
    assert result.net_cash == 1300.0


def test_transfers_and_cc_payments_excluded():
    df = pd.DataFrame(
        [
            {"amount": 2000.0, "category": "Transfer"},
            {"amount": -2000.0, "category": "Transfer"},
            {"amount": -500.0, "category": "Credit Card Payment"},
            {"amount": 500.0, "category": "Credit Card Payment"},
            {"amount": 100.0, "category": "Paycheck"},
            {"amount": -25.0, "category": "Shopping"},
        ]
    )
    result = compute_cash_flow(df)

    # Only paycheck + shopping should remain
    assert result.included_rows == 2
    assert result.excluded_rows == 4

    assert result.income == 100.0
    assert result.gross_expenses == 25.0
    assert result.expense_offsets == 0.0
    assert result.net_expenses == 25.0
    assert result.net_cash == 75.0
