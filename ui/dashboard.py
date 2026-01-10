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


def _normalize_type_value(raw_type: object) -> str:
    normalized = str(raw_type or "").lower().replace("_", " ").replace("-", " ")
    return " ".join(normalized.split())


def _type_series(df: pd.DataFrame) -> pd.Series:
    """
    Best-effort transaction type extraction.
    We prefer 'transaction_type' but fallback to 'type' if present.
    """
    if "transaction_type" in df.columns:
        return df["transaction_type"].apply(_normalize_type_value)
    if "type" in df.columns:
        return df["type"].apply(_normalize_type_value)
    return pd.Series([""] * len(df.index), index=df.index)


def _excluded_mask(df: pd.DataFrame, excluded_types: set[str]) -> pd.Series:
    """
    Exclude rows whose normalized transaction_type equals (or starts with) an excluded token.
    Examples handled:
      - "credit card payment"
      - "credit card payment - autopay"
    """
    types = _type_series(df)
    if types.empty:
        return pd.Series([False] * len(df.index), index=df.index)

    def _is_excluded(value: str) -> bool:
        if not value:
            return False
        for ex in excluded_types:
            if value == ex or value.startswith(f"{ex} "):
                return True
        return False

    return types.apply(_is_excluded)


def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
) -> None:
    """
    Core rebuild dashboard (Cash Flow v1).

    Business definition (v1):
    - Income = sum(amount > 0) excluding Transfers / Credit Card Payments / Refunds
    - Expenses = sum(abs(amount < 0)) excluding Transfers / Credit Card Payments / Refunds
    - Net = Income - Expenses

    This matches your expectation that:
    - Transfers and CC Payments should NOT distort cash flow
    """

    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    year_tabs = st.tabs(available_years)

    # v1 exclusions (expand later if needed)
    excluded_types = {
        "transfer",
        "credit card payment",
        "refund",
    }

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

            # Exclude transfers/cc/refunds from BOTH income and expenses
            mask_excluded = _excluded_mask(scoped_tx, excluded_types)
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

            # --- Audit (temporary but extremely useful) ---
            raw_positive = int((amounts > 0).sum())
            raw_negative = int((amounts < 0).sum())
            excl_count = int(mask_excluded.sum())

            types_found = _type_series(scoped_tx)
            excluded_breakdown = (
                scoped_tx.loc[mask_excluded]
                .assign(_tx_type=types_found.loc[mask_excluded])
                .groupby("_tx_type")["amount"]
                .agg(["count", "sum"])
                .sort_values("count", ascending=False)
                .reset_index()
            )

            st.caption(
                "Audit (v1): "
                f"Raw + rows: {raw_positive} | Raw - rows: {raw_negative} | "
                f"Excluded rows: {excl_count}"
            )

            if excl_count > 0:
                with st.expander("Show excluded rows breakdown (temporary audit)", expanded=False):
                    st.dataframe(excluded_breakdown, use_container_width=True)



