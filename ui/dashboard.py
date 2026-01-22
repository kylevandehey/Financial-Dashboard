# ui/dashboard.py

import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, timedelta

from src.cash_flow import compute_cash_flow, build_exclusion_mask
from src.formatting import format_currency, format_date_range

# =====================================================
# Date Range Presets (Ledger-Style, Canonical)
# =====================================================

def _resolve_date_range(tx: pd.DataFrame):
    if tx.empty or "date" not in tx.columns:
        return tx, None, None

    tx = tx.copy()
    tx["date"] = pd.to_datetime(tx["date"]).dt.date

    min_date = tx["date"].min()
    max_date = tx["date"].max()
    today = max_date

    years = sorted(tx["date"].apply(lambda d: d.year).unique(), reverse=True)

    preset_options = (
        ["ALL YEARS"]
        + ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 180 Days", "Last Full Year"]
        + [str(y) for y in years]
        + ["Custom Range"]
    )

    preset = st.selectbox(
        "Date Range Presets",
        preset_options,
        index=0,
        key="dashboard_date_preset",
    )

    start_date = None
    end_date = None

    if preset == "ALL YEARS":
        start_date, end_date = min_date, max_date

    elif preset.startswith("Last "):
        days = int(preset.split()[1])
        start_date = today - timedelta(days=days)
        end_date = today

    elif preset == "Last Full Year":
        y = today.year - 1
        start_date = date(y, 1, 1)
        end_date = date(y, 12, 31)

    elif preset.isdigit():
        y = int(preset)
        start_date = date(y, 1, 1)
        end_date = date(y, 12, 31)

    elif preset == "Custom Range":
        start_date, end_date = st.date_input(
            "Custom Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="dashboard_custom_range",
        )

    if not start_date or not end_date:
        return tx, None, None

    mask = (tx["date"] >= start_date) & (tx["date"] <= end_date)
    return tx.loc[mask], start_date, end_date


# =====================================================
# Helper Frames
# =====================================================

def _monthly_cash_flow_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["month_start"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()

    rows = []
    for m, g in df.groupby("month_start"):
        r = compute_cash_flow(g)
        rows.append(
            {
                "month_start": m,
                "Income": r.income,
                "Net Expenses": r.net_expenses,
                "Net Cash": r.net_cash,
            }
        )

    wide = pd.DataFrame(rows).sort_values("month_start")
    long = wide.melt(
        id_vars="month_start",
        value_vars=["Income", "Net Expenses", "Net Cash"],
        var_name="metric",
        value_name="value",
    )
    long["value_fmt"] = long["value"].apply(format_currency)
    return long


def _category_volatility_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")

    rows = []
    for (cat, month), g in df.groupby(["category", "month"]):
        rows.append(
            {
                "category": cat or "(Uncategorized)",
                "month": month,
                "net_cash": compute_cash_flow(g).net_cash,
            }
        )

    monthly = pd.DataFrame(rows)
    agg = (
        monthly.groupby("category")["net_cash"]
        .agg(avg_net="mean", volatility="std", months="count")
        .reset_index()
        .sort_values("volatility", ascending=False)
    )

    agg["avg_net_fmt"] = agg["avg_net"].apply(format_currency)
    agg["volatility_fmt"] = agg["volatility"].fillna(0).apply(format_currency)
    return agg


# =====================================================
# Dashboard Renderer
# =====================================================

def render_dashboard_tab(transactions: pd.DataFrame) -> None:
    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    # -----------------------------
    # Date Controls (Single Source)
    # -----------------------------
    filtered_tx, start_date, end_date = _resolve_date_range(transactions)

    if start_date and end_date:
        st.caption("Date Range")
        st.caption(format_date_range((start_date, end_date)))

    if filtered_tx.empty:
        st.info("No transactions in selected date range.")
        return

    # -----------------------------
    # Snapshot Metrics
    # -----------------------------
    result = compute_cash_flow(filtered_tx)

    st.markdown("### Snapshot")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Income", format_currency(result.income))
    with c2:
        st.metric("Expenses", format_currency(result.net_expenses))
    with c3:
        st.metric("Net Cash Flow", format_currency(result.net_cash))

    # -----------------------------
    # Snapshot Details
    # -----------------------------
    st.markdown("### Snapshot Details")

    income = (
        filtered_tx[filtered_tx["amount"] > 0]
        .groupby("merchant")["amount"]
        .sum()
        .nlargest(5)
        .reset_index()
    )

    expenses = (
        filtered_tx[filtered_tx["amount"] < 0]
        .groupby("merchant")["amount"]
        .sum()
        .nsmallest(5)
        .reset_index()
    )

    freq = (
        filtered_tx[filtered_tx["amount"] < 0]
        .groupby("merchant")
        .size()
        .nlargest(5)
        .reset_index(name="count")
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Top Income Sources**")
        st.bar_chart(income.set_index("merchant"))

    with c2:
        st.markdown("**Top Expenses**")
        st.bar_chart(expenses.set_index("merchant"))

    with c3:
        st.markdown("**Most Frequent Expenses**")
        st.bar_chart(freq.set_index("merchant"))

    # -----------------------------
    # Monthly Cash Flow Charts
    # -----------------------------
    monthly = _monthly_cash_flow_frame(filtered_tx)
    if not monthly.empty:
        st.markdown("### Cash Flow Charts (Canonical)")

        bars = monthly[monthly["metric"].isin(["Income", "Net Expenses"])]

        bar_chart = alt.Chart(bars).mark_bar().encode(
            x="month_start:T",
            xOffset="metric:N",
            y="value:Q",
            tooltip=["month_start:T", "metric:N", "value_fmt:N"],
        )

        net_line = alt.Chart(
            monthly[monthly["metric"] == "Net Cash"]
        ).mark_line(point=True).encode(
            x="month_start:T",
            y="value:Q",
            tooltip=["month_start:T", "value_fmt:N"],
        )

        st.altair_chart(bar_chart + net_line, use_container_width=True)

    # -----------------------------
    # Category Volatility
    # -----------------------------
    st.markdown("### Category Volatility")

    vol = _category_volatility_frame(filtered_tx)
    if not vol.empty:
        st.bar_chart(vol.set_index("category")[["volatility"]])

    # -----------------------------
    # Exclusions Audit
    # -----------------------------
    mask = build_exclusion_mask(filtered_tx)
    excluded = filtered_tx.loc[mask]

    st.markdown(f"**Excluded totals:** {format_currency(excluded['amount'].sum())}")

    with st.expander("Show excluded rows (audit)"):
        st.dataframe(excluded, use_container_width=True)

    st.caption(
        f"Expense offsets: {format_currency(result.expense_offsets)} | "
        f"Gross expenses: {format_currency(result.gross_expenses)}"
    )
