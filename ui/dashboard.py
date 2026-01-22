# ui/dashboard.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from src.cash_flow import compute_cash_flow, build_exclusion_mask
from src.formatting import format_currency, format_date_range


# =============================
# Session State Keys
# =============================
_SS_DATASET_SIG = "dash_dataset_signature_v1"

_SS_PRESET = "dash_date_preset_v1"
_SS_CUSTOM_START = "dash_custom_start_v1"
_SS_CUSTOM_END = "dash_custom_end_v1"

_SS_EXCL_INCOME = "dash_exclude_income_categories_v1"
_SS_EXCL_EXPENSE = "dash_exclude_expense_categories_v1"
_SS_EXCL_FREQ = "dash_exclude_frequency_categories_v1"


# =============================
# Defaults
# =============================
DEFAULT_EXCLUDE_KEYWORDS = (
    "transfer",
    "credit card",
    "creditcard",
    "cc payment",
    "card payment",
    "payment",
)


# =============================
# Helpers
# =============================
def _coerce_df(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    return pd.DataFrame(df).copy()


def _ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "date" not in df.columns:
        return df
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    return out.dropna(subset=["date"])


def _dataset_signature(tx: pd.DataFrame) -> str:
    """
    Lightweight fingerprint so we can reset defaults when the user uploads a new CSV.
    """
    tx = _ensure_datetime(_coerce_df(tx))
    if tx.empty:
        return "empty"

    n = int(len(tx))
    min_d = tx["date"].min()
    max_d = tx["date"].max()
    amt = pd.to_numeric(tx.get("amount", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    amt_sum = float(amt.sum())
    amt_abs_sum = float(amt.abs().sum())

    return f"n={n}|min={min_d.date().isoformat()}|max={max_d.date().isoformat()}|sum={amt_sum:.2f}|abs={amt_abs_sum:.2f}"


def _infer_default_excludes(categories: List[str]) -> List[str]:
    """
    Pre-select likely 'system' categories (transfer + CC payment) if present.
    """
    out = []
    for c in categories:
        lc = str(c or "").strip().lower()
        if any(k in lc for k in DEFAULT_EXCLUDE_KEYWORDS):
            out.append(c)
    # Keep it deterministic
    return sorted(set(out), key=lambda x: str(x).lower())


def _init_exclusion_state_if_needed(tx: pd.DataFrame) -> None:
    """
    Initialize (or reset) exclusion lists ONLY when a new dataset is detected.
    """
    sig = _dataset_signature(tx)
    if st.session_state.get(_SS_DATASET_SIG) != sig:
        # New dataset detected -> reset to defaults
        tx = _ensure_datetime(_coerce_df(tx))
        cats = sorted(set([c for c in tx.get("category", pd.Series(dtype=str)).fillna("").astype(str).tolist() if c.strip()]))
        defaults = _infer_default_excludes(cats)

        st.session_state[_SS_DATASET_SIG] = sig
        st.session_state[_SS_EXCL_INCOME] = defaults.copy()
        st.session_state[_SS_EXCL_EXPENSE] = defaults.copy()
        st.session_state[_SS_EXCL_FREQ] = defaults.copy()

        # Date preset defaults
        if _SS_PRESET not in st.session_state:
            st.session_state[_SS_PRESET] = "ALL YEARS"


def _derive_full_range(tx: pd.DataFrame) -> Optional[Tuple[date, date]]:
    tx = _ensure_datetime(_coerce_df(tx))
    if tx.empty:
        return None
    return tx["date"].min().date(), tx["date"].max().date()


def _available_years(tx: pd.DataFrame) -> List[int]:
    tx = _ensure_datetime(_coerce_df(tx))
    if tx.empty:
        return []
    years = sorted(tx["date"].dt.year.dropna().astype(int).unique().tolist())
    return years


def _last_full_year_range(ref: date) -> Tuple[date, date]:
    year = ref.year - 1
    return date(year, 1, 1), date(year, 12, 31)


def _clip_range_to_data(
    start: date,
    end: date,
    data_min: date,
    data_max: date,
) -> Tuple[date, date]:
    s = max(start, data_min)
    e = min(end, data_max)
    if e < s:
        return data_min, data_max
    return s, e


def _filter_by_date(tx: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    tx = _ensure_datetime(_coerce_df(tx))
    if tx.empty:
        return tx
    mask = (tx["date"].dt.date >= start) & (tx["date"].dt.date <= end)
    return tx.loc[mask].copy()


def _top_n_categories_by_amount(
    df: pd.DataFrame,
    n: int,
    *,
    positive_only: bool = False,
    negative_only: bool = False,
) -> List[str]:
    if df.empty or "category" not in df.columns or "amount" not in df.columns:
        return []
    tmp = df.copy()
    tmp["amount"] = pd.to_numeric(tmp["amount"], errors="coerce").fillna(0.0)

    if positive_only:
        tmp = tmp.loc[tmp["amount"] > 0]
    if negative_only:
        tmp = tmp.loc[tmp["amount"] < 0]

    if tmp.empty:
        return []

    agg = (
        tmp.groupby("category", dropna=False)["amount"]
        .sum()
        .reset_index()
    )
    # Use abs magnitude to rank consistently for negative-only selections
    agg["rank_value"] = agg["amount"].abs()
    agg = agg.sort_values("rank_value", ascending=False).head(n)
    return [str(c or "(Uncategorized)") for c in agg["category"].tolist()]


def _safe_category_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).replace({"": "(Uncategorized)"})


# =============================
# Date Controls (Ledger-style)
# =============================
@dataclass
class DateControlResult:
    filtered_tx: pd.DataFrame
    start_date: date
    end_date: date
    label: str


def _render_date_controls(tx: pd.DataFrame) -> DateControlResult:
    """
    Single dropdown that includes:
    - Last 7/30/90/180 days
    - Last Full Year
    - ALL YEARS
    - Each full year present in CSV
    - Custom Range (start/end)
    """
    tx = _ensure_datetime(_coerce_df(tx))
    full_range = _derive_full_range(tx)
    if not full_range:
        # fallback
        today = datetime.now().date()
        return DateControlResult(tx, today, today, "No data")

    data_min, data_max = full_range

    years = _available_years(tx)
    year_labels = [str(y) for y in years]

    preset_options = [
        "Last 7 Days",
        "Last 30 Days",
        "Last 90 Days",
        "Last 180 Days",
        "Last Full Year",
        "ALL YEARS",
    ] + year_labels + [
        "Custom Range",
    ]

    st.markdown("### Date Range Presets")

    # Initialize preset default if missing
    if _SS_PRESET not in st.session_state:
        st.session_state[_SS_PRESET] = "ALL YEARS"

    selected = st.selectbox(
        "Date Range Presets",
        preset_options,
        index=preset_options.index(st.session_state[_SS_PRESET]) if st.session_state[_SS_PRESET] in preset_options else preset_options.index("ALL YEARS"),
        key=_SS_PRESET,
        label_visibility="visible",
    )

    # Resolve selection -> (start, end)
    today = datetime.now().date()

    if selected == "Last 7 Days":
        start, end = today - timedelta(days=6), today
        label = "Last 7 Days"
    elif selected == "Last 30 Days":
        start, end = today - timedelta(days=29), today
        label = "Last 30 Days"
    elif selected == "Last 90 Days":
        start, end = today - timedelta(days=89), today
        label = "Last 90 Days"
    elif selected == "Last 180 Days":
        start, end = today - timedelta(days=179), today
        label = "Last 180 Days"
    elif selected == "Last Full Year":
        start, end = _last_full_year_range(today)
        label = f"Last Full Year ({start.year})"
    elif selected == "Custom Range":
        # Defaults
        if _SS_CUSTOM_START not in st.session_state:
            st.session_state[_SS_CUSTOM_START] = data_min
        if _SS_CUSTOM_END not in st.session_state:
            st.session_state[_SS_CUSTOM_END] = data_max

        st.markdown("### Custom Date Range")
        c1, c2 = st.columns(2)
        with c1:
            start = st.date_input(
                "Start date",
                value=st.session_state[_SS_CUSTOM_START],
                min_value=data_min,
                max_value=data_max,
                key=_SS_CUSTOM_START,
            )
        with c2:
            end = st.date_input(
                "End date",
                value=st.session_state[_SS_CUSTOM_END],
                min_value=data_min,
                max_value=data_max,
                key=_SS_CUSTOM_END,
            )

        # Normalize if user flips
        if end < start:
            end = start

        label = "Custom Range"
    elif selected in year_labels:
        y = int(selected)
        start, end = date(y, 1, 1), date(y, 12, 31)
        label = str(y)
    else:
        # ALL YEARS
        start, end = data_min, data_max
        label = "ALL YEARS"

    # Clip to available data
    start, end = _clip_range_to_data(start, end, data_min, data_max)
    filtered = _filter_by_date(tx, start, end)

    st.caption("Date Range")
    st.caption(format_date_range((start, end)))

    return DateControlResult(filtered, start, end, label)


# =============================
# Charts (Snapshot Details)
# =============================
def _build_income_top_frame(scoped_tx: pd.DataFrame, excluded_categories: List[str], top_n: int = 10) -> pd.DataFrame:
    if scoped_tx.empty or "amount" not in scoped_tx.columns:
        return pd.DataFrame()

    df = scoped_tx.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["category"] = _safe_category_text(df.get("category", pd.Series(dtype=str)))

    # Canonical income rows only
    if "is_income" in df.columns:
        df = df.loc[df["is_income"] == True]  # noqa: E712
    else:
        df = df.loc[df["amount"] > 0]

    if excluded_categories:
        df = df.loc[~df["category"].isin(excluded_categories)]

    if df.empty:
        return pd.DataFrame()

    agg = df.groupby("category")["amount"].sum().reset_index()
    agg = agg.sort_values("amount", ascending=False).head(top_n)
    agg["amount_fmt"] = agg["amount"].apply(format_currency)
    return agg


def _build_expense_top_frame(scoped_tx: pd.DataFrame, excluded_categories: List[str], top_n: int = 10) -> pd.DataFrame:
    if scoped_tx.empty or "amount" not in scoped_tx.columns:
        return pd.DataFrame()

    df = scoped_tx.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["category"] = _safe_category_text(df.get("category", pd.Series(dtype=str)))

    # Canonical expense rows only
    if "is_expense" in df.columns:
        df = df.loc[df["is_expense"] == True]  # noqa: E712
    else:
        df = df.loc[df["amount"] < 0]

    if excluded_categories:
        df = df.loc[~df["category"].isin(excluded_categories)]

    if df.empty:
        return pd.DataFrame()

    # Spend as positive magnitude
    df["spend"] = (-df["amount"]).clip(lower=0.0)
    agg = df.groupby("category")["spend"].sum().reset_index()
    agg = agg.sort_values("spend", ascending=False).head(top_n)
    agg["spend_fmt"] = agg["spend"].apply(format_currency)
    return agg


def _build_expense_frequency_frame(scoped_tx: pd.DataFrame, excluded_categories: List[str], top_n: int = 10) -> pd.DataFrame:
    if scoped_tx.empty or "amount" not in scoped_tx.columns:
        return pd.DataFrame()

    df = scoped_tx.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["category"] = _safe_category_text(df.get("category", pd.Series(dtype=str)))

    # Expense-like rows for frequency
    if "is_expense" in df.columns:
        df = df.loc[df["is_expense"] == True]  # noqa: E712
    else:
        df = df.loc[df["amount"] < 0]

    if excluded_categories:
        df = df.loc[~df["category"].isin(excluded_categories)]

    if df.empty:
        return pd.DataFrame()

    df["spend"] = (-df["amount"]).clip(lower=0.0)

    agg = (
        df.groupby("category")
        .agg(
            occurrences=("category", "count"),
            total_spend=("spend", "sum"),
        )
        .reset_index()
    )

    agg = agg.sort_values(["occurrences", "total_spend"], ascending=[False, False]).head(top_n)
    agg["total_spend_fmt"] = agg["total_spend"].apply(format_currency)
    return agg


def _alt_hbar_top_income(df: pd.DataFrame) -> alt.Chart:
    # Vertical bars, sorted high->low, $ axis formatting
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("category:N", sort=alt.SortField(field="amount", order="descending"), title="Category"),
            y=alt.Y("amount:Q", title="Income", axis=alt.Axis(format="$,.0f")),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("amount_fmt:N", title="Income"),
            ],
        )
        .properties(height=260)
    )


