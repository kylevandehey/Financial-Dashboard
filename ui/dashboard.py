# ui/dashboard.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

import altair as alt
import pandas as pd
import streamlit as st

from src.cash_flow import build_exclusion_mask, compute_cash_flow
from src.formatting import format_currency, format_date_range


# -----------------------------
# Constants (session keys)
# -----------------------------
_SS_DATE_PRESET = "dash_date_preset_v3"
_SS_CUSTOM_RANGE = "dash_custom_range_v3"  # tuple(date,date)
_SS_DATA_SIG = "dash_data_sig_v3"

_SS_INCOME_CATS = "dash_income_categories_v3"
_SS_EXPENSE_CATS = "dash_expense_categories_v3"
_SS_FREQ_CATS = "dash_frequency_categories_v3"


# -----------------------------
# Helpers
# -----------------------------
def _coerce_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    out = pd.DataFrame(df).copy()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
    if "amount" in out.columns:
        out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0.0)
    if "category" in out.columns:
        out["category"] = out["category"].fillna("").astype(str).str.strip()
    return out


def _derive_date_range(df: pd.DataFrame) -> tuple[date, date] | None:
    if df.empty or "date" not in df.columns:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return dates.min().date(), dates.max().date()


def _dataset_signature(df: pd.DataFrame) -> str:
    """
    Lightweight signature to detect "new upload" events without hashing the full dataset.
    """
    if df.empty or "date" not in df.columns or "amount" not in df.columns:
        return "empty"
    dr = _derive_date_range(df)
    if not dr:
        return f"rows={len(df)}"
    start, end = dr
    return f"rows={len(df)}|start={start.isoformat()}|end={end.isoformat()}"


def _safe_category(value: str) -> str:
    text = str(value or "").strip()
    return text if text else "(Uncategorized)"


def _available_years(df: pd.DataFrame) -> list[int]:
    if df.empty or "date" not in df.columns:
        return []
    years = pd.to_datetime(df["date"], errors="coerce").dt.year.dropna().astype(int).unique().tolist()
    return sorted(years, reverse=True)


def _apply_date_filter(df: pd.DataFrame, start_date: date | None, end_date: date | None) -> pd.DataFrame:
    if df.empty or "date" not in df.columns:
        return df
    if not start_date or not end_date:
        return df
    d = pd.to_datetime(df["date"], errors="coerce")
    mask = (d.dt.date >= start_date) & (d.dt.date <= end_date)
    return df.loc[mask].copy()


def _preset_options(df: pd.DataFrame) -> list[str]:
    years = _available_years(df)
    year_opts = ["ALL YEARS"] + [str(y) for y in years]
    # Order requirement: presets, then years, then custom
    presets = ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 180 Days", "Last Full Year"]
    return presets + year_opts + ["Custom Range"]


def _resolve_preset_to_range(
    *,
    preset: str,
    df: pd.DataFrame,
    today: date | None = None,
) -> tuple[date | None, date | None]:
    today = today or datetime.now().date()
    derived = _derive_date_range(df)
    if preset == "ALL YEARS":
        if derived:
            return derived[0], derived[1]
        return None, None

    if preset == "Last 7 Days":
        return today - timedelta(days=6), today
    if preset == "Last 30 Days":
        return today - timedelta(days=29), today
    if preset == "Last 90 Days":
        return today - timedelta(days=89), today
    if preset == "Last 180 Days":
        return today - timedelta(days=179), today
    if preset == "Last Full Year":
        last_year = today.year - 1
        return date(last_year, 1, 1), date(last_year, 12, 31)

    # Year selection
    try:
        year = int(preset)
        return date(year, 1, 1), date(year, 12, 31)
    except Exception:
        return None, None


