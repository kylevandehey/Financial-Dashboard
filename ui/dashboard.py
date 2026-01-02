"""Streamlit dashboard tab with defensive rendering and YoY analytics."""

from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL
from src.filters import compute_scope_date_range, filter_transactions_for_scope, period_options_for_scope
from src.ingest import identify_csv_roles, normalize_accounts, normalize_transactions
from src.metrics import (
    build_category_breakdown,
    build_monthly_cash_flow,
    build_yearly_balance_trends,
    build_yearly_income_expense,
    summarize_cash_flow,
)
from ui.transaction_filters import render_transaction_filters


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
    height: fit-content;
    z-index: 10;
}
.dashboard-sticky-panel > div {
    width: 100%;
}
</style>
"""


def _ensure_sticky_panel_style() -> None:
    if st.session_state.get("_dashboard_sticky_style_applied"):
        return
    st.markdown(_STICKY_PANEL_STYLE, unsafe_allow_html=True)
    st.session_state["_dashboard_sticky_style_applied"] = True


def _coerce_dataframe(data: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Return a copy of the incoming data or an empty frame."""
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


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
    return transactions_df, accounts_df


def _render_global_controls(transactions: pd.DataFrame, year_label: str) -> tuple[str, tuple[date, date], set[int]]:
    """Render reusable period selection and date bounds for all tabs."""
    period_options = period_options_for_scope(year_label)
    default_period = period_options[0]
    selected_period = st.radio(
        "Period Selection",
        period_options,
        index=period_options.index(default_period),
        key=f"dashboard_period_{year_label}",
    )

    default_start, default_end = compute_scope_date_range(transactions, year_label=year_label, period_label=selected_period)
    date_input = st.date_input(
        "Date Range",
        (default_start, default_end),
        key=f"dashboard_dates_{year_label}",
    )
    try:
        start_date, end_date = date_input
    except Exception:
        start_date, end_date = default_start, default_end

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    months_filter = _QUARTER_MONTHS.get(selected_period, set()) or _QUARTER_MONTHS.get(selected_period.upper(), set())
    return selected_period, (start_date, end_date), months_filter


def _render_date_status(date_range: Tuple[date, date]) -> None:
    start_date, end_date = date_range
    st.write("Date Range")
    st.caption(f"{start_date.strftime('%b %d, %Y')} → {end_date.strftime('%b %d, %Y')}")


def _render_data_status(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    selected_period: Optional[str] = None,
    date_range: Optional[Tuple[date, date]] = None,
) -> None:
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

    if date_range is None:
        fallback_date = date.today()
        date_range = (fallback_date, fallback_date)
    start_date, end_date = date_range
    _render_date_status((start_date, end_date))


def _render_transaction_configuration() -> None:
    """Wrap transaction filter configuration to ensure it only appears in the control rail."""
    render_transaction_filters()


def render_left_control_panel(
    transactions_df: Optional[pd.DataFrame],
    accounts_df: Optional[pd.DataFrame],
    year_label: str,
) -> tuple[str, tuple[date, date], set[int]]:
    """Render the sticky left rail shared across all tabs."""
    _ensure_sticky_panel_style()
    st.markdown('<div class="dashboard-sticky-panel">', unsafe_allow_html=True)

    st.markdown("### Controls & Status")
    uploaded_transactions, uploaded_accounts = _handle_uploads(year_label)
    active_transactions = _coerce_dataframe(uploaded_transactions or st.session_state.get("transactions_df") or transactions_df)
    active_accounts = _coerce_dataframe(uploaded_accounts or st.session_state.get("accounts_df") or accounts_df)

    selected_period, date_range, months_filter = _render_global_controls(active_transactions, year_label)
    _render_data_status(active_transactions, active_accounts, selected_period, date_range)

    st.markdown("---")
    _render_transaction_configuration()

    st.markdown("</div>", unsafe_allow_html=True)
    return selected_period, date_range, months_filter


def _render_header(year_label: str, selected_period: str) -> None:
    """Render the dashboard heading and scope context."""
    st.markdown("### Dashboard Overview")
    st.caption(
        f"Scope: {year_label} · Period: {selected_period}"
    )


def render_key_metrics(transactions: pd.DataFrame) -> None:
    """Render headline metrics with accounting-style formatting and guards."""
    if transactions is None or transactions.empty:
        st.info("No data available for selected filters.")
        return

    st.markdown("#### Key Metrics")
    totals = summarize_cash_flow(transactions)
    st.metric("Transactions", f"{len(transactions.index):,}")
    st.metric("Income", _format_currency(totals.income))
    st.metric("Expenses", _format_currency(totals.expenses))
    st.metric("Net Cash Flow", _format_currency(totals.net))


def render_monthly_cash_flow(transactions: pd.DataFrame, date_range: tuple[date, date]) -> None:
    if transactions is None or transactions.empty:
        st.info("No data available for selected filters.")
        return

    st.markdown("#### Cash Flow")
    monthly = build_monthly_cash_flow(transactions, date_range)
    if monthly.empty:
        st.info("Cash flow chart will appear after transactions are available for this period.")
        return

    ordered = monthly.sort_values("period_order")
    pivot = ordered.pivot(index="period_label", columns="flow", values="amount")
    st.bar_chart(pivot)


def render_category_breakdown(transactions: pd.DataFrame) -> None:
    if transactions is None or transactions.empty:
        st.info("No data available for selected filters.")
        return

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


def render_yoy_analytics(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    months_filter: set[int],
    selected_period: str,
) -> None:
    if transactions is None or transactions.empty:
        st.info("No data available for selected filters.")
        return

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
    year_context = year_label or ALL_YEARS_LABEL
    base_transactions = _coerce_dataframe(st.session_state.get("transactions_df") or transactions_df)
    base_accounts = _coerce_dataframe(st.session_state.get("accounts_df") or accounts_df)

    left_col, right_col = st.columns([1.1, 2.9], gap="large")

    with left_col:
        selected_period, date_range, months_filter = render_left_control_panel(
            base_transactions,
            base_accounts,
            year_context,
        )
        active_transactions = _coerce_dataframe(st.session_state.get("transactions_df") or base_transactions)
        active_accounts = _coerce_dataframe(st.session_state.get("accounts_df") or base_accounts)

    scoped_transactions = filter_transactions_for_scope(
        active_transactions,
        year_label=year_context,
        period_label=selected_period,
        date_range=date_range,
    )
    scoped_accounts = _coerce_dataframe(active_accounts)

    with right_col:
        _render_header(year_context, selected_period)
        if scoped_transactions.empty and scoped_accounts.empty:
            st.info("Upload transactions and accounts CSVs to enable full dashboard features.")
            return

        render_key_metrics(scoped_transactions)
        render_monthly_cash_flow(scoped_transactions, date_range)
        render_category_breakdown(scoped_transactions)

        if year_context == ALL_YEARS_LABEL:
            render_yoy_analytics(
                scoped_transactions,
                scoped_accounts,
                months_filter,
                selected_period,
            )

    if scoped_transactions.empty and base_transactions.empty and base_accounts.empty:
        st.info("Upload transactions and accounts CSVs to enable full dashboard features.")


if __name__ == "__main__":
    print("dashboard.py imports successfully")
