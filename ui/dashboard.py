"""Streamlit dashboard tab with defensive rendering and YoY analytics."""

from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

import pandas as pd
import altair as alt
import streamlit as st

from src.config import ALL_YEARS_LABEL
from src.formatting import format_currency, format_date_range
from src.metrics import (
    build_category_breakdown,
    build_monthly_cash_flow,
    build_yearly_balance_trends,
    build_yearly_income_expense,
    get_balances_snapshot,
    summarize_cash_flow,
    summarize_accounts,
)

_QUARTER_MONTHS: dict[str, set[int]] = {
    "Q1": {1, 2, 3},
    "Q2": {4, 5, 6},
    "Q3": {7, 8, 9},
    "Q4": {10, 11, 12},
}


def _make_section_id(section: str, year_label: str, selected_period: str) -> str:
    normalized = f"{section}_{year_label}_{selected_period}".lower().replace(" ", "_")
    return f"dashboard_{normalized}"


def _coerce_dataframe(data: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Return a copy of the incoming data or an empty frame."""
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def _currency_axis(title: str | None = None) -> alt.Axis:
    """Altair axis with accounting-style label formatting."""
    return alt.Axis(
        title=title,
        labelExpr="datum.value < 0 ? '($' + format(-datum.value, ',.2f') + ')' : '$' + format(datum.value, ',.2f')",
    )


def _render_header(year_label: str, selected_period: str, date_range: tuple[date, date]) -> None:
    """Render the dashboard heading and scope context."""
    st.markdown("### Dashboard Overview")
    st.caption(f"Scope: {year_label} · Period: {selected_period}")
    st.caption("Date Range")
    st.caption(format_date_range(date_range))


def _render_data_grid(df: pd.DataFrame, *, title: str, section_id: str, height: int | None = None) -> None:
    """Reusable, stateful collapsible data grid for tables under charts."""
    row_count = len(df.index) if df is not None else 0
    header = f"{title} ({row_count} rows)"
    expanded_default = st.session_state.get(section_id, False)
    with st.expander(header, expanded=expanded_default, key=section_id):
        st.dataframe(df, use_container_width=True, height=height)


def render_key_metrics(transactions: pd.DataFrame, accounts: pd.DataFrame, date_range: tuple[date, date]) -> None:
    """Render headline metrics with consistent grouping and accounting formatting."""
    if (transactions is None or transactions.empty) and (accounts is None or accounts.empty):
        st.info("No data available for selected filters. Metrics shown below use zero values until data is uploaded.")

    st.markdown("#### Key Metrics")
    totals = summarize_cash_flow(transactions, date_range)
    account_summary = summarize_accounts(accounts, end_date=date_range[1] if accounts is not None else None)

    start_date, end_date = date_range
    start_label = start_date.strftime("%b %d, %Y")
    end_label = end_date.strftime("%b %d, %Y")

    transaction_count = len(transactions.index) if transactions is not None else 0
    st.caption(f"{transaction_count:,} transactions in scope · {start_label} → {end_label}")

    cash_flow_group, balance_sheet_group = st.columns(2)
    with cash_flow_group:
        st.markdown("**Cash Flow**")
        income_col, expense_col, net_col = st.columns(3)
        with income_col:
            st.metric("Income", format_currency(totals.income))
        with expense_col:
            st.metric("Expenses", format_currency(totals.expenses))
        with net_col:
            st.metric("Net Cash Flow", format_currency(totals.net))

    with balance_sheet_group:
        st.markdown("**Balance Sheet**")
        assets_col, liabilities_col, networth_col = st.columns(3)
        with assets_col:
            st.metric("Assets", format_currency(account_summary["total_assets"]))
        with liabilities_col:
            st.metric("Liabilities", format_currency(account_summary["total_liabilities"]))
        with networth_col:
            st.metric("Net Worth", format_currency(account_summary["net_worth"]))


def render_monthly_cash_flow(transactions: pd.DataFrame, date_range: tuple[date, date], *, section_id: str) -> None:
    if transactions is None or transactions.empty:
        st.info("No data available for selected filters.")
        return

    st.markdown("#### Cash Flow")
    monthly = build_monthly_cash_flow(transactions, date_range)
    if monthly.empty:
        st.info("Cash flow chart will appear after transactions are available for this period.")
        return

    ordered = monthly.sort_values("period_order").copy()
    ordered["formatted_amount"] = ordered["amount"].map(format_currency)
    # Safe extension point: swap chart types without changing the ordered DataFrame schema.
    chart = (
        alt.Chart(ordered)
        .mark_bar()
        .encode(
            x=alt.X("period_label:N", sort=ordered["period_label"].tolist(), title="Period"),
            xOffset="flow",
            y=alt.Y("amount:Q", axis=_currency_axis("Amount")),
            color=alt.Color(
                "flow:N",
                title="Flow",
                sort=["Income", "Expenses"],
                scale=alt.Scale(domain=["Income", "Expenses"], range=["#2e7d32", "#c62828"]),
            ),
            tooltip=[
                alt.Tooltip("period_label:N", title="Period"),
                alt.Tooltip("flow:N", title="Flow"),
                alt.Tooltip("formatted_amount:N", title="Amount"),
            ],
        )
    )
    st.altair_chart(chart, use_container_width=True)

    display = ordered[["period_label", "flow", "amount"]].copy()
    display["Amount"] = ordered["formatted_amount"]
    display = display.rename(columns={"period_label": "Period", "flow": "Flow"})[["Period", "Flow", "Amount"]]
    _render_data_grid(display, title="Cash Flow Data", section_id=section_id)


def render_category_breakdown(transactions: pd.DataFrame, *, section_id: str) -> None:
    if transactions is None or transactions.empty:
        st.info("No data available for selected filters.")
        return

    st.markdown("#### Category Pressure")
    breakdown = build_category_breakdown(transactions, top_n=6)
    if breakdown.empty:
        st.info("Categories unavailable; upload data to see top categories.")
        return

    ordered = breakdown.sort_values("amount", ascending=True).copy()
    ordered["formatted_amount"] = ordered["amount"].map(format_currency)
    # Safe extension point: adjust visualization without mutating the category aggregation contract.
    chart = (
        alt.Chart(ordered)
        .mark_bar()
        .encode(
            x=alt.X("amount:Q", axis=_currency_axis("Amount")),
            y=alt.Y("label:N", sort=ordered["label"].tolist(), title="Category"),
            tooltip=[
                alt.Tooltip("label:N", title="Category"),
                alt.Tooltip("formatted_amount:N", title="Amount"),
            ],
            color=alt.Color("label:N", legend=None),
        )
    )
    st.altair_chart(chart, use_container_width=True)

    display = ordered[["label", "formatted_amount"]].rename(columns={"label": "Category", "formatted_amount": "Amount"})
    _render_data_grid(display, title="Category Data", section_id=section_id)


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


def _render_yoy_metric_block(title: str, df: pd.DataFrame, column: str, *, section_id: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        if df.empty or column not in df.columns:
            st.info("Upload data to view year-over-year analytics.")
            return

        chart_data = df.sort_values("year").copy()
        chart_data["formatted_amount"] = chart_data[column].map(format_currency)
        chart = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(
                x=alt.X("year:O", title="Year"),
                y=alt.Y(f"{column}:Q", axis=_currency_axis("Amount")),
                tooltip=[
                    alt.Tooltip("year:O", title="Year"),
                    alt.Tooltip("formatted_amount:N", title="Amount"),
                ],
            )
        )
        st.altair_chart(chart, use_container_width=True)

        latest_value, delta_value, prior_year = _latest_delta(df, column)
        delta_pct = None
        prior_value = None
        if prior_year is not None:
            prior_value = float(df.loc[df["year"] == prior_year, column].iloc[0])
            if prior_value != 0:
                delta_pct = (delta_value / prior_value) * 100 if delta_value is not None else None

        delta_display = "No prior year"
        if delta_value is not None and prior_year is not None:
            delta_display = f"{format_currency(delta_value)} vs {prior_year}"
        st.metric(
            "Latest",
            format_currency(latest_value or 0.0),
            delta=delta_display,
        )
        if delta_pct is not None and prior_year is not None:
            st.caption(f"Δ % vs {prior_year}: {delta_pct:.1f}%")
        else:
            st.caption("Δ % vs prior year: N/A")

        display = chart_data[["year", "formatted_amount"]].rename(columns={"formatted_amount": "Amount"})
        _render_data_grid(display, title=f"{title} Data", height=175, section_id=section_id)


def render_yoy_analytics(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    months_filter: set[int],
    selected_period: str,
    *,
    key_prefix: str,
) -> None:
    if transactions is None or transactions.empty:
        st.info("No data available for selected filters.")
        return

    st.markdown("#### Year-over-Year Analytics")

    preset = "full_year" if selected_period.upper() == ALL_YEARS_LABEL else selected_period.lower()
    balance_trends = build_yearly_balance_trends(accounts, preset=preset)
    flow_trends = build_yearly_income_expense(
        transactions,
        months=months_filter if selected_period.upper() in _QUARTER_MONTHS else None,
    )

    balance_cols = st.columns(3)
    for col, (title, field) in zip(
        balance_cols, [("Net Worth", "net_worth"), ("Assets", "assets"), ("Liabilities", "liabilities")]
    ):
        with col:
            _render_yoy_metric_block(title, balance_trends, field, section_id=f"{key_prefix}_{field}")

    flow_cols = st.columns(2)
    for col, (title, field) in zip(flow_cols, [("Income", "income"), ("Expenses", "expenses")]):
        with col:
            _render_yoy_metric_block(title, flow_trends, field, section_id=f"{key_prefix}_{field}")


def render_balance_snapshot(accounts: pd.DataFrame, date_range: tuple[date, date], *, section_id: str) -> None:
    if accounts is None or accounts.empty:
        return

    st.markdown("#### Balance Snapshot")
    snapshot = get_balances_snapshot(accounts, end_date=date_range[1])
    if snapshot.empty:
        st.info("No balances available for this period.")
        return

    summary = summarize_accounts(snapshot, end_date=date_range[1])

    aggregated = pd.DataFrame(
        {
            "label": ["Assets", "Liabilities", "Net Worth"],
            "amount": [summary["total_assets"], summary["total_liabilities"], summary["net_worth"]],
        }
    )
    aggregated["display_amount"] = aggregated["amount"].abs()
    aggregated["formatted_amount"] = aggregated["amount"].map(format_currency)
    aggregated["label_with_amount"] = aggregated["label"] + ": " + aggregated["formatted_amount"]

    base = alt.Chart(aggregated)
    pie = base.mark_arc().encode(
        theta=alt.Theta("display_amount:Q", stack=True),
        color=alt.Color("label:N", title=""),
        tooltip=[
            alt.Tooltip("label:N", title="Metric"),
            alt.Tooltip("formatted_amount:N", title="Amount"),
        ],
    )
    labels = base.mark_text(radius=120, size=12).encode(
        theta=alt.Theta("display_amount:Q", stack=True),
        color=alt.Color("label:N", legend=None),
        text=alt.Text("label_with_amount:N"),
    )
    st.altair_chart(pie + labels, use_container_width=True)
    balance_table = aggregated[["label", "formatted_amount"]].rename(
        columns={"label": "Metric", "formatted_amount": "Amount"}
    )
    _render_data_grid(balance_table, title="Balance Snapshot Data", section_id=section_id)


def render_dashboard_tab(
    transactions_df: Optional[pd.DataFrame],
    accounts_df: Optional[pd.DataFrame],
    *,
    year_label: str,
    selected_period: str,
    date_range: Tuple[date, date],
    months_filter: set[int],
) -> None:
    """Render the dashboard tab without triggering ingestion or layout resets."""
    transactions = _coerce_dataframe(transactions_df)
    accounts = _coerce_dataframe(accounts_df)
    # Safe extension point: introduce new stacked modules here without touching ingestion or control wiring.
    section_id_for = lambda section: _make_section_id(section, year_label, selected_period)

    _render_header(year_label, selected_period, date_range)
    if transactions.empty and accounts.empty:
        st.info("Upload transactions and accounts CSVs to enable full dashboard features.")
        return

    render_key_metrics(transactions, accounts, date_range)
    render_monthly_cash_flow(transactions, date_range, section_id=section_id_for("cash_flow_data"))
    render_category_breakdown(transactions, section_id=section_id_for("category_pressure"))
    render_balance_snapshot(accounts, date_range, section_id=section_id_for("balance_snapshot"))

    if year_label == ALL_YEARS_LABEL:
        render_yoy_analytics(
            transactions,
            accounts,
            months_filter,
            selected_period,
            key_prefix=section_id_for("yoy"),
        )
