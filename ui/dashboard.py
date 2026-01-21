import streamlit as st
import pandas as pd
import altair as alt
from datetime import date

from src.formatting import format_currency, format_date_range
from src.cash_flow import compute_cash_flow, build_exclusion_mask


# -----------------------------
# Helpers
# -----------------------------

def _coerce_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    return pd.DataFrame(df).copy()


def _filter_by_year(df: pd.DataFrame, year_label: str) -> pd.DataFrame:
    if df.empty or year_label == "ALL YEARS":
        return df
    if "date" not in df.columns:
        return df
    try:
        year = int(year_label)
    except ValueError:
        return df
    dates = pd.to_datetime(df["date"], errors="coerce")
    return df.loc[dates.dt.year == year]


def _derive_date_range(df: pd.DataFrame) -> tuple[date, date] | None:
    if df.empty or "date" not in df.columns:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return dates.min().date(), dates.max().date()


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


def _category_monthly_net_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Monthly net cash impact per category using canonical cash flow.
    """
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
    """
    Volatility = standard deviation of monthly net cash per category.
    """
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
# UI
# -----------------------------

def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
    date_range: tuple[date, date] | None = None,
) -> None:
    st.markdown("## Dashboard (Core Rebuild)")

    # Ledger-style reset button placed at top of Dashboard UI
    reset_col_left, reset_col_right = st.columns([1, 6])
    with reset_col_left:
        if st.button("Reset Dashboard", key="reset_dashboard_btn"):
            st.session_state.clear()
            st.rerun()
    with reset_col_right:
        st.markdown("### Dashboard Overview")

    year_tabs = st.tabs(available_years)

    for tab, year_label in zip(year_tabs, available_years):
        with tab:
            scoped_tx = _filter_by_year(_coerce_df(transactions), year_label)
            derived_range = _derive_date_range(scoped_tx)

            st.caption(f"Scope: {year_label}")
            if derived_range:
                st.caption("Date Range")
                st.caption(format_date_range(derived_range))

            if scoped_tx.empty or "amount" not in scoped_tx.columns:
                st.info("No transactions in scope.")
                continue

            # -----------------------------
            # Canonical Cash Flow
            # -----------------------------
            result = compute_cash_flow(scoped_tx)

            st.markdown("### Key Metrics (Core Cash Flow)")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Income", format_currency(result.income))
            with c2:
                st.metric("Expenses", format_currency(result.net_expenses))
            with c3:
                st.metric("Net", format_currency(result.net_cash))

            # -----------------------------
            # Monthly Charts
            # -----------------------------
            monthly_long = _monthly_cash_flow_frame(scoped_tx)

            if not monthly_long.empty:
                st.markdown("### Cash Flow Charts (Canonical)")

                show_net = st.toggle(
                    "Show Net Cash line overlay",
                    value=True,
                    key=f"cf_net_toggle_{year_label}",
                )

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
                        alt.Chart(
                            monthly_long[monthly_long["metric"] == "Net Cash"]
                        )
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

            # -----------------------------
            # Category Contribution
            # -----------------------------
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

            # -----------------------------
            # Category Volatility
            # -----------------------------
            st.markdown("### Category Volatility (Monthly Net)")

            volatility = _category_volatility_frame(scoped_tx)

            if volatility.empty:
                st.info("Not enough data to compute volatility.")
            else:
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
                            alt.Tooltip("category:N", title="Category"),
                            alt.Tooltip("volatility_fmt:N", title="Volatility"),
                            alt.Tooltip("avg_net_fmt:N", title="Avg Monthly Net"),
                            alt.Tooltip("months:Q", title="Months Observed"),
                        ],
                    )
                    .properties(height=350)
                )

                st.altair_chart(vol_chart, use_container_width=True)

                with st.expander("Show category volatility table", expanded=False):
                    st.dataframe(
                        volatility[
                            ["category", "avg_net", "volatility", "months"]
                        ],
                        use_container_width=True,
                    )

            # -----------------------------
            # Exclusions Audit
            # -----------------------------
            mask = build_exclusion_mask(scoped_tx)
            excluded_amounts = (
                pd.to_numeric(scoped_tx.loc[mask, "amount"], errors="coerce")
                .fillna(0.0)
            )

            st.markdown(
                f"**Excluded totals:** {format_currency(excluded_amounts.sum())}"
            )

            with st.expander("Show excluded rows (audit)", expanded=False):
                cols = [c for c in ["date", "merchant", "category", "amount"] if c in scoped_tx.columns]
                st.dataframe(scoped_tx.loc[mask, cols], use_container_width=True)

            st.caption(
                f"Expense offsets: {format_currency(result.expense_offsets)} | "
                f"Gross expenses: {format_currency(result.gross_expenses)}"
            )