def _infer_income_mask(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series([], dtype=bool)
    if "is_income" in df.columns:
        return df["is_income"].astype(bool)
    return df.get("amount", pd.Series(0.0, index=df.index)).astype(float) > 0


def _infer_expense_mask(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series([], dtype=bool)
    if "is_expense" in df.columns:
        return df["is_expense"].astype(bool)
    return df.get("amount", pd.Series(0.0, index=df.index)).astype(float) < 0


def _categories_in_scope(df: pd.DataFrame) -> list[str]:
    if df.empty or "category" not in df.columns:
        return []
    cats = df["category"].fillna("").astype(str).map(_safe_category).unique().tolist()
    # Stable, readable ordering
    return sorted(cats, key=lambda x: (x == "(Uncategorized)", x.lower()))


def _top_categories_by_amount(
    df: pd.DataFrame,
    *,
    mask: pd.Series,
    top_n: int,
    direction: str,
) -> list[str]:
    """
    direction:
      - "income": sum of positive amounts, descending
      - "expense_abs": abs(sum of negative amounts), descending
    """
    if df.empty or "category" not in df.columns or "amount" not in df.columns:
        return []
    work = df.loc[mask, ["category", "amount"]].copy()
    if work.empty:
        return []
    work["category"] = work["category"].map(_safe_category)
    if direction == "income":
        grouped = work.groupby("category", dropna=False)["amount"].sum()
        grouped = grouped.sort_values(ascending=False)
    else:
        grouped = work.groupby("category", dropna=False)["amount"].sum().abs()
        grouped = grouped.sort_values(ascending=False)
    return grouped.head(top_n).index.tolist()


def _top_categories_by_frequency(
    df: pd.DataFrame,
    *,
    mask: pd.Series,
    top_n: int,
) -> list[str]:
    if df.empty or "category" not in df.columns:
        return []
    work = df.loc[mask, ["category", "amount"]].copy()
    if work.empty:
        return []
    work["category"] = work["category"].map(_safe_category)
    grouped = work.groupby("category", dropna=False).size().sort_values(ascending=False)
    return grouped.head(top_n).index.tolist()


def _ensure_section_defaults(
    *,
    df_filtered: pd.DataFrame,
    data_sig: str,
    top_n_default: int = 7,
) -> None:
    """
    Initialize (or re-initialize on new upload) the section selections.
    Persistence rule:
      - date range changes DO NOT reset selections
      - new dataset DOES reset selections
    """
    if st.session_state.get(_SS_DATA_SIG) != data_sig:
        st.session_state[_SS_DATA_SIG] = data_sig

        income_mask = _infer_income_mask(df_filtered)
        expense_mask = _infer_expense_mask(df_filtered)

        st.session_state[_SS_INCOME_CATS] = _top_categories_by_amount(
            df_filtered, mask=income_mask, top_n=top_n_default, direction="income"
        )
        st.session_state[_SS_EXPENSE_CATS] = _top_categories_by_amount(
            df_filtered, mask=expense_mask, top_n=top_n_default, direction="expense_abs"
        )
        st.session_state[_SS_FREQ_CATS] = _top_categories_by_frequency(
            df_filtered, mask=expense_mask, top_n=top_n_default
        )

    # Ensure keys exist even if dataset was empty
    st.session_state.setdefault(_SS_INCOME_CATS, [])
    st.session_state.setdefault(_SS_EXPENSE_CATS, [])
    st.session_state.setdefault(_SS_FREQ_CATS, [])


def _reset_to_defaults(
    *,
    df_filtered: pd.DataFrame,
    top_n_default: int = 7,
) -> None:
    income_mask = _infer_income_mask(df_filtered)
    expense_mask = _infer_expense_mask(df_filtered)

    st.session_state[_SS_INCOME_CATS] = _top_categories_by_amount(
        df_filtered, mask=income_mask, top_n=top_n_default, direction="income"
    )
    st.session_state[_SS_EXPENSE_CATS] = _top_categories_by_amount(
        df_filtered, mask=expense_mask, top_n=top_n_default, direction="expense_abs"
    )
    st.session_state[_SS_FREQ_CATS] = _top_categories_by_frequency(
        df_filtered, mask=expense_mask, top_n=top_n_default
    )


def _bar_chart_amount(
    df: pd.DataFrame,
    *,
    title: str,
    x_field: str,
    y_field: str,
    y_title: str,
    tooltip_fields: list[alt.Tooltip],
    height: int = 260,
) -> alt.Chart:
    base = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_field}:N", sort="-y", title=None),
            y=alt.Y(f"{y_field}:Q", title=y_title),
            tooltip=tooltip_fields,
        )
        .properties(title=title, height=height)
    )
    return base


