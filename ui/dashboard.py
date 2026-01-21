import streamlit as st
import pandas as pd
import altair as alt
from datetime import date

from src.formatting import format_currency, format_date_range
from src.cash_flow import compute_cash_flow, build_exclusion_mask


# =====================================================
# Helpers
# =====================================================

def _coerce_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    return pd.DataFrame(df).copy()


def _derive_date_range(df: pd.DataFrame) -> tuple[date, date] | None:
    if df.empty or "date" not in df.columns:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return dates.min().date(), dates.max().date()


# -----------------------------
# Monthly cash flow (canonical)
# -----------------------------

def _monthly_cash_flow_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["month_start"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()

    rows = []
    for month, month_df in df.groupby("month_start"):
        r = compute_cash_flow(month_df)
        rows.append(
            {
                "month_start": month,
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


# -----------------------------
# Rolling net cash trend
# -----------------------------

def _monthly_net_cash_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["month_start"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()

    rows = []
    for month, group in df.groupby("month_start"):
        r = compute_cash_flow(group)
        rows.append(
            {
                "month_start": month,
                "net_cash": r.net_cash,
            }
        )

    out = pd.DataFrame(rows).sort_values("month_start")
    out["net_cash_fmt"] = out["net_cash"].apply(format_currency)
    return out


def _apply_rolling(df: pd.DataFrame, window: int) -> pd.Series:
    return df["net_cash"].rolling(window=window, min_periods=1).mean()


# -----------------------------
# Category analytics
# -----------------------------

def _category_monthly_net_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "category" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["month_start"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()

    rows = []
    for (category, month), group in df.groupby(["category", "month_start"]):
        r = compute_cash_flow(group)
        rows.append(
            {
                "category": category or "(Uncategorized)",
                "month_start": month,
                "net_cash": r.net_cash,
            }
        )

    return pd.DataFrame(rows)


def _category_volatility_frame(df: pd.DataFrame) -> pd.DataFrame:
    monthly = _category_monthly_net_frame(df)
    if monthly.empty:
        return pd.DataFrame()

    agg = (
        monthly.groupby("category")["net_cash"]
        .agg(
            avg_net="mean",
            volatility="std",
            months="count",
        )
        .reset_index()
    )

    agg["avg_net_fmt"] = agg["avg_net"].apply(format_currency)
    agg["volatility_fmt"] = agg["volatility"].fillna(0.0).apply(format_currency)

    return agg.sort_values("volatility", ascending=False)


# -----------------------------
# Snapshot detail helpers (PR-4)
# -----------------------------

def _top_income_sources(df: pd.DataFrame) -> pd.DataFrame:
    income = df[df.get("is_income", False)]
    if income.empty:
        return pd.DataFrame()

    grp = (
        income.groupby("merchant", dropna=False)
        .agg(total_amount=("amount", "sum"), count=("amount", "size"))
        .reset_index()
        .sort_values("total_amount", ascending=False)
        .head(5)
    )

    grp["amount_fmt"] = grp["total_amount"].apply(format_currency)
    return grp


def _top_expenses(df: pd.DataFrame) -> pd.DataFrame:
    expenses = df[df.get("is_expense", False)]
    if expenses.empty:
        return pd.DataFrame()

    grp = (
        expenses.groupby("merchant", dropna=False)
        .agg(total_amount=("amount", "sum"), count=("amount", "size"))
        .reset_index()
        .sort_values("total_amount")
        .head(5)
    )

    grp["amount_fmt"] = grp["total_amount"].apply(format_currency)
    return grp


def _most_frequent_expenses(df: pd.DataFrame) -> pd.DataFrame:
    expenses = df[df.get("is_expense", False)]
    if expenses.empty:
        return pd.DataFrame()

    grp = (
        expenses.groupby("merchant", dropna=False)
        .agg(
            count=("amount", "size"),
            total_amount=("amount", "sum"),
        )
        .reset_index()
        .sort_values("count", ascending=False)
        .head(5)
    )

    grp["amount_fmt"] = grp["total_amount"].apply(format_currency)
    return grp


# =====================================================
# UI
# =====================================================

def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str] | None = None,
    date_range: tuple[date, date] | None = None,
) -> None:
    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    scoped_tx = _coerce_df(transactions)
    derived_range = _derive_date_range(scoped_tx)

    if derived_range:
        st.caption("Date Range")
        st.caption(format_date_range(derived_range))

    if scoped_tx.empty or "amount" not in scoped_tx.columns:
        st.info("No transactions in scope.")
        return

    # =================================================
    # Snapshot Metrics
    # =================================================
    result = compute_cash_flow(scoped_tx)

    st.markdown("### Snapshot")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Income", format_currency(result.income))
    with c2:
        st.metric("Expenses", format_currency(result.net_expenses))
    with c3:
        st.metric("Net Cash Flow", format_currency(result.net_cash))

    # =================================================
    # Snapshot Details (PR-4)
    # =================================================
    st.markdown("### Snapshot Details")

    d1, d2, d3 = st.columns(3)

    top_income = _top_income_sources(scoped_tx)
    top_expenses = _top_expenses(scoped_tx)
    freq_expenses = _most_frequent_expenses(scoped_tx)

    with d1:
        st.markdown("**Top Income Sources**")
        if top_income.empty:
            st.caption("No income in range.")
        else:
            chart = (
                alt.Chart(top_income)
                .mark_bar()
                .encode(
                    y=alt.Y("merchant:N", sort="-x", title=None),
                    x=alt.X("total_amount:Q", title="Income"),
                    tooltip=[
                        alt.Tooltip("merchant:N"),
                        alt.Tooltip("amount_fmt:N", title="Total"),
                        alt.Tooltip("count:Q", title="Transactions"),
                    ],
                )
                .properties(height=220)
            )
            st.altair_chart(chart, use_container_width=True)

    with d2:
        st.markdown("**Top Expenses**")
        if top_expenses.empty:
            st.caption("No expenses in range.")
        else:
            chart = (
                alt.Chart(top_expenses)
                .mark_bar()
                .encode(
                    y=alt.Y("merchant:N", sort="x", title=None),
                    x=alt.X("total_amount:Q", title="Expense"),
                    tooltip=[
                        alt.Tooltip("merchant:N"),
                        alt.Tooltip("amount_fmt:N", title="Total"),
                        alt.Tooltip("count:Q", title="Transactions"),
                    ],
                )
                .properties(height=220)
            )
            st.altair_chart(chart, use_container_width=True)

    with d3:
        st.markdown("**Most Frequent Expenses**")
        if freq_expenses.empty:
            st.caption("No expenses in range.")
        else:
            chart = (
                alt.Chart(freq_expenses)
                .mark_bar()
                .encode(
                    y=alt.Y("merchant:N", sort="-x", title=None),
                    x=alt.X("count:Q", title="Occurrences"),
                    tooltip=[
                        alt.Tooltip("merchant:N"),
                        alt.Tooltip("count:Q", title="Count"),
                        alt.Tooltip("amount_fmt:N", title="Total Spend"),
                    ],
                )
                .properties(height=220)
            )
            st.altair_chart(chart, use_container_width=True)

    # =================================================
    # Cash Flow Charts (Canonical)
    # =================================================
    monthly_long = _monthly_cash_flow_frame(scoped_tx)

    if not monthly_long.empty:
        st.markdown("### Cash Flow Charts (Canonical)")

        show_net = st.toggle("Show Net Cash line overlay", value=True)

        bars = monthly_long[
            monthly_long["metric"].isin(["Income", "Net Expenses"])
        ]

        bar_chart = (
            alt.Chart(bars)
            .mark_bar()
            .encode(
                x=alt.X("month_start:T", title="Month"),
                xOffset="metric:N",
                y=alt.Y("value:Q", title="Amount"),
                tooltip=[
                    alt.Tooltip("month_start:T", title="Month"),
                    alt.Tooltip("metric:N", title="Metric"),
                    alt.Tooltip("value_fmt:N", title="Amount"),
                ],
            )
            .properties(height=280)
        )

        if show_net:
            net_line = (
                alt.Chart(monthly_long[monthly_long["metric"] == "Net Cash"])
                .mark_line(point=True)
                .encode(
                    x="month_start:T",
                    y="value:Q",
                    tooltip=[
                        alt.Tooltip("month_start:T", title="Month"),
                        alt.Tooltip("value_fmt:N", title="Net Cash"),
                    ],
                )
            )
            st.altair_chart(bar_chart + net_line, use_container_width=True)
        else:
            st.altair_chart(bar_chart, use_container_width=True)

    # =================================================
    # Rolling Net Cash Trend
    # =================================================
    st.markdown("### Net Cash Trend (Rolling Smoothing)")

    monthly = _monthly_net_cash_frame(scoped_tx)
    if not monthly.empty and len(monthly) > 1:
        monthly["roll_3"] = _apply_rolling(monthly, 3)
        monthly["roll_6"] = _apply_rolling(monthly, 6)

        base = alt.Chart(monthly).encode(
            x=alt.X("month_start:T", title="Month")
        )

        bars = base.mark_bar(opacity=0.35).encode(
            y=alt.Y("net_cash:Q", title="Net Cash"),
            tooltip=[
                alt.Tooltip("month_start:T", title="Month"),
                alt.Tooltip("net_cash_fmt:N", title="Net Cash"),
            ],
        )

        line_3 = base.mark_line(point=True).encode(
            y=alt.Y("roll_3:Q", title="Rolling Avg"),
            tooltip=[alt.Tooltip("roll_3:Q", title="3-Month Avg")],
        )

        line_6 = base.mark_line(strokeDash=[6, 3]).encode(
            y="roll_6:Q",
            tooltip=[alt.Tooltip("roll_6:Q", title="6-Month Avg")],
        )

        st.altair_chart(bars + line_3 + line_6, use_container_width=True)

    # =================================================
    # Category Contribution
    # =================================================
    st.markdown("### Category Contribution (Net Impact)")

    contrib = (
        scoped_tx.groupby("category", dropna=False)
        .apply(lambda g: compute_cash_flow(g).net_cash)
        .reset_index(name="net_cash")
        .sort_values("net_cash")
    )
    contrib["net_cash_fmt"] = contrib["net_cash"].apply(format_currency)

    if not contrib.empty:
        chart = (
            alt.Chart(contrib)
            .mark_bar()
            .encode(
                y=alt.Y("category:N", sort=alt.SortField("net_cash")),
                x=alt.X("net_cash:Q", title="Net Cash Impact"),
                tooltip=[
                    alt.Tooltip("category:N", title="Category"),
                    alt.Tooltip("net_cash_fmt:N", title="Net Impact"),
                ],
            )
            .properties(height=350)
        )
        st.altair_chart(chart, use_container_width=True)

    # =================================================
    # Category Volatility
    # =================================================
    st.markdown("### Category Volatility (Monthly Net)")

    volatility = _category_volatility_frame(scoped_tx)

    if not volatility.empty:
        vol_chart = (
            alt.Chart(volatility)
            .mark_bar()
            .encode(
                y=alt.Y(
                    "category:N",
                    sort=alt.SortField("volatility", order="descending"),
                    title="Category",
                ),
                x=alt.X("volatility:Q", title="Volatility (Std Dev)"),
                tooltip=[
                    alt.Tooltip("category:N"),
                    alt.Tooltip("volatility_fmt:N", title="Volatility"),
                    alt.Tooltip("avg_net_fmt:N", title="Avg Monthly Net"),
                    alt.Tooltip("months:Q", title="Months"),
                ],
            )
            .properties(height=350)
        )

        st.altair_chart(vol_chart, use_container_width=True)

    # =================================================
    # Exclusions Audit
    # =================================================
    mask = build_exclusion_mask(scoped_tx)
    excluded_amounts = (
        pd.to_numeric(scoped_tx.loc[mask, "amount"], errors="coerce")
        .fillna(0.0)
    )

    st.markdown(f"**Excluded totals:** {format_currency(excluded_amounts.sum())}")

    with st.expander("Show excluded rows (audit)", expanded=False):
        cols = [c for c in ["date", "merchant", "category", "amount"] if c in scoped_tx.columns]
        st.dataframe(scoped_tx.loc[mask, cols], use_container_width=True)

    st.caption(
        f"Expense offsets: {format_currency(result.expense_offsets)} | "
        f"Gross expenses: {format_currency(result.gross_expenses)}"
    )

