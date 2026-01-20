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
# UI
# -----------------------------

def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
    date_range: tuple[date, date] | None = None,
) -> None:
    st.markdown("## Dashboard (Core Rebuild)")
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
            # Rolling Net Cash Trend
            # -----------------------------
            st.markdown("### Net Cash Trend (Rolling Smoothing)")

            monthly = _monthly_net_cash_frame(scoped_tx)
            if monthly.empty or len(monthly) < 2:
                st.info("Not enough monthly data for rolling analysis.")
            else:
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

                line_3 = base.mark_line(color="#1f77b4", point=True).encode(
                    y=alt.Y("roll_3:Q", title="Rolling Avg"),
                    tooltip=[alt.Tooltip("roll_3:Q", title="3-Month Avg")],
                )

                line_6 = base.mark_line(color="#ff7f0e", strokeDash=[6, 3]).encode(
                    y=alt.Y("roll_6:Q"),
                    tooltip=[alt.Tooltip("roll_6:Q", title="6-Month Avg")],
                )

                st.altair_chart(
                    bars + line_3 + line_6,
                    use_container_width=True,
                )

                st.caption(
                    "Interpretation: Rolling averages smooth short-term volatility to reveal "
                    "underlying cash flow trends."
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














