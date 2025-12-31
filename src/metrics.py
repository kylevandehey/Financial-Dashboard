"""
Financial aggregation helpers for the Dashboard tab.

All functions remain UI-agnostic so Streamlit surfaces can reuse them without
duplicating business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping, Optional

import pandas as pd

from src.categories import aggregate_categories, format_accounting_currency
from src.date_filters import filter_dataframe_by_date


@dataclass
class PeriodTotals:
    income: float = 0.0
    expenses: float = 0.0

    @property
    def net(self) -> float:
        return self.income + self.expenses

    @property
    def savings_rate(self) -> float:
        if self.income == 0:
            return 0.0
        return max(min(self.net / self.income, 1.0), -1.0)


def summarize_accounts(accounts: pd.DataFrame) -> Mapping[str, float]:
    """
    Return total assets, liabilities, and net worth from normalized accounts data.

    The accounts DataFrame is expected to contain:
        - signed_balance: float (positive for assets, negative for liabilities)
        - is_asset: bool
        - is_liability: bool
    """
    if accounts is None or accounts.empty:
        return {"total_assets": 0.0, "total_liabilities": 0.0, "net_worth": 0.0}

    total_assets = float(accounts.loc[accounts["is_asset"], "signed_balance"].sum())
    raw_liabilities = accounts.loc[accounts["is_liability"], "signed_balance"].sum()
    # Force liabilities to be negative so accounting-formatting renders parentheses.
    total_liabilities = -abs(float(raw_liabilities))
    net_worth = total_assets + total_liabilities
    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,
    }


def summarize_cash_flow(transactions: pd.DataFrame, date_range: Iterable[date]) -> PeriodTotals:
    """
    Compute income and expense totals for the selected date range.
    """
    if transactions is None or transactions.empty:
        return PeriodTotals()

    filtered = filter_dataframe_by_date(transactions, date_range, date_column="date")
    income = float(filtered.loc[filtered["is_income"], "amount"].sum())
    expenses = float(filtered.loc[filtered["is_expense"], "amount"].sum())
    return PeriodTotals(income=income, expenses=expenses)


def expense_category_pressure(
    transactions: pd.DataFrame, date_range: Iterable[date], top_n: int = 5
) -> pd.DataFrame:
    """
    Return the top N expense categories by absolute spend for the selected range.
    """
    if transactions is None or transactions.empty:
        return pd.DataFrame(columns=["category", "total_amount", "transaction_count"])

    filtered = filter_dataframe_by_date(transactions, date_range, date_column="date")
    expenses = aggregate_categories(
        filtered,
        sign="expense",
        category_column="category",
        amount_column="amount",
    )
    expenses = expenses.copy()
    expenses["abs_total"] = expenses["total_amount"].abs()
    ordered = expenses.sort_values(by=["abs_total", "category"], ascending=[False, True])
    return ordered.head(top_n).drop(columns=["abs_total"])


def build_cash_flow_chart_data(totals: PeriodTotals) -> pd.DataFrame:
    """
    Prepare income vs expense amounts for donut/stacked visualizations.
    """
    data = pd.DataFrame(
        {
            "label": ["Income", "Expenses"],
            "amount": [totals.income, abs(totals.expenses)],
        }
    )
    data["formatted"] = data["amount"].map(format_accounting_currency)
    return data
