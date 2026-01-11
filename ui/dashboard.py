import streamlit as st
import pandas as pd
from datetime import date

from src.formatting import format_currency, format_date_range
from src.cash_flow import calculate_cash_flow


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

            if scoped_tx.empty:
                st.info("No transactions in scope.")
                continue

            result = calculate_cash_flow(scoped_tx)

            st.markdown("### Key Metrics (Core Cash Flow)")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Income", format_currency(result["income"]))
            with c2:
                st.metric("Expenses", format_currency(result["expenses"]))
            with c3:
                st.metric("Net", format_currency(result["net"]))

            st.caption(
                f"Audit: Included rows = {result['included_rows']} | "
                f"Excluded rows = {result['excluded_rows']} | "
                "Category-driven exclusions"
            )

            st.markdown(
                f"**Excluded totals:** "
                f"{format_currency(abs(result['excluded_total']))} "
                f"(+{format_currency(result['excluded_positive'])} / "
                f"{format_currency(result['excluded_negative'])})"
            )

            with st.expander("Show excluded rows (audit)", expanded=False):
                cols = [
                    c for c in
                    ["date", "merchant", "category", "amount"]
                    if c in scoped_tx.columns
                ]
                st.dataframe(
                    scoped_tx.loc[result["exclusion_mask"], cols],
                    use_container_width=True
                )

