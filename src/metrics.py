"""
Financial aggregation helpers for the Dashboard tab.

All functions remain UI-agnostic so Streamlit surfaces can reuse them without
duplicating business logic.

Stabilization contract:
- Metric builder functions must tolerate empty inputs.
- Functions that are invoked from UI may accept `date_range` for API consistency.
- When `date_range` is provided, filtering occurs inside the metric builder unless
  explicitly documented otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping, Optional

import pandas as pd

from src.categories import aggregate_categories, format_accounting_currency
from src.debug import log_debug_event
from src.date_filters import compute_date_range, filter_dataframe_by_date


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


def get_balances_snapshot(balances_df: pd.DataFrame, end_date: Optional[date]) -> pd.DataFrame:
    """
    Select the latest balance per account up to end_date (inclusive).

    When end_date is None, the latest available balance per account is returned
    without truncating the dataset. This supports ALL YEARS views where the
    full balances CSV should be considered.
    """
    if balances_df is None or balances_df.empty:
        return pd.DataFrame(
            columns=["date", "account", "balance", "signed_balance", "is_asset", "is_liability", "subtype"]
        )

    working = balances_df.copy()
    working["date"] = pd.to_datetime(working["date"], errors="coerce").dt.normalize()
    working = working.dropna(subset=["date"])
    if working.empty:
        return pd.DataFrame(
            columns=["date", "account", "balance", "signed_balance", "is_asset", "is_liability", "subtype"]
        )

    cutoff = pd.to_datetime(end_date).normalize() if end_date is not None else working["date"].max()
    working = working.loc[working["date"] <= cutoff]
    if working.empty:
        return working

    working = working.sort_values("date")
    latest_indices = working.groupby("account")["date"].idxmax()
    snapshot = working.loc[latest_indices].copy()
    return snapshot


def summarize_accounts(accounts: pd.DataFrame, *, end_date: Optional[date] = None) -> Mapping[str, float]:
    """
    Return total assets, liabilities, and net worth from normalized accounts data.

    Expected columns:
        - signed_balance: float (positive for assets, negative for liabilities)
        - is_asset: bool
        - is_liability: bool

    Returns keys:
        - total_assets
        - total_liabilities (negative)
        - net_worth
    """
    if accounts is None or accounts.empty:
        return {"total_assets": 0.0, "total_liabilities": 0.0, "net_worth": 0.0}

    working_accounts = accounts
    if end_date is not None and "date" in accounts.columns:
        working_accounts = get_balances_snapshot(accounts, end_date)

    if working_accounts is None or working_accounts.empty:
        return {"total_assets": 0.0, "total_liabilities": 0.0, "net_worth": 0.0}

    total_assets = float(working_accounts.loc[working_accounts["is_asset"], "signed_balance"].sum())
    raw_liabilities = working_accounts.loc[working_accounts["is_liability"], "signed_balance"].sum()
    total_liabilities = -abs(float(raw_liabilities))
    net_worth = total_assets + total_liabilities

    totals = {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,
    }

    log_debug_event(
        "account_snapshot_totals",
        {
            "end_date": str(end_date) if end_date else "ALL",
            **totals,
        },
    )
    return totals


def build_yearly_balance_trends(
    accounts: pd.DataFrame,
    date_range: Iterable[date] | None = None,
    *,
    preset: str = "full_year",
) -> pd.DataFrame:
    """
    Return yearly net worth, assets, and liabilities snapshots for YoY comparisons.

    Note:
    - `date_range` is accepted for UI/API consistency but not used for computation here.
      YoY trends are computed using `preset` per year via compute_date_range().
    """
    if accounts is None or accounts.empty or "date" not in accounts.columns:
        return pd.DataFrame(columns=["year", "net_worth", "assets", "liabilities"])

    working = accounts.copy()
    working["date"] = pd.to_datetime(working["date"], errors="coerce")
    working = working.dropna(subset=["date"])
    if working.empty:
        return pd.DataFrame(columns=["year", "net_worth", "assets", "liabilities"])

    years = sorted(working["date"].dt.year.unique())
    rows: list[dict[str, float | int]] = []

    for year in years:
        try:
            _, end_date = compute_date_range(preset, year=int(year))
        except ValueError:
            continue

        summary = summarize_accounts(working, end_date=end_date)
        rows.append(
            {
                "year": int(year),
                "net_worth": summary["net_worth"],
                "assets": summary["total_assets"],
                "liabilities": summary["total_liabilities"],
            }
        )

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def summarize_cash_flow(transactions: pd.DataFrame, date_range: Iterable[date] | None = None) -> PeriodTotals:
    """
    Compute income and expense totals for the selected date range.
    """
    if transactions is None or transactions.empty:
        return PeriodTotals()

    filtered = (
        filter_dataframe_by_date(transactions, date_range, date_column="date") if date_range is not None else transactions
    )

    if filtered is None or filtered.empty:
        return PeriodTotals()

    income = float(filtered.loc[filtered["is_income"], "amount"].sum())
    expenses = float(filtered.loc[filtered["is_expense"], "amount"].sum())
    totals = PeriodTotals(income=income, expenses=expenses)

    log_debug_event(
        "cash_flow_totals",
        {
            "date_range": tuple(str(d) for d in date_range) if date_range is not None else "ALL",
            "income": income,
            "expenses": expenses,
            "net": totals.net,
        },
    )
    return totals


def expense_category_pressure(
    transactions: pd.DataFrame,
    date_range: Iterable[date] | None = None,
    top_n: int = 5,
) -> pd.DataFrame:
    """
    Return the top N expense categories by absolute spend for the selected range.
    """
    if transactions is None or transactions.empty:
        return pd.DataFrame(columns=["category", "total_amount", "transaction_count"])

    filtered = (
        filter_dataframe_by_date(transactions, date_range, date_column="date") if date_range is not None else transactions
    )
    if filtered is None or filtered.empty:
        return pd.DataFrame(columns=["category", "total_amount", "transaction_count"])

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


def _classify_asset_bucket(row: pd.Series) -> str:
    text = " ".join(
        str(row.get(field, "") or "") for field in ("type", "account_type", "subtype", "category", "account_group")
    ).lower()
    if any(keyword in text for keyword in ("cash", "checking", "saving", "money market")):
        return "Cash"
    if any(keyword in text for keyword in ("brokerage", "invest", "stock", "fund", "taxable")):
        return "Investments (Taxable)"
    if any(keyword in text for keyword in ("retire", "401", "ira", "roth", "pension")):
        return "Retirement"
    return "Other Assets"


def _classify_liability_bucket(row: pd.Series) -> str:
    text = " ".join(str(row.get(field, "") or "") for field in ("type", "account_type", "subtype", "category")).lower()
    if "mortgage" in text or "home" in text:
        return "Mortgage"
    if "credit" in text or "card" in text:
        return "Credit Cards"
    if "loan" in text or "lien" in text:
        return "Loans"
    return "Other Liabilities"


def build_balance_breakdowns(accounts_snapshot: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Prepare asset, liability, and net worth donut chart data from an accounts snapshot.
    """
    if accounts_snapshot is None or accounts_snapshot.empty:
        empty = pd.DataFrame({"label": [], "amount": []})
        return empty, empty, empty

    assets = accounts_snapshot.loc[accounts_snapshot["is_asset"]].copy()
    liabilities = accounts_snapshot.loc[accounts_snapshot["is_liability"]].copy()

    amount_column = "balance" if "balance" in accounts_snapshot.columns else "signed_balance"
    assets["bucket"] = assets.apply(_classify_asset_bucket, axis=1)
    liabilities["bucket"] = liabilities.apply(_classify_liability_bucket, axis=1)

    asset_breakdown = (
        assets.groupby("bucket")[amount_column]
        .sum()
        .abs()
        .reset_index()
        .rename(columns={"bucket": "label", amount_column: "amount"})
    )
    liability_breakdown = (
        liabilities.groupby("bucket")[amount_column]
        .sum()
        .abs()
        .reset_index()
        .rename(columns={"bucket": "label", amount_column: "amount"})
    )

    summary = summarize_accounts(accounts_snapshot)
    net_pie = pd.DataFrame(
        {
            "label": ["Assets", "Liabilities"],
            "amount": [summary["total_assets"], abs(summary["total_liabilities"])],
        }
    )
    return asset_breakdown, liability_breakdown, net_pie


