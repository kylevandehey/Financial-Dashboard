import streamlit as st
import pandas as pd
from datetime import date
import altair as alt

from src.formatting import format_currency, format_date_range
from src.cash_flow import (
    compute_cash_flow,
    build_exclusion_mask,
)

# ======================================================
# Helpers
# ======================================================

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


def _safe_cols(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


# ======================================================
# Monthly aggregation (CANONICAL)
# ======================================================

def _monthly_cash_flow_frames(scoped_tx: pd.DataFrame):
    if scoped_tx.empty or "amount" not in scoped_tx.columns or "date" not in scoped_tx.columns:
        return pd.DataFrame(), pd.DataFrame()

    df = scoped_tx.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    df["month_start"] = df["date"].dt.to_period("M").dt.to_timestamp()

    rows = []
    for month, g in df.groupby("month_start"):
        result = compute_cash_flow(g)
        rows.extend(
            [
                {"month_start": month, "metric": "Income", "value": result.income},
                {"month_start": month, "metric": "Net Expenses", "value": result.net_expenses},
                {"month_start": month, "metric": "Net Cash", "value": result.net_cash},
            ]
        )

    long_df = pd.DataFrame(rows)
    long_df["value_fmt"] = long_df["value"].apply(format_currency)

    return long_df


# ======================================================
# Charts (CANONICAL + SAFE KEYS)
# ======================================================

def _render_monthly_cash_flow_charts(
    scoped_tx: pd.DataFrame,
    *,
    year_label: str,
) -> None:
    grouped_long = _monthly_cash_flow_frames(scoped_tx)

    if grouped_long.empty:
        st.info("Not enough data to render cash flow charts for this scope.")
        return

    st.markdown("### Cash Flow Charts (Canonical)")

    show_net_line = st.toggle(
        "Show Net Cash line overlay",
        value=True,
        help="Net Cash = Income - Net Expenses (derived from canonical logic).",
        key=f"cf_show_net_line_{year_label}",
    )

    bars_source = grouped_long[grouped_long["metric"].isin(["Income", "Net Expenses"])]

    bar_chart = (
        alt.Chart(bars_source)
        .mark_bar()
        .encode(
            x=alt.X("month_start:T", title="Month"),
            xOffset=alt.XOffset("metric:N"),
            y=alt.Y("value:Q", title="Amount"),
            tooltip=[
                alt.Tooltip("month_start:T", title="Month"),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value_fmt:N", title="Amount"),
            ],
        )
        .properties(height=280)
    )

    if show_net_line:
        net_source = grouped_long[grouped_long["metric"] == "Net Cash"]
        line_chart = (
            alt.Chart(net_source)
            .mark_line(point=True)
            .encode(
                x=alt.X("month_start:T"),
                y=alt.Y("value:Q"),
                tooltip=[
                    alt.Tooltip("month_start:T", title="Month"),
                    alt.Tooltip("value_fmt:N", title="Net Cash"),
                ],
            )
        )
        st.altair_chart(bar_chart + line_chart, use_container_width=True)
    else:
        st.altair_chart(bar_chart, use_container_width=True)

    st.divider()


# ======================================================
# Main Dashboard Renderer
# ======================================================

def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
    date_range: tuple[date, date] | None = None,  # intentionally ignored
) -> None:
    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")
    st.caption("Cash Flow Rules Source: config/cash_flow_rules.json")

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

            # ==================================================
            # Canonical engine
            # ==================================================

            result = compute_cash_flow(scoped_tx)

            st.markdown("### Key Metrics (Core Cash Flow)")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Income", format_currency(result.income))
            with c2:
                st.metric("Expenses", format_currency(result.net_expenses))
            with c3:
                st.metric("Net", format_currency(result.net_cash))

            st.caption(
                f"Audit: Included rows = {result.included_rows} | "
                f"Excluded rows = {result.excluded_rows} | "
                f"Category-driven exclusions"
            )

            # ==================================================
            # Charts
            # ==================================================

            _render_monthly_cash_flow_charts(
                scoped_tx,
                year_label=year_label,
            )

            # ==================================================
            # Exclusion Audit
            # ==================================================

            exclusion_mask = build_exclusion_mask(scoped_tx)
            excluded_amounts = (
                pd.to_numeric(scoped_tx.loc[exclusion_mask, "amount"], errors="coerce")
                .fillna(0.0)
            )

            excluded_net = float(excluded_amounts.sum())
            excluded_pos = float(excluded_amounts[excluded_amounts > 0].sum())
            excluded_neg_abs = float((-excluded_amounts[excluded_amounts < 0]).sum())

            st.markdown(
                f"**Excluded totals:** {format_currency(excluded_net)} "
                f"({format_currency(excluded_pos)} / {format_currency(-excluded_neg_abs)})"
            )

            with st.expander("Show excluded rows (audit)", expanded=False):
                cols = _safe_cols(scoped_tx, ["date", "merchant", "category", "notes", "amount"])
                st.dataframe(scoped_tx.loc[exclusion_mask, cols], use_container_width=True)

            st.caption(
                f"Expense offsets (positive non-income): {format_currency(result.expense_offsets)} | "
                f"Gross expenses: {format_currency(result.gross_expenses)}"
            )










