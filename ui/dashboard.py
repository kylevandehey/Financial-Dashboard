import streamlit as st
import pandas as pd
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


def _monthly_net_cash_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a DataFrame with:
        month_start | net_cash
    Computed strictly via canonical cash flow.
    """
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["month_start"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()

    rows = []
    for month, month_df in df.groupby("month_start"):
        result = compute_cash_flow(month_df)
        rows.append(
            {
                "month_start": month,
                "net_cash": result.net_cash,
            }
        )

    return pd.DataFrame(rows).sort_values("month_start")


# -----------------------------
# UI
# -----------------------------

def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
    date_range: tuple[date, date] | None = None,  # intentionally ignored
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

            st.caption(
                f"Audit: Included rows = {result.included_rows} | "
                f"Excluded rows = {result.excluded_rows} | "
                f"Category-driven exclusions"
            )

            # -----------------------------
            # NEW: Monthly Net Cash Trend
            # -----------------------------
            monthly = _monthly_net_cash_series(scoped_tx)

            if len(monthly) >= 2:
                latest = monthly.iloc[-1]
                prior = monthly.iloc[-2]

                delta = latest["net_cash"] - prior["net_cash"]
                pct = (
                    (delta / abs(prior["net_cash"])) * 100
                    if prior["net_cash"] != 0
                    else None
                )

                st.markdown("### Net Cash Trend (Month-over-Month)")

                t1, t2, t3 = st.columns(3)
                with t1:
                    st.metric(
                        "Latest Month",
                        format_currency(latest["net_cash"]),
                    )
                with t2:
                    st.metric(
                        "Prior Month",
                        format_currency(prior["net_cash"]),
                    )
                with t3:
                    st.metric(
                        "MoM Change",
                        format_currency(delta),
                        f"{pct:.1f}%" if pct is not None else "—",
                    )

            elif len(monthly) == 1:
                st.markdown("### Net Cash Trend")
                st.info(
                    "Only one month of data available. "
                    "Month-over-month trend will appear once additional data exists."
                )

            # -----------------------------
            # Excluded totals (audit)
            # -----------------------------
            mask = build_exclusion_mask(scoped_tx)
            excluded_amounts = (
                pd.to_numeric(scoped_tx.loc[mask, "amount"], errors="coerce")
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
                cols = [c for c in ["date", "merchant", "category", "amount"] if c in scoped_tx.columns]
                st.dataframe(scoped_tx.loc[mask, cols], use_container_width=True)

            st.caption(
                f"Expense offsets (positive non-income): {format_currency(result.expense_offsets)} | "
                f"Gross expenses: {format_currency(result.gross_expenses)}"
            )