def build_category_breakdown(
    transactions: pd.DataFrame,
    date_range: Iterable[date] | None = None,
    *,
    top_n: int = 5,
) -> pd.DataFrame:
    """
    Aggregate income and expense categories for donut visualization with an 'Other' bucket.

    Returns columns:
      - label
      - amount
    """
    if transactions is None or transactions.empty or top_n <= 0:
        return pd.DataFrame(columns=["label", "amount"])

    working = (
        filter_dataframe_by_date(transactions, date_range, date_column="date") if date_range is not None else transactions
    )
    if working is None or working.empty:
        return pd.DataFrame(columns=["label", "amount"])

    working = working.loc[working["is_income"] | working["is_expense"]].copy()
    if working.empty:
        return pd.DataFrame(columns=["label", "amount"])

    working["category"] = working["category"].fillna("").replace("", "Uncategorized")
    working["flow"] = working.apply(lambda row: "Income" if row.get("is_income") else "Expense", axis=1)
    working["label"] = working["flow"] + " · " + working["category"]
    working["amount"] = working["amount"].abs()

    grouped = working.groupby("label", as_index=False)["amount"].sum()
    ordered = grouped.sort_values(by=["amount", "label"], ascending=[False, True]).reset_index(drop=True)

    if len(ordered) <= top_n:
        return ordered

    top = ordered.head(top_n).copy()
    other_total = ordered["amount"].iloc[top_n:].sum()
    if other_total > 0:
        top = pd.concat([top, pd.DataFrame([{"label": "Other", "amount": other_total}])], ignore_index=True)

    return top


