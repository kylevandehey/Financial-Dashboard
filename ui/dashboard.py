import streamlit as st
import pandas as pd
from datetime import date

from src.formatting import format_currency, format_date_range


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


def _norm(s: object) -> str:
    return " ".join(str(s or "").lower().replace("_", " ").replace("-", " ").split())


def _first_present_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _build_exclusion_mask(df: pd.DataFrame, excluded: set[str]) -> tuple[pd.Series, str]:
    """
    Returns (mask, detection_source)

    Priority:
      1) transaction_type / type
      2) category
      3) keyword scan of text columns (merchant/notes/original_statement)
    """
    if df.empty:
        return pd.Series([], dtype=bool), "none"

    # 1) transaction_type / type
    type_col = _first_present_column(df, ["transaction_type", "type"])
    if type_col:
        series = df[type_col].apply(_norm)
        mask = series.apply(lambda v: any(v == ex or v.startswith(f"{ex} ") for ex in excluded))
        return mask.fillna(False), type_col

    # 2) category fallback (this matches what your spreadsheet screenshot shows)
    cat_col = _first_present_column(df, ["category", "Category"])
    if cat_col:
        series = df[cat_col].apply(_norm)
        mask = series.apply(lambda v: any(v == ex or v.startswith(f"{ex} ") for ex in excluded))
        return mask.fillna(False), cat_col

    # 3) keyword scan fallback (last resort)
    scan_cols = [c for c in ["merchant", "notes", "original_statement"] if c in df.columns]
    if scan_cols:
        haystack = (
            df[scan_cols]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .apply(_norm)
        )
        mask = haystack.apply(lambda txt: any(ex in txt for ex in excluded))
        return mask.fillna(False), "keyword_scan"

    return pd.Series([False] * len(df.index), index=df.index), "none"


def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
) -> None:
    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    # Keep exclusions narrow and explicit for now
    excluded_types = {"transfer", "credit card payment", "refund"}

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

            amounts = pd.to_numeric(scoped_tx["amount"], errors="coerce").fillna(0.0)

            mask_excluded, source = _build_exclusion_mask(scoped_tx, excluded_types)
            included_amounts = amounts.loc[~mask_excluded]

            positive = included_amounts[included_amounts > 0]
            negative = included_amounts[included_amounts < 0]

            income = float(positive.sum())
            expenses = float((-negative).sum())
            net = float(income - expenses)

            st.markdown("### Key Metrics (Core Cash Flow v1)")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Income", format_currency(income))
            with c2:
                st.metric("Expenses", format_currency(expenses))
            with c3:
                st.metric("Net", format_currency(net))

            # --- Audit ---
            raw_positive = int((amounts > 0).sum())
            raw_negative = int((amounts < 0).sum())
            excl_count = int(mask_excluded.sum())

            st.caption(
                f"Audit (v1): Raw + rows: {raw_positive} | Raw - rows: {raw_negative} | "
                f"Excluded rows: {excl_count} | Detection source: {source}"
            )

            if excl_count > 0:
                # Show what got excluded so we can confirm correctness quickly
                preview_cols = [c for c in ["date", "merchant", "category", "transaction_type", "type", "amount", "notes", "original_statement"] if c in scoped_tx.columns]
                excluded_df = scoped_tx.loc[mask_excluded, preview_cols].copy()
                with st.expander("Show excluded transactions (temporary audit)", expanded=False):
                    st.dataframe(excluded_df, use_container_width=True)




