import streamlit as st
import pandas as pd
from datetime import date

from src.formatting import format_currency, format_date_range
from src.cash_flow import compute_cash_flow


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


def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
    date_range: tuple[date, date] | None = None,  # intentionally ignored (derived per tab)
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

            # Totals line above expander (requested)
            excluded_total = float(
                pd.to_numeric(scoped_tx["amount"], errors="coerce")
                .fillna(0.0)
                .loc[~pd.Series([True] * len(scoped_tx), index=scoped_tx.index)]  # placeholder; replaced below
                .sum()
            )

            # Build excluded rows for display + totals (without duplicating logic elsewhere)
            # We rely on compute_cash_flow's exclusion behavior by recomputing mask through the engine file.
            from src.cash_flow import build_exclusion_mask

            mask = build_exclusion_mask(scoped_tx)
            excluded_amounts = pd.to_numeric(scoped_tx.loc[mask, "amount"], errors="coerce").fillna(0.0)
            excluded_net = float(excluded_amounts.sum())
            excluded_pos = float(excluded_amounts[excluded_amounts > 0].sum())
            excluded_neg = float((-excluded_amounts[excluded_amounts < 0]).sum())

            st.markdown(
                f"**Excluded totals:** {format_currency(excluded_net)} "
                f"({format_currency(excluded_pos)} / {format_currency(-excluded_neg)})"
            )

            with st.expander("Show excluded rows (audit)", expanded=False):
                cols = [c for c in ["date", "merchant", "category", "amount"] if c in scoped_tx.columns]
                st.dataframe(scoped_tx.loc[mask, cols], use_container_width=True)

            # Optional: show offsets transparency (useful for coaching users)
            st.caption(
                f"Expense offsets (positive non-income): {format_currency(result.expense_offsets)} | "
                f"Gross expenses: {format_currency(result.gross_expenses)}"
            )


