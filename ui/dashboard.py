"""Dashboard tab rendering for Control Tower."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

import pandas as pd
import plotly.express as px
import streamlit as st

from src.categories import format_accounting_currency
from src.config import ALL_YEARS_LABEL
from src.date_filters import compute_date_range, compute_month_range, filter_dataframe_by_date_and_month
from src.metrics import (
    PeriodTotals,
    build_balance_breakdowns,
    build_category_breakdown,
    build_monthly_cash_flow,
    expense_category_pressure,
    get_balances_snapshot,
    summarize_accounts,
    summarize_cash_flow,
)

ALL_MONTHS_LABEL = "ALL MONTHS"
CURRENT_YEAR_PRESETS = [
    ("last_week_to_date", "WTD"),
    ("mtd", "MTD"),
    ("ytd", "YTD"),
    ("full_year", "Full Year"),
    ("q1", "Q1"),
    ("q2", "Q2"),
    ("q3", "Q3"),
    ("q4", "Q4"),
]
HISTORICAL_YEAR_PRESETS = [
    ("full_year", "Full Year"),
    ("q1", "Q1"),
    ("q2", "Q2"),
    ("q3", "Q3"),
    ("q4", "Q4"),
]
ALL_YEARS_PRESETS = [("all_years_span", "All Years")]
MONTH_TAB_LABELS = [
    ALL_MONTHS_LABEL,
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
MONTH_NAME_TO_NUMBER = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
QUARTER_MONTHS: dict[str, set[int]] = {
    "q1": {1, 2, 3},
    "q2": {4, 5, 6},
    "q3": {7, 8, 9},
    "q4": {10, 11, 12},
}


def _year_from_label(label: str) -> Optional[int]:
    normalized = str(label).strip().upper()
    if normalized in {"ALL", ALL_YEARS_LABEL}:
        return None
    try:
        return int(label)
    except ValueError:
        return None


def _key_fragment(label: str) -> str:
    return label.lower().replace(" ", "_")


def _month_from_label(label: str) -> Optional[int]:
    normalized = label.lower().strip()
    if normalized == ALL_MONTHS_LABEL.lower():
        return None
    return MONTH_NAME_TO_NUMBER.get(normalized)


@dataclass
class ScopeSelection:
    """Resolved filters for the current year/month scope."""

    date_range: tuple[date, date]
    month_filter: Optional[Sequence[int]]
    scope_context: str


def _preset_options(year_context: Optional[int], *, is_month_scope: bool, today: date) -> list[tuple[str, str]]:
    if is_month_scope:
        return []

    if year_context is None:
        return ALL_YEARS_PRESETS

    return CURRENT_YEAR_PRESETS if year_context == today.year else HISTORICAL_YEAR_PRESETS


def _render_donut(chart_df: pd.DataFrame, title: str, color_sequence: Optional[list[str]] = None) -> None:
    if chart_df.empty or chart_df["amount"].sum() == 0:
        st.info(f"No data available for {title.lower()}.")
        return

    fig = px.pie(
        chart_df,
        names="label",
        values="amount",
        hole=0.5,
        color_discrete_sequence=color_sequence,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.subheader(title)
    st.plotly_chart(fig, use_container_width=True)


def _render_global_controls(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    *,
    year_label: str,
    month_label: str,
    context: str,
    available_start: date,
    available_end: date,
) -> tuple[str, tuple[date, date], bool, st.delta_generator.DeltaGenerator]:
    st.markdown("### Global Controls")
    key_prefix = f"dashboard_{_key_fragment(year_label)}_{_key_fragment(month_label)}"
    preset_key = f"preset_{key_prefix}"
    custom_key = f"custom_dates_{key_prefix}"
    use_custom_key = f"use_custom_{key_prefix}"

    is_month_scope = month_label != ALL_MONTHS_LABEL
    available_presets = _preset_options(_year_from_label(year_label), is_month_scope=is_month_scope, today=date.today())

    with st.container(border=True):
        status_col, preset_col, custom_col, info_col = st.columns([1.2, 2.4, 2.4, 1.4])

        with status_col:
            if transactions is not None and not transactions.empty and accounts is not None and not accounts.empty:
                st.success("CSV uploads detected")
            elif transactions is not None and not transactions.empty:
                st.warning("Transactions loaded\nAccounts missing")
            elif accounts is not None and not accounts.empty:
                st.warning("Accounts loaded\nTransactions missing")
            else:
                st.error("No CSV data")

            data_as_of = pd.to_datetime(transactions["date"]).max() if transactions is not None and not transactions.empty else None
            if data_as_of:
                st.caption(f"Data as of {data_as_of.date().isoformat()}")

        with preset_col:
            st.caption("Preset Ranges")
            if not available_presets:
                st.info("Month tab active — presets are controlled by the tab scope.")
                selected_label = "month_scope"
            else:
                preset_values = [value for value, _ in available_presets]
                default_label = "ytd" if "ytd" in preset_values else preset_values[0]
                selected_label = st.radio(
                    "Period",
                    options=preset_values,
                    format_func=lambda x: dict(available_presets)[x],
                    horizontal=True,
                    index=preset_values.index(default_label),
                    key=preset_key,
                )

        with custom_col:
            st.caption("Custom Range")
            use_custom = st.checkbox("Use custom dates", key=use_custom_key, value=False)
            start_default = available_start if isinstance(available_start, date) else available_start.date()
            end_default = available_end if isinstance(available_end, date) else available_end.date()
            default_range = (start_default, end_default)
            chosen_range = st.date_input(
                "Start / End",
                value=default_range,
                min_value=start_default,
                max_value=end_default,
                key=custom_key,
            )
            if isinstance(chosen_range, tuple):
                custom_start, custom_end = chosen_range
            elif isinstance(chosen_range, list) and len(chosen_range) == 2:
                custom_start, custom_end = chosen_range
            else:
                custom_start, custom_end = default_range

        with info_col:
            st.caption("Active Range")
            range_placeholder = st.empty()

    return selected_label, (custom_start, custom_end), use_custom, range_placeholder


def _resolve_time_scope(
    *,
    selected_preset: str,
    custom_range: tuple[date, date],
    use_custom: bool,
    year_label: str,
    month_label: str,
    context: str,
    available_start: date,
    available_end: date,
    *,
    today: date,
) -> ScopeSelection:
    year_context = _year_from_label(year_label)
    month_number = _month_from_label(month_label)
    month_filter: Optional[Sequence[int]] = None

    if use_custom and custom_range:
        base_range = custom_range
    elif context == "all_years":
        base_range = (available_start, available_end)
    elif month_number and year_context:
        base_range = compute_month_range(year_context, month_number)
    else:
        preset_for_range = selected_preset if selected_preset not in {"month_scope", "all_years_span"} else "full_year"
        base_range = compute_date_range(
            preset_for_range,
            year=year_context,
            today=today,
        )

    if month_number:
        month_filter = {month_number}
    elif year_context:
        month_filter = QUARTER_MONTHS.get(selected_preset)

    return ScopeSelection(date_range=base_range, month_filter=month_filter, scope_context=context)


def _determine_active_range(transactions: Optional[pd.DataFrame], fallback_range: tuple[date, date]) -> tuple[date, date]:
    if transactions is not None and not transactions.empty and "date" in transactions.columns:
        start_date = pd.to_datetime(transactions["date"]).min().date()
        end_date = pd.to_datetime(transactions["date"]).max().date()
        return start_date, end_date
    return fallback_range


def _render_metric_cards(account_summary: dict[str, float], totals: PeriodTotals) -> None:
    st.markdown("### Key Financial Metrics")
    cards = [
        ("💼 Net Worth", account_summary["net_worth"]),
        ("💰 Total Assets", account_summary["total_assets"]),
        ("🏦 Total Liabilities", account_summary["total_liabilities"]),
        ("📈 Total Income", totals.income),
        ("💸 Total Expenses", totals.expenses),
        ("💾 Savings Rate", f"{totals.savings_rate * 100:.1f}%"),
    ]

    columns = st.columns(len(cards))
    for col, (label, value) in zip(columns, cards):
        if isinstance(value, str):
            col.metric(label, value)
        else:
            col.metric(label, format_accounting_currency(value))


def _render_cash_flow_timeseries(transactions: pd.DataFrame, *, date_range: tuple[date, date]) -> None:
    monthly = build_monthly_cash_flow(transactions, date_range)
    if monthly is None or monthly.empty:
        st.info("No income or expense rows available for charting.")
        return

    monthly = monthly.sort_values("period_order")
    period_order = monthly["period_label"].drop_duplicates().tolist()
    fig = px.bar(
        monthly,
        x="period_label",
        y="amount",
        color="flow",
        barmode="group",
        labels={"amount": "Amount", "period_label": "Month", "flow": "Flow"},
        category_orders={"period_label": period_order},
    )
    fig.update_layout(legend_title="Flow Type", bargap=0.2)
    st.plotly_chart(fig, use_container_width=True)


def _render_cash_flow(totals: PeriodTotals, transactions: pd.DataFrame, *, date_range: tuple[date, date]) -> None:
    st.markdown("### Cash Flow Summary")
    cols = st.columns([2, 1])
    with cols[0]:
        _render_cash_flow_timeseries(transactions, date_range=date_range)
        category_breakdown = build_category_breakdown(transactions, top_n=5)
        _render_donut(category_breakdown, "Income vs Expenses Breakdown", color_sequence=px.colors.qualitative.Set2)

    with cols[1]:
        net_value = totals.net
        color = "green" if net_value >= 0 else "red"
        st.markdown(f"**Net Cash Flow:** :{color}[{format_accounting_currency(net_value)}]")
        st.caption("Positive values indicate surplus for the selected period.")


def _render_top_categories(transactions: pd.DataFrame) -> None:
    st.markdown("### Category Pressure Snapshot (Top 5)")
    top_expenses = expense_category_pressure(transactions, None, top_n=5)
    if top_expenses.empty:
        st.info("No expenses available for this period.")
        return

    for chunk in range(0, len(top_expenses), 5):
        cols = st.columns(min(5, len(top_expenses) - chunk))
        for col, (_, row) in zip(cols, top_expenses.iloc[chunk : chunk + 5].iterrows()):
            col.metric(
                label=f"💳 {row['category']}",
                value=format_accounting_currency(row["total_amount"]),
                delta=f"{int(row['transaction_count'])} tx",
            )
    st.caption("Showing top 5 expense categories by spend. 'Show more' coming soon.")


def render_dashboard_tab(
    filtered_transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    *,
    year_label: str,
) -> None:
    context = "all_years" if _year_from_label(year_label) is None else "single_year"
    today = date.today()
    available_start = (
        pd.to_datetime(filtered_transactions["date"]).min().date()
        if filtered_transactions is not None and not filtered_transactions.empty
        else today
    )
    available_end = (
        pd.to_datetime(filtered_transactions["date"]).max().date()
        if filtered_transactions is not None and not filtered_transactions.empty
        else today
    )

    month_tabs = st.tabs(MONTH_TAB_LABELS)
    for month_tab, month_label in zip(month_tabs, MONTH_TAB_LABELS):
        with month_tab:
            selected_preset, custom_range, use_custom, range_placeholder = _render_global_controls(
                filtered_transactions,
                accounts,
                year_label=year_label,
                month_label=month_label,
                context=context,
                available_start=available_start,
                available_end=available_end,
            )
            scope = _resolve_time_scope(
                selected_preset=selected_preset,
                custom_range=custom_range,
                use_custom=use_custom,
                year_label=year_label,
                month_label=month_label,
                context=context,
                available_start=available_start,
                available_end=available_end,
                today=today,
            )
            scoped_transactions = filter_dataframe_by_date_and_month(
                filtered_transactions,
                scope.date_range,
                months=scope.month_filter,
                date_column="date",
            )
            active_range = _determine_active_range(scoped_transactions, scope.date_range)
            range_placeholder.metric(
                label="Dates",
                value=f"{active_range[0].isoformat()} → {active_range[1].isoformat()}",
            )

            totals = summarize_cash_flow(scoped_transactions, scope.date_range)
            end_date = active_range[1]
            account_snapshot = get_balances_snapshot(accounts, None if scope.scope_context == "all_years" else end_date) if accounts is not None else accounts
            account_summary = summarize_accounts(account_snapshot)

            _render_metric_cards(account_summary, totals)

            st.markdown("### Balance Sheet Composition")
            asset_breakdown, liability_breakdown, net_breakdown = build_balance_breakdowns(account_snapshot)
            asset_col, liability_col, net_col = st.columns(3)
            with asset_col:
                _render_donut(asset_breakdown, "Assets Breakdown")
            with liability_col:
                _render_donut(liability_breakdown, "Liabilities Breakdown")
            with net_col:
                _render_donut(net_breakdown, "Net Worth Context")

            _render_cash_flow(totals, scoped_transactions, date_range=active_range)
            _render_top_categories(scoped_transactions)
