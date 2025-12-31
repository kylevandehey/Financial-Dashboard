"""
Category aggregation and formatting helpers.

All functions in this module are intentionally Streamlit-free to keep
business logic testable and reusable across UI surfaces.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd


CategorySign = Literal["income", "expense"]


def _require_columns(df: pd.DataFrame, category_column: str, amount_column: str) -> None:
    missing = [col for col in (category_column, amount_column) if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def _prepare_transactions(
    df: pd.DataFrame, category_column: str = "Category", amount_column: str = "Amount"
) -> pd.DataFrame:
    """
    Copy and coerce numeric values so aggregation is reliable.
    """
    _require_columns(df, category_column, amount_column)
    prepared = df[[category_column, amount_column]].copy()
    prepared[amount_column] = pd.to_numeric(prepared[amount_column], errors="coerce")
    prepared = prepared.dropna(subset=[amount_column])
    return prepared


def _filter_by_sign(df: pd.DataFrame, sign: CategorySign, amount_column: str) -> pd.DataFrame:
    if sign == "income":
        return df[df[amount_column] > 0]
    return df[df[amount_column] < 0]


def aggregate_categories(
    transactions: pd.DataFrame,
    *,
    sign: CategorySign,
    category_column: str = "Category",
    amount_column: str = "Amount",
) -> pd.DataFrame:
    """
    Aggregate transactions by category for either income or expenses.

    Returns a DataFrame with columns: category, total_amount, transaction_count.
    """
    prepared = _prepare_transactions(transactions, category_column, amount_column)
    filtered = _filter_by_sign(prepared, sign=sign, amount_column=amount_column)

    if filtered.empty:
        return pd.DataFrame(columns=["category", "total_amount", "transaction_count"])

    grouped = (
        filtered.groupby(category_column)[amount_column]
        .agg(total_amount="sum", transaction_count="count")
        .reset_index()
    )
    grouped = grouped.rename(columns={category_column: "category"})
    return grouped[["category", "total_amount", "transaction_count"]]


def aggregate_income_categories(
    transactions: pd.DataFrame, *, category_column: str = "Category", amount_column: str = "Amount"
) -> pd.DataFrame:
    return aggregate_categories(
        transactions,
        sign="income",
        category_column=category_column,
        amount_column=amount_column,
    )


def aggregate_expense_categories(
    transactions: pd.DataFrame, *, category_column: str = "Category", amount_column: str = "Amount"
) -> pd.DataFrame:
    return aggregate_categories(
        transactions,
        sign="expense",
        category_column=category_column,
        amount_column=amount_column,
    )


def _ordered_categories(category_totals: pd.DataFrame) -> pd.DataFrame:
    if category_totals.empty:
        return category_totals.copy()

    working = category_totals.copy()
    working["abs_total_amount"] = working["total_amount"].abs()
    ordered = working.sort_values(
        by=["abs_total_amount", "category"], ascending=[False, True]
    ).drop(columns="abs_total_amount")
    return ordered.reset_index(drop=True)


def get_top_categories(category_totals: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Return the top N categories ordered by absolute total_amount.
    """
    if n <= 0:
        return pd.DataFrame(columns=["category", "total_amount", "transaction_count"])
    ordered = _ordered_categories(category_totals)
    return ordered.head(n)


def get_all_categories(category_totals: pd.DataFrame) -> pd.DataFrame:
    """
    Return all categories ordered by absolute total_amount.
    """
    return _ordered_categories(category_totals)


def format_accounting_currency(value: float) -> str:
    """
    Format values using accounting-style parentheses for negatives.
    """
    if pd.isna(value):
        value = 0.0
    absolute = abs(value)
    formatted = f"${absolute:,.2f}"
    return f"({formatted})" if value < 0 else formatted
