"""Streamlit dashboard tab with defensive rendering and YoY analytics."""

from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL
from src.date_filters import compute_date_range, filter_dataframe_by_date_and_month
from src.ingest import identify_csv_roles, normalize_accounts, normalize_transactions
from src.metrics import (
    build_category_breakdown,
    build_monthly_cash_flow,
    build_yearly_balance_trends,
    build_yearly_income_expense,
)


_QUARTER_MONTHS: dict[str, set[int]] = {
    "Q1": {1, 2, 3},
    "Q2": {4, 5, 6},
    "Q3": {7, 8, 9},
    "Q4": {10, 11, 12},
}

_STICKY_PANEL_STYLE = """
<style>
.dashboard-sticky-panel {
    position: sticky;
    top: 68px;
    z-index: 2;
}
.dashboard-sticky-panel > div {
    width: 100%;
}
</style>
"""


def _coerce_dataframe(data: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Return a copy of the incoming data or an empty frame."""
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def _infer_date_range(transactions: pd.DataFrame) -> tuple[date, date]:
    """Infer the available date range, falling back to today when missing."""
    today = date.today()
    if transactions.empty or "date" not in transactions.columns:
        return today, today

    dates = pd.to_datetime(transactions["date"], errors="coerce").dropna()
    if dates.empty:
        return today, today

    return dates.min().date(), dates.max().date()


def _filter_by_year(df: pd.DataFrame, year_label: Optional[str]) -> pd.DataFrame:
    """Filter transactions by the selected year label."""
    if df.empty or year_label in (None, ALL_YEARS_LABEL):
        return df

    if "year" not in df.columns:
        return df

    try:
        year_int = int(year_label)
    except (TypeError, ValueError):
        return df

    return df.loc[df["year"] == year_int].copy()


def _quarter_bounds_for_all_years(transactions: pd.DataFrame, months: set[int]) -> tuple[date, date]:
    """Return the min/max date for the specified quarter across all years."""
    if transactions.empty or "date" not in transactions.columns:
        return _infer_date_range(transactions)

    dates = pd.to_datetime(transactions["date"], errors="coerce")
    quarter_dates = dates.loc[dates.dt.month.isin(months)].dropna()
    if quarter_dates.empty:
        return _infer_date_range(transactions)
    return quarter_dates.min().date(), quarter_dates.max().date()


def _format_currency(value: float) -> str:
    """Format currency using accounting style for negatives."""
    amount = float(value or 0)
    formatted = f"${abs(amount):,.2f}"
    return f"({formatted})" if amount < 0 else formatted


def _handle_uploads(year_label: str) -> tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Process CSV uploads from the stationary panel, persisting to session state."""
    transactions_df: Optional[pd.DataFrame] = st.session_state.get("transactions_df")
    accounts_df: Optional[pd.DataFrame] = st.session_state.get("accounts_df")

    if year_label != ALL_YEARS_LABEL:
        st.caption("Upload and refresh from the ALL YEARS panel.")
        return transactions_df, accounts_df

    uploaded_files = st.file_uploader(
        "Upload Monarch CSVs",
        accept_multiple_files=True,
        type=["csv"],
        key="monarch_csvs",
    )

    if not uploaded_files:
        if transactions_df is None:
            st.warning("Upload Transactions and Balances CSVs to unlock analytics.")
        return transactions_df, accounts_df

    transactions_file, accounts_file, _diagnostics, error_message = identify_csv_roles(uploaded_files)
    if error_message:
        st.error(error_message)
        return transactions_df, accounts_df

    try:
        transactions_df = normalize_transactions(transactions_file)
    except ValueError as exc:
        st.error(f"Transactions CSV error: {exc}")
        return transactions_df, accounts_df

    try:
        accounts_df = normalize_accounts(accounts_file)
    except ValueError as exc:
        st.error(f"Accounts CSV error: {exc}")
        return transactions_df, accounts_df

    st.session_state["transactions_df"] = transactions_df
    st.session_state["accounts_df"] = accounts_df
    st.success("CSV upload processed. Dashboard refreshed.")
    st.experimental_rerun()
    return transactions_df, accounts_df


def _determine_period_scope(
    transactions: pd.DataFrame, year_label: str
) -> tuple[str, tuple[date, date], set[int], pd.DataFrame]:
    """Resolve the selected period and return filtered data."""
    period_label = "ALL YEARS" if year_label == ALL_YEARS_LABEL else "FULL YEAR"
    period_options = [period_label, "Q1", "Q2", "Q3", "Q4"]

    selected_period = st.radio(
        "Period Selection",
        period_options,
        index=0,
        key=f"dashboard_period_{year_label}",
    )

    months_filter = _QUARTER_MONTHS.get(selected_period, set())

    try:
        if selected_period == "ALL YEARS":
            start_date, end_date = _infer_date_range(transactions)
        elif selected_period == "FULL YEAR":
            start_date, end_date = compute_date_range("full_year", year=int(year_label))
        else:
            if year_label == ALL_YEARS_LABEL:
                start_date, end_date = _quarter_bounds_for_all_years(transactions, months_filter)
            else:
                start_date, end_date = compute_date_range(selected_period.lower(), year=int(year_label))
    except Exception:
        start_date, end_date = _infer_date_range(transactions)

    filtered = filter_dataframe_by_date_and_month(
        transactions,
        (start_date, end_date),
        months=months_filter or None,
        date_column="date",
    )
    return selected_period, (start_date, end_date), months_filter, filtered


def _render_date_status(date_range: Tuple[date, date]) -> None:
    start_date, end_date = date_range
    st.write("Date Range (read-only)")
    st.caption(f"{start_date.strftime('%b %d, %Y')} → {end_date.strftime('%b %d, %Y')}")


def _render_data_status(transactions: pd.DataFrame, accounts: pd.DataFrame) -> None:
    st.write("Status")
    if transactions.empty and accounts.empty:
        st.info("Awaiting uploads.")
    elif transactions.empty:
        st.warning("Transactions missing. Upload to enable analytics.")
    elif accounts.empty:
        st.warning("Accounts missing. Upload balances to unlock net worth.")
    else:
        st.success("Data ready")
    st.caption("Panel stays fixed while you scroll charts.")

    return selected_period, (start_date, end_date)


def _render_key_metrics(transactions: pd.DataFrame) -> None:
    """Render headline metrics vertically with accounting-style formatting."""
    st.write("Key Metrics")
    amount_series = pd.to_numeric(
        transactions.get("amount", pd.Series(dtype=float, index=transactions.index)),
        errors="coerce",
    )
    total_count = len(transactions.index)
    total_income = amount_series[amount_series > 0].sum() if not amount_series.empty else 0.0
    total_expense = amount_series[amount_series < 0].sum() if not amount_series.empty else 0.0
    net = amount_series.sum() if not amount_series.empty else 0.0

    st.metric("Transactions", f"{total_count:,}")
    st.metric("Income", _format_currency(total_income))
    st.metric("Expenses", _format_currency(total_expense))
    st.metric("Net Cash Flow", _format_currency(net))


def _render_stationary_panel(
    scoped_transactions: pd.DataFrame, accounts: pd.DataFrame, year_label: str
) -> tuple[str, tuple[date, date], set[int], pd.DataFrame, pd.DataFrame]:
    """Render the fixed left-side panel with upload, scope, and key metrics."""
    st.markdown(_STICKY_PANEL_STYLE, unsafe_allow_html=True)
    st.markdown('<div class="dashboard-sticky-panel">', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("### Controls & Status")
        transactions_df, accounts_df = _handle_uploads(year_label)
        working_transactions = _coerce_dataframe(scoped_transactions)
        accounts_df = _coerce_dataframe(accounts_df)

        selected_period, date_range, months_filter, filtered = _determine_period_scope(working_transactions, year_label)
        _render_date_status(date_range)
        _render_data_status(working_transactions, accounts_df)
        _render_key_metrics(filtered)
    st.markdown("</div>", unsafe_allow_html=True)

    return selected_period, date_range, months_filter, filtered, _coerce_dataframe(accounts_df)


def _render_header(year_label: str, selected_period: str) -> None:
    """Render the dashboard heading and scope context."""
    st.markdown("### Dashboard Overview")
    st.caption(
        f"Scope: {year_label} · Period: {selected_period}"
    )


def _render_cash_flow(transactions: pd.DataFrame, date_range: tuple[date, date]) -> None:
    st.markdown("#### Cash Flow")
    monthly = build_monthly_cash_flow(transactions, date_range)
    if monthly.empty:
        st.info("Cash flow chart will appear after transactions are available for this period.")
        return

    ordered = monthly.sort_values("period_order")
    pivot = ordered.pivot(index="period_label", columns="flow", values="amount")
    st.bar_chart(pivot)


def _render_category_breakdown(transactions: pd.DataFrame) -> None:
    st.markdown("#### Category Pressure")
    breakdown = build_category_breakdown(transactions, top_n=6)
    if breakdown.empty:
        st.info("Categories unavailable; upload data to see top categories.")
        return
    st.bar_chart(breakdown.set_index("label")["amount"])


def _latest_delta(df: pd.DataFrame, column: str) -> tuple[Optional[float], Optional[float], Optional[int]]:
    ordered = df.sort_values("year")
    if ordered.empty or column not in ordered.columns:
        return None, None, None
    latest_row = ordered.iloc[-1]
    prior_row = ordered.iloc[-2] if len(ordered.index) > 1 else None
    latest_value = float(latest_row[column])
    if prior_row is None:
        return latest_value, None, None
    delta_value = latest_value - float(prior_row[column])
    return latest_value, delta_value, int(prior_row["year"])


def _render_yoy_metric_block(title: str, df: pd.DataFrame, column: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        if df.empty or column not in df.columns:
            st.info("Upload data to view year-over-year analytics.")
            return

        chart_data = df.set_index("year")[[column]]
        st.bar_chart(chart_data)

        latest_value, delta_value, prior_year = _latest_delta(df, column)
        delta_pct = None
        prior_value = None
        if prior_year is not None:
            prior_value = float(df.loc[df["year"] == prior_year, column].iloc[0])
            if prior_value != 0:
                delta_pct = (delta_value / prior_value) * 100 if delta_value is not None else None

        delta_display = "No prior year"
        if delta_value is not None and prior_year is not None:
            delta_display = f"{_format_currency(delta_value)} vs {prior_year}"
        st.metric(
            "Latest",
            _format_currency(latest_value or 0.0),
            delta=delta_display,
        )
        if delta_pct is not None and prior_year is not None:
            st.caption(f"Δ % vs {prior_year}: {delta_pct:.1f}%")
        else:
            st.caption("Δ % vs prior year: N/A")


def _render_yoy_analytics(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    months_filter: set[int],
    selected_period: str,
) -> None:
    st.markdown("#### Year-over-Year Analytics")

    preset = "full_year" if selected_period == "ALL YEARS" else selected_period.lower()
    balance_trends = build_yearly_balance_trends(accounts, preset=preset)
    flow_trends = build_yearly_income_expense(
        transactions,
        months=months_filter if selected_period in _QUARTER_MONTHS else None,
    )

    balance_cols = st.columns(3)
    for col, (title, field) in zip(balance_cols, [("Net Worth", "net_worth"), ("Assets", "assets"), ("Liabilities", "liabilities")]):
        with col:
            _render_yoy_metric_block(title, balance_trends, field)

    flow_cols = st.columns(2)
    for col, (title, field) in zip(flow_cols, [("Income", "income"), ("Expenses", "expenses")]):
        with col:
            _render_yoy_metric_block(title, flow_trends, field)


def render_dashboard_tab(
    transactions_df: Optional[pd.DataFrame],
    accounts_df: Optional[pd.DataFrame],
    year_label: Optional[str] = None,
) -> None:
    """Render the dashboard tab with fixed controls and YoY analytics."""
    transactions = _coerce_dataframe(transactions_df)
    accounts = _coerce_dataframe(accounts_df)

    year_context = year_label or ALL_YEARS_LABEL
    scoped_transactions = _filter_by_year(transactions, year_context)

    left_col, right_col = st.columns([1.05, 2.95], gap="large")

    with left_col:
        selected_period, date_range, months_filter, filtered_transactions, scoped_accounts = _render_stationary_panel(
            scoped_transactions,
            accounts,
            year_context,
        )

    with right_col:
        _render_header(year_context, selected_period)
        if filtered_transactions.empty and scoped_accounts.empty:
            st.info("Upload transactions and accounts CSVs to enable full dashboard features.")
            return

        if year_context == ALL_YEARS_LABEL:
            _render_yoy_analytics(filtered_transactions, scoped_accounts, months_filter, selected_period)
        else:
            _render_cash_flow(filtered_transactions, date_range)
            _render_category_breakdown(filtered_transactions)

    if scoped_transactions.empty and transactions.empty and accounts.empty:
        st.info("Upload transactions and accounts CSVs to enable full dashboard features.")


if __name__ == "__main__":
    print("dashboard.py imports successfully")