def _build_income_summary(df: pd.DataFrame, selected_categories: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category", "amount", "amount_fmt"])
    mask = _infer_income_mask(df)
    work = df.loc[mask, ["category", "amount"]].copy()
    if work.empty:
        return pd.DataFrame(columns=["category", "amount", "amount_fmt"])
    work["category"] = work["category"].map(_safe_category)
    if selected_categories:
        work = work[work["category"].isin(selected_categories)]
    grouped = work.groupby("category", dropna=False)["amount"].sum().reset_index()
    grouped["amount_fmt"] = grouped["amount"].apply(format_currency)
    grouped = grouped.sort_values("amount", ascending=False)
    return grouped


def _build_expense_summary(df: pd.DataFrame, selected_categories: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category", "spend_abs", "spend_abs_fmt"])
    mask = _infer_expense_mask(df)
    work = df.loc[mask, ["category", "amount"]].copy()
    if work.empty:
        return pd.DataFrame(columns=["category", "spend_abs", "spend_abs_fmt"])
    work["category"] = work["category"].map(_safe_category)
    if selected_categories:
        work = work[work["category"].isin(selected_categories)]
    grouped = work.groupby("category", dropna=False)["amount"].sum().abs().reset_index()
    grouped = grouped.rename(columns={"amount": "spend_abs"})
    grouped["spend_abs_fmt"] = grouped["spend_abs"].apply(format_currency)
    grouped = grouped.sort_values("spend_abs", ascending=False)
    return grouped


def _build_frequency_summary(df: pd.DataFrame, selected_categories: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category", "occurrences", "total_spend_abs", "total_spend_abs_fmt"])
    mask = _infer_expense_mask(df)
    work = df.loc[mask, ["category", "amount"]].copy()
    if work.empty:
        return pd.DataFrame(columns=["category", "occurrences", "total_spend_abs", "total_spend_abs_fmt"])
    work["category"] = work["category"].map(_safe_category)
    if selected_categories:
        work = work[work["category"].isin(selected_categories)]

    agg = (
        work.groupby("category", dropna=False)
        .agg(
            occurrences=("amount", "size"),
            total_spend_abs=("amount", lambda s: float(s.sum().__abs__())),
        )
        .reset_index()
    )
    agg["total_spend_abs_fmt"] = agg["total_spend_abs"].apply(format_currency)
    agg = agg.sort_values(["occurrences", "total_spend_abs"], ascending=[False, False])
    return agg


# -----------------------------
# Date Range Controls (Ledger-style)
# -----------------------------
def _render_date_range_controls(tx: pd.DataFrame) -> tuple[pd.DataFrame, date | None, date | None]:
    st.markdown("### Date Range Presets")

    options = _preset_options(tx)
    current = st.session_state.get(_SS_DATE_PRESET)
    if current not in options:
        current = "ALL YEARS" if "ALL YEARS" in options else options[0]

    preset = st.selectbox(
        "Date Range Presets",
        options=options,
        index=options.index(current),
        key=_SS_DATE_PRESET,
        label_visibility="visible",
    )

    start_date: date | None = None
    end_date: date | None = None

    if preset == "Custom Range":
        derived = _derive_date_range(tx)
        default_start = derived[0] if derived else datetime.now().date() - timedelta(days=29)
        default_end = derived[1] if derived else datetime.now().date()

        prior = st.session_state.get(_SS_CUSTOM_RANGE)
        if (
            isinstance(prior, (tuple, list))
            and len(prior) == 2
            and isinstance(prior[0], date)
            and isinstance(prior[1], date)
        ):
            default_tuple = (prior[0], prior[1])
        else:
            default_tuple = (default_start, default_end)

        st.markdown("#### Custom Date Range")
        picked = st.date_input(
            "Choose a date range",
            value=default_tuple,
            key=_SS_CUSTOM_RANGE,
        )
        # Streamlit may return a single date if mis-used; enforce tuple
        if isinstance(picked, (tuple, list)) and len(picked) == 2 and isinstance(picked[0], date) and isinstance(picked[1], date):
            start_date, end_date = picked[0], picked[1]
        else:
            # Fallback: treat as single date selection
            one = picked if isinstance(picked, date) else default_start
            start_date, end_date = one, one
    else:
        start_date, end_date = _resolve_preset_to_range(preset=preset, df=tx)

    filtered = _apply_date_filter(tx, start_date, end_date)

    # Display resolved range
    if start_date and end_date:
        st.caption("Date Range")
        st.caption(format_date_range((start_date, end_date)))

    return filtered, start_date, end_date


# -----------------------------
# UI
# -----------------------------
def render_dashboard_tab(
    transactions: pd.DataFrame,
) -> None:
    tx = _coerce_df(transactions)

    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    # Date range controls (Ledger-style)
    filtered_tx, start_date, end_date = _render_date_range_controls(tx)

    if filtered_tx.empty or "amount" not in filtered_tx.columns:
        st.info("No transactions in scope for the selected date range.")
        return

    # Snapshot (canonical)
    result = compute_cash_flow(filtered_tx)

    st.markdown("## Snapshot")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("Income", format_currency(result.income))
    with s2:
        st.metric("Expenses", format_currency(result.net_expenses))
    with s3:
        st.metric("Net Cash Flow", format_currency(result.net_cash))

    #  metrics per section (Ledger-style)
    data_sig = _dataset_signature(tx)
    _ensure_section_defaults(df_filtered=filtered_tx, data_sig=data_sig, top_n_default=7)

    st.markdown("## Snapshot Details")

    with st.expander("⚙️ Configure metrics per section", expanded=False):
        if st.button("Reset to Defaults", key="dash_reset_defaults_v3"):
            _reset_to_defaults(df_filtered=filtered_tx, top_n_default=7)
            st.rerun()

        all_categories = _categories_in_scope(filtered_tx)

        # Income categories (income-only)
        income_mask = _infer_income_mask(filtered_tx)
        income_categories_in_scope = sorted(
            set(filtered_tx.loc[income_mask, "category"].map(_safe_category).tolist()),
            key=lambda x: x.lower(),
        )
        income_options = [c for c in all_categories if c in set(income_categories_in_scope)]
        current_income = [c for c in st.session_state.get(_SS_INCOME_CATS, []) if c in income_options]
        st.session_state[_SS_INCOME_CATS] = current_income  # sanitize without changing defaults
        st.multiselect(
            "Income",
            options=income_options,
            default=current_income,
            key=_SS_INCOME_CATS,
            help="Top 7 defaults. Remove with ×. Add categories from the dropdown.",
        )

        # Expense categories (expense-only)
        expense_mask = _infer_expense_mask(filtered_tx)
        expense_categories_in_scope = sorted(
            set(filtered_tx.loc[expense_mask, "category"].map(_safe_category).tolist()),
            key=lambda x: x.lower(),
        )
        expense_options = [c for c in all_categories if c in set(expense_categories_in_scope)]
        current_expense = [c for c in st.session_state.get(_SS_EXPENSE_CATS, []) if c in expense_options]
        st.session_state[_SS_EXPENSE_CATS] = current_expense
        st.multiselect(
            "Expenses",
            options=expense_options,
            default=current_expense,
            key=_SS_EXPENSE_CATS,
            help="Top 7 defaults. Remove with ×. Add categories from the dropdown.",
        )

        # Frequency categories (expense-only)
        current_freq = [c for c in st.session_state.get(_SS_FREQ_CATS, []) if c in expense_options]
        st.session_state[_SS_FREQ_CATS] = current_freq
        st.multiselect(
            "Most Frequent Expenses",
            options=expense_options,
            default=current_freq,
            key=_SS_FREQ_CATS,
            help="Top 7 defaults by occurrence. Remove with ×. Add categories from the dropdown.",
        )

    # Build chart frames (category name, formatted values, sorted high->low left->right)
    income_sel = st.session_state.get(_SS_INCOME_CATS, [])
    expense_sel = st.session_state.get(_SS_EXPENSE_CATS, [])
    freq_sel = st.session_state.get(_SS_FREQ_CATS, [])

    income_df = _build_income_summary(filtered_tx, income_sel)
    expense_df = _build_expense_summary(filtered_tx, expense_sel)
    freq_df = _build_frequency_summary(filtered_tx, freq_sel)

    # If user removes everything, show guidance
    if income_df.empty and expense_df.empty and freq_df.empty:
        st.info("No categories selected. Add categories in 'Configure metrics per section' to render charts.")
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### Top Income Sources")
        if income_df.empty:
            st.info("No income categories selected in the current date range.")
        else:
            chart = _bar_chart_amount(
                income_df,
                title="",
                x_field="category",
                y_field="amount",
                y_title="Income ($)",
                tooltip_fields=[
                    alt.Tooltip("category:N", title="Category"),
                    alt.Tooltip("amount_fmt:N", title="Total Income"),
                ],
            )
            st.altair_chart(chart, use_container_width=True)

    with c2:
        st.markdown("### Top Expenses")
        if expense_df.empty:
            st.info("No expense categories selected in the current date range.")
        else:
            chart = _bar_chart_amount(
                expense_df,
                title="",
                x_field="category",
                y_field="spend_abs",
                y_title="Spend ($)",
                tooltip_fields=[
                    alt.Tooltip("category:N", title="Category"),
                    alt.Tooltip("spend_abs_fmt:N", title="Total Spend"),
                ],
            )
            st.altair_chart(chart, use_container_width=True)

    with c3:
        st.markdown("### Most Frequent Expenses")
        if freq_df.empty:
            st.info("No frequency categories selected in the current date range.")
        else:
            # Sort highest to lowest already; bar uses sort=-y
            freq_df = freq_df.copy()
            chart = _bar_chart_amount(
                freq_df,
                title="",
                x_field="category",
                y_field="occurrences",
                y_title="Occurrences",
                tooltip_fields=[
                    alt.Tooltip("category:N", title="Category"),
                    alt.Tooltip("occurrences:Q", title="Occurrences"),
                    alt.Tooltip("total_spend_abs_fmt:N", title="Total Spend"),
                ],
            )
            st.altair_chart(chart, use_container_width=True)

            # Requirement: show total dollar values for frequency
            with st.expander("Show frequency totals", expanded=False):
                st.dataframe(
                    freq_df[["category", "occurrences", "total_spend_abs"]],
                    use_container_width=True,
                )

    st.divider()

    # Exclusions audit (kept)
    mask = build_exclusion_mask(filtered_tx)
    excluded_amounts = pd.to_numeric(filtered_tx.loc[mask, "amount"], errors="coerce").fillna(0.0)

    st.markdown(f"**Excluded totals:** {format_currency(float(excluded_amounts.sum()))}")

    with st.expander("Show excluded rows (audit)", expanded=False):
        cols = [c for c in ["date", "merchant", "category", "notes", "amount"] if c in filtered_tx.columns]
        st.dataframe(filtered_tx.loc[mask, cols], use_container_width=True)

    st.caption(
        f"Expense offsets: {format_currency(result.expense_offsets)} | "
        f"Gross expenses: {format_currency(result.gross_expenses)}"
    )