def _alt_hbar_top_expenses(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("category:N", sort=alt.SortField(field="spend", order="descending"), title="Category"),
            y=alt.Y("spend:Q", title="Expense", axis=alt.Axis(format="$,.0f")),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("spend_fmt:N", title="Expense"),
            ],
        )
        .properties(height=260)
    )


def _alt_hbar_frequency(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("category:N", sort=alt.SortField(field="occurrences", order="descending"), title="Category"),
            y=alt.Y("occurrences:Q", title="Occurrences", axis=alt.Axis(format=",.0f")),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("occurrences:Q", title="Occurrences", format=",.0f"),
                alt.Tooltip("total_spend_fmt:N", title="Total Spend"),
            ],
        )
        .properties(height=260)
    )


def _build_multiselect_options(top_categories: List[str], tx_all_categories: List[str]) -> List[str]:
    """
    Dashboard dropdown should be concise:
    - Top 10 (for that chart)
    - Plus default excludes if they exist
    - Use all_categories to ensure the defaults remain selectable
    """
    defaults = _infer_default_excludes(tx_all_categories)
    merged = []
    for c in (top_categories + defaults):
        if c and c not in merged:
            merged.append(c)
    return merged


# =============================
# UI
# =============================
def render_dashboard_tab(
    transactions: pd.DataFrame,
) -> None:
    tx = _ensure_datetime(_coerce_df(transactions))
    _init_exclusion_state_if_needed(tx)

    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    if tx.empty or "amount" not in tx.columns:
        st.info("No transactions loaded.")
        return

    # -----------------------------
    # Date Controls (Ledger-style)
    # -----------------------------
    dc = _render_date_controls(tx)
    scoped_tx = dc.filtered_tx

    # -----------------------------
    # Snapshot (Canonical Cash Flow)
    # -----------------------------
    result = compute_cash_flow(scoped_tx)

    st.markdown("## Snapshot")
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Income", format_currency(result.income))
    with k2:
        st.metric("Expenses", format_currency(result.net_expenses))
    with k3:
        st.metric("Net Cash Flow", format_currency(result.net_cash))

    # -----------------------------
    # Snapshot Details
    # -----------------------------
    st.markdown("## Snapshot Details")

    all_categories_full = sorted(
        set(_safe_category_text(scoped_tx.get("category", pd.Series(dtype=str))).tolist())
    )

    # Top-10 category lists per chart (dashboard UX)
    top_income_cats = _top_n_categories_by_amount(scoped_tx, 10, positive_only=True)
    top_expense_cats = _top_n_categories_by_amount(scoped_tx, 10, negative_only=True)
    top_freq_cats = top_expense_cats[:]  # frequency is expense-centric

    # Multiselect options (concise, but include default excludes if present)
    income_options = _build_multiselect_options(top_income_cats, all_categories_full)
    expense_options = _build_multiselect_options(top_expense_cats, all_categories_full)
    freq_options = _build_multiselect_options(top_freq_cats, all_categories_full)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.caption("Exclude categories (Income chart)")
        st.multiselect(
            "Exclude categories (Income)",
            options=income_options,
            key=_SS_EXCL_INCOME,
            label_visibility="collapsed",
        )
    with c2:
        st.caption("Exclude categories (Expense chart)")
        st.multiselect(
            "Exclude categories (Expenses)",
            options=expense_options,
            key=_SS_EXCL_EXPENSE,
            label_visibility="collapsed",
        )
    with c3:
        st.caption("Exclude categories (Frequency chart)")
        st.multiselect(
            "Exclude categories (Frequency)",
            options=freq_options,
            key=_SS_EXCL_FREQ,
            label_visibility="collapsed",
        )

    excluded_income = st.session_state.get(_SS_EXCL_INCOME, [])
    excluded_expense = st.session_state.get(_SS_EXCL_EXPENSE, [])
    excluded_freq = st.session_state.get(_SS_EXCL_FREQ, [])

    # Build frames
    income_df = _build_income_top_frame(scoped_tx, excluded_income, top_n=10)
    expense_df = _build_expense_top_frame(scoped_tx, excluded_expense, top_n=10)
    freq_df = _build_expense_frequency_frame(scoped_tx, excluded_freq, top_n=10)

    g1, g2, g3 = st.columns(3)

    with g1:
        st.markdown("### Top Income Sources")
        if income_df.empty:
            st.info("No income categories in this date range (after exclusions).")
        else:
            st.altair_chart(_alt_hbar_top_income(income_df), use_container_width=True)

    with g2:
        st.markdown("### Top Expenses")
        if expense_df.empty:
            st.info("No expense categories in this date range (after exclusions).")
        else:
            st.altair_chart(_alt_hbar_top_expenses(expense_df), use_container_width=True)

    with g3:
        st.markdown("### Most Frequent Expenses")
        if freq_df.empty:
            st.info("No expense frequency in this date range (after exclusions).")
        else:
            st.altair_chart(_alt_hbar_frequency(freq_df), use_container_width=True)

    # -----------------------------
    # Exclusions Audit (Canonical)
    # -----------------------------
    st.divider()
    st.markdown("### Exclusions Audit")

    mask = build_exclusion_mask(scoped_tx)
    excluded_amounts = pd.to_numeric(scoped_tx.loc[mask, "amount"], errors="coerce").fillna(0.0)
    st.markdown(f"**Excluded totals:** {format_currency(float(excluded_amounts.sum()))}")

    with st.expander("Show excluded rows (audit)", expanded=False):
        cols = [c for c in ["date", "merchant", "category", "amount"] if c in scoped_tx.columns]
        st.dataframe(scoped_tx.loc[mask, cols], use_container_width=True)

    st.caption(
        f"Expense offsets: {format_currency(result.expense_offsets)} | "
        f"Gross expenses: {format_currency(result.gross_expenses)}"
    )