def build_monthly_cash_flow(transactions: pd.DataFrame, date_range: Iterable[date] | None = None) -> pd.DataFrame:
    """
    Build monthly income/expense totals for grouped bar visualization.
    """
    def _base_months(start, end) -> pd.DataFrame:
        months = pd.period_range(pd.to_datetime(start).to_period("M"), pd.to_datetime(end).to_period("M"), freq="M")
        base = pd.DataFrame({"period": months.to_timestamp(), "period_label": months.strftime("%b %Y")})
        base["period_order"] = range(len(base))
        return base

    if transactions is None or transactions.empty:
        if date_range is None:
            return pd.DataFrame(columns=["period_label", "period_order", "flow", "amount"])
        start, end = date_range
        base = _base_months(start, end)
        base["Income"] = 0.0
        base["Expenses"] = 0.0
        return base.melt(
            id_vars=["period_label", "period_order"],
            value_vars=["Income", "Expenses"],
            var_name="flow",
            value_name="amount",
        )

    filtered = filter_dataframe_by_date(transactions, date_range, date_column="date") if date_range is not None else transactions
    if filtered is None or filtered.empty:
        if date_range is None:
            return pd.DataFrame(columns=["period_label", "period_order", "flow", "amount"])
        start, end = date_range
        base = _base_months(start, end)
        base["Income"] = 0.0
        base["Expenses"] = 0.0
        return base.melt(
            id_vars=["period_label", "period_order"],
            value_vars=["Income", "Expenses"],
            var_name="flow",
            value_name="amount",
        )

    filtered = filtered.copy()
    filtered["date"] = pd.to_datetime(filtered["date"])
    period_series = filtered["date"].dt.to_period("M")
    if date_range is not None:
        start_period = pd.to_datetime(date_range[0]).to_period("M")
        end_period = pd.to_datetime(date_range[1]).to_period("M")
    else:
        start_period = period_series.min()
        end_period = period_series.max()

    months = pd.period_range(start_period, end_period, freq="M")

    base = pd.DataFrame({"period": months.to_timestamp(), "period_label": months.strftime("%b %Y")})
    base["period_order"] = range(len(base))

    income = (
        filtered.loc[filtered["is_income"]]
        .groupby(filtered["date"].dt.to_period("M"))["amount"]
        .sum()
        .reindex(months, fill_value=0)
    )
    expenses = (
        filtered.loc[filtered["is_expense"]]
        .groupby(filtered["date"].dt.to_period("M"))["amount"]
        .sum()
        .reindex(months, fill_value=0)
    )

    base["Income"] = income.values
    base["Expenses"] = expenses.values

    melted = base.melt(
        id_vars=["period_label", "period_order"],
        value_vars=["Income", "Expenses"],
        var_name="flow",
        value_name="amount",
    )
    return melted


def build_yearly_income_expense(transactions: pd.DataFrame, *, months: set[int] | None = None) -> pd.DataFrame:
    """
    Aggregate yearly income and expenses to support YoY cash flow views.
    """
    if transactions is None or transactions.empty or "date" not in transactions.columns:
        return pd.DataFrame(columns=["year", "income", "expenses", "net_cash_flow"])

    working = transactions.copy()
    working["date"] = pd.to_datetime(working["date"], errors="coerce")
    working = working.dropna(subset=["date"])
    if months:
        working = working.loc[working["date"].dt.month.isin(months)]
    if working.empty:
        return pd.DataFrame(columns=["year", "income", "expenses", "net_cash_flow"])

    working["year"] = working["date"].dt.year

    income = working.loc[working["is_income"]].groupby("year")["amount"].sum()
    expenses = working.loc[working["is_expense"]].groupby("year")["amount"].sum()

    all_years = sorted(working["year"].unique())
    income = income.reindex(all_years, fill_value=0.0)
    expenses = expenses.reindex(all_years, fill_value=0.0)

    result = pd.DataFrame(
        {
            "year": all_years,
            "income": income.values,
            "expenses": expenses.values,
        }
    )
    result["net_cash_flow"] = result["income"] + result["expenses"]
    return result
