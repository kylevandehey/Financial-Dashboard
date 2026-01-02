"""Dashboard tab rendering for Control Tower."""

from __future__ import annotations

from datetime import date
from typing import Optional, Sequence

import pandas as pd
import plotly.express as px
import streamlit as st

from src.categories import format_accounting_currency
from src.filters import TransactionFilterConfig, apply_transaction_config
from src.date_filters import compute_date_range, compute_month_range, filter_dataframe_by_date_and_month
from src.metrics import (
    PeriodTotals,
    build_cash_flow_chart_data,
    expense_category_pressure,
    get_balances_snapshot,
    summarize_accounts,
    summarize_cash_flow,
)

ALL_PRESET_OPTIONS = [
    ("q1", "Q1"),
    ("q2", "Q2"),
    ("q3", "Q3"),
    ("q4", "Q4"),
]
YEAR_PRESET_OPTIONS = [
    ("last_week_to_date", "WTD"),
    ("mtd", "MTD"),
    ("ytd", "YTD"),
    *ALL_PRESET_OPTIONS,
]
MONTH_TAB_LABELS = [
    "All Months",
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
    if label.upper() == "ALL":
        return None
    try:
        return int(label)
    except ValueError:
        return None


def _key_fragment(label: str) -> str:
    return label.lower().replace(" ", "_")


def _month_from_label(label: str) -> Optional[int]:
    normalized = label.lower().strip()
    return MONTH_NAME_TO_NUMBER.get(normalized)


def _classify_asset(subtype: str) -> str:
    text = (subtype or "").lower()
    if any(keyword in text for keyword in ["cash", "checking", "saving", "money market"]):
        return "Cash"
    if any(keyword in text for keyword in ["brokerage", "invest", "stock", "fund"]):
        return "Investments"
    if any(keyword in text for keyword in ["retire", "401", "ira", "roth"]):
        return "Retirement"
    return "Other"


def _classify_liability(subtype: str) -> str:
    text = (subtype or "").lower()
    if "credit" in text or "card" in text:
        return "Credit"
    if any(keyword in text for keyword in ["mortgage", "auto", "secured"]):
        return "Secured"
    if "loan" in text:
        return "Loans"
    return "Unsecured"


def _prepare_balance_breakdown(accounts_snapshot: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if accounts_snapshot is None or accounts_snapshot.empty:
        empty = pd.DataFrame({"label": [], "amount": []})
        return empty, empty, empty

    assets = accounts_snapshot.loc[accounts_snapshot["is_asset"]].copy()
    liabilities = accounts_snapshot.loc[accounts_snapshot["is_liability"]].copy()

    assets["bucket"] = assets["subtype"].map(_classify_asset)
    liabilities["bucket"] = liabilities["subtype"].map(_classify_liability)

    asset_breakdown = (
        assets.groupby("bucket")["balance"].sum().abs().reset_index().rename(columns={"bucket": "label", "balance": "amount"})
    )
    liability_breakdown = (
        liabilities.groupby("bucket")["balance"].sum().abs().reset_index().rename(columns={"bucket": "label", "balance": "amount"})
    )

    summary = summarize_accounts(accounts_snapshot)
    net_pie = pd.DataFrame(
        {
            "label": ["Assets", "Liabilities"],
            "amount": [summary["total_assets"], abs(summary["total_liabilities"])],
        }
    )
    return asset_breakdown, liability_breakdown, net_pie


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
    preset_key = f"preset_{_key_fragment(year_label)}_{_key_fragment(month_label)}"
    custom_key = f"custom_dates_{_key_fragment(year_label)}_{_key_fragment(month_label)}"
    use_custom_key = f"use_custom_{_key_fragment(year_label)}_{_key_fragment(month_label)}"

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
            if month_label != "All Months":
                st.info("Month tab active — quarter presets are hidden.")
                selected_label = "month_scope"
            else:
                preset_options = ALL_PRESET_OPTIONS if context == "all_years" else YEAR_PRESET_OPTIONS
                preset_values = [value for value, _ in preset_options]
                default_index = preset_values.index("ytd") if "ytd" in preset_values else 0
                selected_label = st.radio(
                    "Period",
                    options=preset_values,
                    format_func=lambda x: dict(preset_options)[x],
                    horizontal=True,
                    index=default_index,
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
) -> tuple[tuple[date, date], Optional[Sequence[int]]]:
    year_context = _year_from_label(year_label)
    month_number = _month_from_label(month_label)
    month_filter: Optional[Sequence[int]] = None

    if use_custom and custom_range:
        base_range = custom_range
    elif context == "all_years":
        base_range = (available_start, available_end)
    else:
        base_range = compute_date_range(
            selected_preset if selected_preset != "month_scope" else "ytd",
            year=year_context,
        )

    if context == "all_years":
        month_filter = QUARTER_MONTHS.get(selected_preset)

    if month_number:
        month_filter = {month_number}
        if year_context:
            base_range = compute_month_range(year_context, month_number)

    return base_range, month_filter


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


def _render_cash_flow_timeseries(transactions: pd.DataFrame, *, context: str) -> None:
    if transactions is None or transactions.empty:
        st.info("No transactions available for charting in this range.")
        return

    working = transactions.copy()
    working["date"] = pd.to_datetime(working["date"])
    working["year"] = working["date"].dt.year
    working["month"] = working["date"].dt.month
    working["month_label"] = working["month"].apply(lambda m: date(2000, m, 1).strftime("%b"))

    income = working.loc[working["is_income"], ["year", "month", "month_label", "amount"]].copy()
    income["flow"] = "Income"

    expenses = working.loc[working["is_expense"], ["year", "month", "month_label", "amount"]].copy()
    expenses["amount"] = expenses["amount"].abs()
    expenses["flow"] = "Expenses"

    combined = pd.concat([income, expenses], ignore_index=True)
    if combined.empty:
        st.info("No income or expense rows available for charting.")
        return

    if context == "all_years":
        grouped = combined.groupby(["year", "flow"], as_index=False)["amount"].sum()
        grouped["period"] = grouped["year"].astype(str)
        x_label = "Year"
    else:
        grouped = combined.groupby(["month", "month_label", "flow"], as_index=False)["amount"].sum()
        grouped = grouped.sort_values("month")
        grouped["period"] = pd.Categorical(
            grouped["month_label"],
            categories=MONTH_TAB_LABELS[1:],
            ordered=True,
        )
        x_label = "Month"

    if grouped.empty:
        st.info("No transactions available for the selected scope.")
        return

    fig = px.bar(
        grouped,
        x="period",
        y="amount",
        color="flow",
        barmode="group",
        labels={"amount": "Amount", "period": x_label, "flow": "Flow"},
    )
    fig.update_layout(legend_title="Flow Type", bargap=0.2)
    st.plotly_chart(fig, use_container_width=True)


def _render_cash_flow(totals: PeriodTotals, transactions: pd.DataFrame, *, context: str) -> None:
    st.markdown("### Cash Flow Summary")
    cols = st.columns([2, 1])
    with cols[0]:
        _render_cash_flow_timeseries(transactions, context=context)

    chart_df = build_cash_flow_chart_data(totals)
    with cols[0]:
        _render_donut(chart_df, "Income vs Expenses", color_sequence=px.colors.qualitative.Set2)

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


def _render_transaction_configuration(year_label: str) -> TransactionFilterConfig:
    st.markdown("#### Configure Transactions")
    with st.container(border=True):
        type_col, include_col, exclude_col = st.columns([1.2, 1.4, 1.4])

        available_types = ["transfer", "payment", "refund", "adjustment"]
        excluded_types = type_col.multiselect(
            "Exclude types",
            options=available_types,
            default=list(st.session_state.get("excluded_transaction_types", [])),
            key=f"excluded_types_dash_{_key_fragment(year_label)}",
        )

        include_keywords = include_col.text_input(
            "Only include keywords",
            value=", ".join(st.session_state.get("include_keywords", [])),
            key=f"include_keywords_dash_{_key_fragment(year_label)}",
            placeholder="paycheck, bonus",
        )
        exclude_keywords = exclude_col.text_input(
            "Exclude keywords",
            value=", ".join(st.session_state.get("exclude_keywords", [])),
            key=f"exclude_keywords_dash_{_key_fragment(year_label)}",
            placeholder="transfer, move",
        )

    config = TransactionFilterConfig.from_keyword_strings(
        excluded_types=excluded_types,
        include_keywords=include_keywords,
        exclude_keywords=exclude_keywords,
    )
    st.session_state["excluded_transaction_types"] = config.excluded_types
    st.session_state["include_keywords"] = config.include_keywords
    st.session_state["exclude_keywords"] = config.exclude_keywords
    return config


def render_dashboard_tab(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    *,
    year_label: str,
) -> None:
    context = "all_years" if _year_from_label(year_label) is None else "single_year"
    today = date.today()
    available_start = (
        pd.to_datetime(transactions["date"]).min().date() if transactions is not None and not transactions.empty else today
    )
    available_end = (
        pd.to_datetime(transactions["date"]).max().date() if transactions is not None and not transactions.empty else today
    )

    month_tabs = st.tabs(MONTH_TAB_LABELS)
    for month_tab, month_label in zip(month_tabs, MONTH_TAB_LABELS):
        with month_tab:
            selected_preset, custom_range, use_custom, range_placeholder = _render_global_controls(
                transactions,
                accounts,
                year_label=year_label,
                month_label=month_label,
                context=context,
                available_start=available_start,
                available_end=available_end,
            )
            config = _render_transaction_configuration(year_label)
            filtered_transactions = apply_transaction_config(transactions, config)

            date_range, month_filter = _resolve_time_scope(
                selected_preset=selected_preset,
                custom_range=custom_range,
                use_custom=use_custom,
                year_label=year_label,
                month_label=month_label,
                context=context,
                available_start=available_start,
                available_end=available_end,
            )
            scoped_transactions = filter_dataframe_by_date_and_month(
                filtered_transactions,
                date_range,
                months=month_filter,
                date_column="date",
            )
            active_range = _determine_active_range(scoped_transactions, date_range)
            range_placeholder.metric(
                label="Dates",
                value=f"{active_range[0].isoformat()} → {active_range[1].isoformat()}",
            )

            totals = summarize_cash_flow(scoped_transactions)
            end_date = active_range[1]
            account_snapshot = get_balances_snapshot(accounts, end_date) if accounts is not None else accounts
            account_summary = summarize_accounts(account_snapshot)

            _render_metric_cards(account_summary, totals)

            st.markdown("### Balance Sheet Composition")
            asset_breakdown, liability_breakdown, net_breakdown = _prepare_balance_breakdown(account_snapshot)
            asset_col, liability_col, net_col = st.columns(3)
            with asset_col:
                _render_donut(asset_breakdown, "Assets Breakdown")
            with liability_col:
                _render_donut(liability_breakdown, "Liabilities Breakdown")
            with net_col:
                _render_donut(net_breakdown, "Net Worth Context")

            _render_cash_flow(totals, scoped_transactions, context=context)
            _render_top_categories(scoped_transactions)
