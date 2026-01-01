"""Dashboard tab rendering for Monarch+."""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from src.categories import format_accounting_currency
from src.filters import TransactionFilterConfig, apply_transaction_config
from src.date_filters import compute_date_range
from src.metrics import (
    PeriodTotals,
    build_cash_flow_chart_data,
    expense_category_pressure,
    summarize_accounts,
    summarize_cash_flow,
)

PRESET_OPTIONS = [
    ("last_week_to_date", "WTD"),
    ("mtd", "MTD"),
    ("ytd", "YTD"),
    ("q1", "Q1"),
    ("q2", "Q2"),
    ("q3", "Q3"),
    ("q4", "Q4"),
]


def _year_from_label(label: str) -> Optional[int]:
    if label.upper() == "ALL":
        return None
    try:
        return int(label)
    except ValueError:
        return None


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


def _prepare_balance_breakdown(accounts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if accounts is None or accounts.empty:
        empty = pd.DataFrame({"label": [], "amount": []})
        return empty, empty, empty

    assets = accounts.loc[accounts["is_asset"]].copy()
    liabilities = accounts.loc[accounts["is_liability"]].copy()

    assets["bucket"] = assets["subtype"].map(_classify_asset)
    liabilities["bucket"] = liabilities["subtype"].map(_classify_liability)

    asset_breakdown = (
        assets.groupby("bucket")["balance"].sum().abs().reset_index().rename(columns={"bucket": "label", "balance": "amount"})
    )
    liability_breakdown = (
        liabilities.groupby("bucket")["balance"].sum().abs().reset_index().rename(columns={"bucket": "label", "balance": "amount"})
    )

    summary = summarize_accounts(accounts)
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
) -> tuple[str, tuple[date, date]]:
    st.markdown("### Global Controls")
    default_today = date.today()
    available_start = pd.to_datetime(transactions["date"]).min() if transactions is not None and not transactions.empty else pd.Timestamp(default_today)
    available_end = pd.to_datetime(transactions["date"]).max() if transactions is not None and not transactions.empty else pd.Timestamp(default_today)

    preset_key = f"preset_{year_label}"
    custom_key = f"custom_dates_{year_label}"
    use_custom_key = f"use_custom_{year_label}"

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
            preset_labels = [label for _, label in PRESET_OPTIONS]
            preset_values = [value for value, _ in PRESET_OPTIONS]
            default_index = preset_values.index("ytd")
            selected_label = st.radio(
                "Period",
                options=preset_values,
                format_func=lambda x: dict(PRESET_OPTIONS)[x],
                horizontal=True,
                index=default_index,
                key=preset_key,
            )

        with custom_col:
            st.caption("Custom Range")
            use_custom = st.checkbox("Use custom dates", key=use_custom_key, value=False)
            default_range = (available_start.date(), available_end.date())
            chosen_range = st.date_input(
                "Start / End",
                value=default_range,
                min_value=available_start.date(),
                max_value=available_end.date(),
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
            year_context = _year_from_label(year_label)
            start_date, end_date = compute_date_range(
                selected_label,
                year=year_context,
                custom_start=custom_start if use_custom else None,
                custom_end=custom_end if use_custom else None,
            )
            st.metric(
                label="Dates",
                value=f"{start_date.isoformat()} → {end_date.isoformat()}",
            )

    return selected_label, (start_date, end_date)


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


def _render_cash_flow(totals: PeriodTotals) -> None:
    st.markdown("### Cash Flow Summary")
    cols = st.columns([2, 1])
    chart_df = build_cash_flow_chart_data(totals)
    with cols[0]:
        _render_donut(chart_df, "Income vs Expenses", color_sequence=px.colors.qualitative.Set2)

    with cols[1]:
        net_value = totals.net
        color = "green" if net_value >= 0 else "red"
        st.markdown(f"**Net Cash Flow:** :{color}[{format_accounting_currency(net_value)}]")
        st.caption("Positive values indicate surplus for the selected period.")


def _render_top_categories(transactions: pd.DataFrame, date_range: Iterable[date]) -> None:
    st.markdown("### Category Pressure Snapshot (Top 5)")
    top_expenses = expense_category_pressure(transactions, date_range, top_n=5)
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
            key=f"excluded_types_dash_{year_label}",
        )

        include_keywords = include_col.text_input(
            "Only include keywords",
            value=", ".join(st.session_state.get("include_keywords", [])),
            key=f"include_keywords_dash_{year_label}",
            placeholder="paycheck, bonus",
        )
        exclude_keywords = exclude_col.text_input(
            "Exclude keywords",
            value=", ".join(st.session_state.get("exclude_keywords", [])),
            key=f"exclude_keywords_dash_{year_label}",
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
    preset, date_range = _render_global_controls(transactions, accounts, year_label=year_label)
    config = _render_transaction_configuration(year_label)

    working_transactions = apply_transaction_config(transactions, config)

    totals = summarize_cash_flow(working_transactions, date_range)
    account_summary = summarize_accounts(accounts)

    _render_metric_cards(account_summary, totals)

    st.markdown("### Balance Sheet Composition")
    asset_breakdown, liability_breakdown, net_breakdown = _prepare_balance_breakdown(accounts)
    asset_col, liability_col, net_col = st.columns(3)
    with asset_col:
        _render_donut(asset_breakdown, "Assets Breakdown")
    with liability_col:
        _render_donut(liability_breakdown, "Liabilities Breakdown")
    with net_col:
        _render_donut(net_breakdown, "Net Worth Context")

    _render_cash_flow(totals)
    _render_top_categories(working_transactions, date_range)
