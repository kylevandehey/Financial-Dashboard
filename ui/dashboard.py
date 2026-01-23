# ui/dashboard.py

from __future__ import annotations

import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta

from src.formatting import format_currency, format_date_range
from src.cash_flow import compute_cash_flow


# -----------------------------
# Session keys (Dashboard)
# -----------------------------
_K_PRESET = "dash_date_preset_v3"
_K_CUSTOM_RANGE = "dash_custom_range_v3"

_K_INCOME_SELECTED = "dash_income_selected_v3"
_K_EXPENSE_SELECTED = "dash_expense_selected_v3"
_K_FREQ_SELECTED = "dash_freq_selected_v3"


# -----------------------------
# Data helpers
# -----------------------------
def _coerce_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    return pd.DataFrame(df).copy()


def _ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "date" not in df.columns:
        return df
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def _derive_min_max_dates(df: pd.DataFrame) -> tuple[date, date] | None:
    if df.empty or "date" not in df.columns:
        return None
    d = pd.to_datetime(df["date"], errors="coerce").dropna()
    if d.empty:
        return None
    return d.min().date(), d.max().date()


def _years_in_df(df: pd.DataFrame) -> list[int]:
    if df.empty or "date" not in df.columns:
        return []
    d = pd.to_datetime(df["date"], errors="coerce").dropna()
    if d.empty:
        return []
    years = sorted(d.dt.year.unique().tolist(), reverse=True)
    return [int(y) for y in years if pd.notna(y)]


def _filter_date_range(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    if df.empty or "date" not in df.columns:
        return df
    d = pd.to_datetime(df["date"], errors="coerce")
    mask = (d.dt.date >= start) & (d.dt.date <= end)
    return df.loc[mask].copy()


def _classify_income_expense(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prefer canonical flags if present (is_income/is_expense). Fall back to sign-based.
    """
    if df.empty or "amount" not in df.columns:
        return df.iloc[0:0].copy(), df.iloc[0:0].copy()

    if "is_income" in df.columns and "is_expense" in df.columns:
        income_df = df.loc[df["is_income"] == True].copy()
        expense_df = df.loc[df["is_expense"] == True].copy()
        return income_df, expense_df

    # Fallback: sign-based
    amt = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    income_df = df.loc[amt > 0].copy()
    expense_df = df.loc[amt < 0].copy()
    return income_df, expense_df


def _months_observed(df: pd.DataFrame, start: date, end: date) -> int:
    # Prefer months present in data; fallback to calendar span.
    if df.empty or "date" not in df.columns:
        # calendar span
        span_months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        return max(1, span_months)

    d = pd.to_datetime(df["date"], errors="coerce").dropna()
    if d.empty:
        span_months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        return max(1, span_months)

    months = d.dt.to_period("M").nunique()
    return int(max(1, months))


def _safe_pct(num: float, den: float) -> float | None:
    if den == 0:
        return None
    return num / den


def _fmt_pct(value: float | None, *, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value*100:.{digits}f}%"


def _arrow(delta: float) -> str:
    if delta > 0:
        return "▲"
    if delta < 0:
        return "▼"
    return "→"


# -----------------------------
# Date controls (Ledger-style)
# -----------------------------
def _build_preset_options(years: list[int]) -> list[str]:
    options = [
        "Last 7 Days",
        "Last 30 Days",
        "Last 90 Days",
        "Last 180 Days",
        "Last Full Year",
        "ALL YEARS",
    ]
    for y in years:
        options.append(str(y))
    options.append("Custom Range")
    return options


def _compute_preset_range(
    preset: str,
    *,
    min_date: date,
    max_date: date,
    years: list[int],
) -> tuple[date, date]:
    # All rolling windows anchor off max_date (i.e., latest transaction date)
    anchor = max_date
    if preset == "Last 7 Days":
        return anchor - timedelta(days=6), anchor
    if preset == "Last 30 Days":
        return anchor - timedelta(days=29), anchor
    if preset == "Last 90 Days":
        return anchor - timedelta(days=89), anchor
    if preset == "Last 180 Days":
        return anchor - timedelta(days=179), anchor
    if preset == "Last Full Year":
        # previous full calendar year relative to max_date
        y = anchor.year - 1
        return date(y, 1, 1), date(y, 12, 31)
    if preset == "ALL YEARS":
        return min_date, max_date
    # Year selection
    try:
        y = int(preset)
        if y in years:
            return date(y, 1, 1), date(y, 12, 31)
    except Exception:
        pass
    # Fallback
    return min_date, max_date


def _render_date_controls(tx: pd.DataFrame) -> tuple[pd.DataFrame, date, date, str]:
    """
    Returns: filtered_tx, start_date, end_date, preset_label
    """
    tx = _coerce_df(tx)
    tx = _ensure_datetime(tx)

    mm = _derive_min_max_dates(tx)
    if not mm:
        today = datetime.now().date()
        return tx, today, today, "ALL YEARS"

    min_date, max_date = mm
    years = _years_in_df(tx)
    options = _build_preset_options(years)

    # Initialize session defaults ONCE (avoid Streamlit warning about default+session set)
    if _K_PRESET not in st.session_state:
        st.session_state[_K_PRESET] = "ALL YEARS"
    if _K_CUSTOM_RANGE not in st.session_state:
        st.session_state[_K_CUSTOM_RANGE] = (min_date, max_date)

    st.markdown("### Date Range Presets")

    preset = st.selectbox(
        "Date Range Presets",
        options=options,
        index=options.index(st.session_state[_K_PRESET]) if st.session_state[_K_PRESET] in options else options.index("ALL YEARS"),
        key=_K_PRESET,
        label_visibility="visible",
    )

    # If not custom, compute range from preset (but DO NOT overwrite custom selection)
    if preset != "Custom Range":
        start_date, end_date = _compute_preset_range(
            preset, min_date=min_date, max_date=max_date, years=years
        )
        # Keep custom range stored but don't force it.
    else:
        st.markdown("#### Custom Date Range")
        # Use a single range picker (Ledger-like behavior)
        current = st.session_state.get(_K_CUSTOM_RANGE, (min_date, max_date))
        start_date, end_date = st.date_input(
            "Choose a date range",
            value=current,
            min_value=min_date,
            max_value=max_date,
            key="dash_date_range_picker_v3",
        )
        # Persist chosen custom range
        st.session_state[_K_CUSTOM_RANGE] = (start_date, end_date)

    # Normalize / guard
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    filtered = _filter_date_range(tx, start_date, end_date)
    st.caption("Date Range")
    st.caption(format_date_range((start_date, end_date)))

    return filtered, start_date, end_date, preset


# -----------------------------
# Snapshot + Health strip
# -----------------------------
def _compute_prior_period_range(start_date: date, end_date: date) -> tuple[date, date]:
    span_days = (end_date - start_date).days + 1
    prior_end = start_date - timedelta(days=1)
    prior_start = prior_end - timedelta(days=span_days - 1)
    return prior_start, prior_end


def _render_snapshot_and_health(
    tx_filtered: pd.DataFrame,
    tx_all: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> None:
    result = compute_cash_flow(tx_filtered)

    # Prior-period comparison (same length window immediately preceding)
    prior_start, prior_end = _compute_prior_period_range(start_date, end_date)
    tx_prior = _filter_date_range(_ensure_datetime(_coerce_df(tx_all)), prior_start, prior_end)
    prior_result = compute_cash_flow(tx_prior) if not tx_prior.empty else None

    net_delta = None
    net_pct = None
    if prior_result is not None:
        net_delta = result.net_cash - prior_result.net_cash
        net_pct = _safe_pct(net_delta, abs(prior_result.net_cash))  # percent vs prior magnitude

    st.markdown("## Snapshot")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Income", format_currency(result.income))
    with c2:
        st.metric("Expenses", format_currency(result.net_expenses))
    with c3:
        # Use metric delta for quick visual
        if net_delta is not None:
            st.metric("Net Cash Flow", format_currency(result.net_cash), delta=format_currency(net_delta))
            st.caption(f"{_arrow(net_delta)} {_fmt_pct(net_pct)} vs prior period")
        else:
            st.metric("Net Cash Flow", format_currency(result.net_cash))
            st.caption("— vs prior period")

    # -----------------------------
    # Financial Health Strip
    # -----------------------------
    st.markdown("### Financial Health")
    income = float(result.income or 0.0)
    expenses = float(result.net_expenses or 0.0)
    net = float(result.net_cash or 0.0)

    savings_rate = _safe_pct(net, income)
    expense_ratio = _safe_pct(expenses, income)

    months = _months_observed(tx_filtered, start_date, end_date)
    avg_monthly_net = net / months if months else net
    avg_monthly_spend = expenses / months if months else expenses

    # Largest expense category (% of spend)
    _, expense_df = _classify_income_expense(tx_filtered)
    largest_exp_pct = None
    largest_exp_label = "—"
    if not expense_df.empty and "category" in expense_df.columns and "amount" in expense_df.columns:
        exp = expense_df.copy()
        exp["amount"] = pd.to_numeric(exp["amount"], errors="coerce").fillna(0.0)
        # Spend as positive magnitude
        exp["spend"] = exp["amount"].abs()
        by_cat = exp.groupby("category", dropna=False)["spend"].sum().sort_values(ascending=False)
        total_spend = float(by_cat.sum())
        if total_spend > 0 and len(by_cat) > 0:
            largest_exp_label = str(by_cat.index[0] if pd.notna(by_cat.index[0]) else "(Uncategorized)")
            largest_exp_pct = float(by_cat.iloc[0]) / total_spend

    h1, h2, h3, h4, h5 = st.columns(5)
    with h1:
        st.metric("Savings Rate", _fmt_pct(savings_rate))
    with h2:
        st.metric("Expense Ratio", _fmt_pct(expense_ratio))
    with h3:
        st.metric("Avg Monthly Net", format_currency(avg_monthly_net))
    with h4:
        st.metric("Avg Monthly Spend", format_currency(avg_monthly_spend))
    with h5:
        st.metric("Largest Expense Share", _fmt_pct(largest_exp_pct))
        st.caption(largest_exp_label)


# -----------------------------
# Snapshot Details (Configurator + Charts + Tables)
# -----------------------------
def _income_totals_by_category(df: pd.DataFrame) -> pd.DataFrame:
    income_df, _ = _classify_income_expense(df)
    if income_df.empty or "category" not in income_df.columns or "amount" not in income_df.columns:
        return pd.DataFrame(columns=["category", "amount"])
    income_df = income_df.copy()
    income_df["amount"] = pd.to_numeric(income_df["amount"], errors="coerce").fillna(0.0)
    agg = (
        income_df.groupby("category", dropna=False)["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )
    agg["category"] = agg["category"].fillna("(Uncategorized)").astype(str)
    return agg


def _expense_totals_by_category(df: pd.DataFrame) -> pd.DataFrame:
    _, expense_df = _classify_income_expense(df)
    if expense_df.empty or "category" not in expense_df.columns or "amount" not in expense_df.columns:
        return pd.DataFrame(columns=["category", "spend"])
    expense_df = expense_df.copy()
    expense_df["amount"] = pd.to_numeric(expense_df["amount"], errors="coerce").fillna(0.0)
    expense_df["spend"] = expense_df["amount"].abs()
    agg = (
        expense_df.groupby("category", dropna=False)["spend"]
        .sum()
        .reset_index()
        .sort_values("spend", ascending=False)
    )
    agg["category"] = agg["category"].fillna("(Uncategorized)").astype(str)
    return agg


def _expense_frequency_by_category(df: pd.DataFrame) -> pd.DataFrame:
    _, expense_df = _classify_income_expense(df)
    if expense_df.empty or "category" not in expense_df.columns or "amount" not in expense_df.columns:
        return pd.DataFrame(columns=["category", "occurrences", "spend"])
    expense_df = expense_df.copy()
    expense_df["amount"] = pd.to_numeric(expense_df["amount"], errors="coerce").fillna(0.0)
    expense_df["spend"] = expense_df["amount"].abs()
    agg = (
        expense_df.groupby("category", dropna=False)
        .agg(
            occurrences=("category", "size"),
            spend=("spend", "sum"),
        )
        .reset_index()
        .sort_values("occurrences", ascending=False)
    )
    agg["category"] = agg["category"].fillna("(Uncategorized)").astype(str)
    return agg


def _default_selected_categories(
    df: pd.DataFrame,
    *,
    mode: str,
    top_n: int = 7,
) -> list[str]:
    """
    mode: "income" | "expense" | "frequency"
    Defaults are recalculated for the *current date range*.
    """
    default_exclude = {"Transfer", "Credit Card Payment"}

    if mode == "income":
        agg = _income_totals_by_category(df)
        cats = [c for c in agg["category"].tolist() if c not in default_exclude]
        return cats[:top_n]
    if mode == "expense":
        agg = _expense_totals_by_category(df)
        cats = [c for c in agg["category"].tolist() if c not in default_exclude]
        return cats[:top_n]
    if mode == "frequency":
        agg = _expense_frequency_by_category(df)
        cats = [c for c in agg["category"].tolist() if c not in default_exclude]
        return cats[:top_n]
    return []


def _ensure_config_defaults(df: pd.DataFrame) -> None:
    if _K_INCOME_SELECTED not in st.session_state:
        st.session_state[_K_INCOME_SELECTED] = _default_selected_categories(df, mode="income", top_n=7)
    if _K_EXPENSE_SELECTED not in st.session_state:
        st.session_state[_K_EXPENSE_SELECTED] = _default_selected_categories(df, mode="expense", top_n=7)
    if _K_FREQ_SELECTED not in st.session_state:
        st.session_state[_K_FREQ_SELECTED] = _default_selected_categories(df, mode="frequency", top_n=7)


def _render_configurator(df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    _ensure_config_defaults(df)

    income_options = _income_totals_by_category(df)["category"].tolist()
    expense_options = _expense_totals_by_category(df)["category"].tolist()
    freq_options = _expense_frequency_by_category(df)["category"].tolist()

    st.markdown("## Snapshot Details")

    with st.expander("⚙️ Configure metrics per section", expanded=False):
        if st.button("Reset to Defaults", key="dash_reset_defaults_v3"):
            st.session_state[_K_INCOME_SELECTED] = _default_selected_categories(df, mode="income", top_n=7)
            st.session_state[_K_EXPENSE_SELECTED] = _default_selected_categories(df, mode="expense", top_n=7)
            st.session_state[_K_FREQ_SELECTED] = _default_selected_categories(df, mode="frequency", top_n=7)
            st.rerun()

        st.markdown("**Income**")
        income_selected = st.multiselect(
            "Income",
            options=income_options,
            default=[c for c in st.session_state[_K_INCOME_SELECTED] if c in income_options],
            key=_K_INCOME_SELECTED,
            label_visibility="collapsed",
        )

        st.markdown("**Expenses**")
        expense_selected = st.multiselect(
            "Expenses",
            options=expense_options,
            default=[c for c in st.session_state[_K_EXPENSE_SELECTED] if c in expense_options],
            key=_K_EXPENSE_SELECTED,
            label_visibility="collapsed",
        )

        st.markdown("**Most Frequent Expenses**")
        freq_selected = st.multiselect(
            "Most Frequent Expenses",
            options=freq_options,
            default=[c for c in st.session_state[_K_FREQ_SELECTED] if c in freq_options],
            key=_K_FREQ_SELECTED,
            label_visibility="collapsed",
        )

    # Pull from session state so charts reflect the latest selections
    income_selected = st.session_state.get(_K_INCOME_SELECTED, [])
    expense_selected = st.session_state.get(_K_EXPENSE_SELECTED, [])
    freq_selected = st.session_state.get(_K_FREQ_SELECTED, [])

    return income_selected, expense_selected, freq_selected


def _alt_bar_chart_categories(
    df: pd.DataFrame,
    *,
    x_field: str,
    y_field: str,
    title: str,
    y_title: str,
    y_format: str | None = None,
    tooltip_fields: list[alt.Tooltip] | None = None,
    height: int = 260,
) -> alt.Chart:
    base = alt.Chart(df).mark_bar().encode(
        x=alt.X(f"{x_field}:N", sort=alt.SortField(y_field, order="descending"), title="category"),
        y=alt.Y(f"{y_field}:Q", title=y_title, axis=alt.Axis(format=y_format) if y_format else alt.Axis()),
        tooltip=tooltip_fields if tooltip_fields else [],
    ).properties(height=height, title=title)
    return base


def _render_income_section(df: pd.DataFrame, selected: list[str]) -> None:
    st.markdown("### Top Income Sources")

    agg = _income_totals_by_category(df)
    if agg.empty:
        st.info("No income data in the selected range.")
        return

    if selected:
        agg = agg.loc[agg["category"].isin(selected)].copy()

    agg["amount_fmt"] = agg["amount"].apply(format_currency)

    chart = _alt_bar_chart_categories(
        agg,
        x_field="category",
        y_field="amount",
        title="Top Income Sources",
        y_title="Income ($)",
        y_format="$,.0f",
        tooltip_fields=[
            alt.Tooltip("category:N", title="Category"),
            alt.Tooltip("amount_fmt:N", title="Total Income"),
        ],
    )
    st.altair_chart(chart, use_container_width=True)

    with st.expander("Show income totals", expanded=False):
        tbl = agg.sort_values("amount", ascending=False)[["category", "amount"]].copy()
        tbl["amount"] = tbl["amount"].apply(format_currency)
        tbl = tbl.rename(columns={"category": "Category", "amount": "Total Income"})
        st.dataframe(tbl, use_container_width=True, hide_index=True)


def _render_expense_section(df: pd.DataFrame, selected: list[str]) -> None:
    st.markdown("### Top Expenses")

    agg = _expense_totals_by_category(df)
    if agg.empty:
        st.info("No expense data in the selected range.")
        return

    if selected:
        agg = agg.loc[agg["category"].isin(selected)].copy()

    agg["spend_fmt"] = agg["spend"].apply(format_currency)

    chart = _alt_bar_chart_categories(
        agg,
        x_field="category",
        y_field="spend",
        title="Top Expenses",
        y_title="Spend ($)",
        y_format="$,.0f",
        tooltip_fields=[
            alt.Tooltip("category:N", title="Category"),
            alt.Tooltip("spend_fmt:N", title="Total Spend"),
        ],
    )
    st.altair_chart(chart, use_container_width=True)

    with st.expander("Show expense totals", expanded=False):
        tbl = agg.sort_values("spend", ascending=False)[["category", "spend"]].copy()
        tbl["spend"] = tbl["spend"].apply(format_currency)
        tbl = tbl.rename(columns={"category": "Category", "spend": "Total Spend"})
        st.dataframe(tbl, use_container_width=True, hide_index=True)


def _render_frequency_section(df: pd.DataFrame, selected: list[str]) -> None:
    st.markdown("### Most Frequent Expenses")

    agg = _expense_frequency_by_category(df)
    if agg.empty:
        st.info("No expense frequency data in the selected range.")
        return

    if selected:
        agg = agg.loc[agg["category"].isin(selected)].copy()

    agg["spend_fmt"] = agg["spend"].apply(format_currency)

    chart = alt.Chart(agg).mark_bar().encode(
        x=alt.X("category:N", sort=alt.SortField("occurrences", order="descending"), title="category"),
        y=alt.Y("occurrences:Q", title="Occurrences", axis=alt.Axis(format=",.0f")),
        tooltip=[
            alt.Tooltip("category:N", title="Category"),
            alt.Tooltip("occurrences:Q", title="Occurrences", format=","),
            alt.Tooltip("spend_fmt:N", title="Total Spend"),
        ],
    ).properties(height=260, title="Most Frequent Expenses")
    st.altair_chart(chart, use_container_width=True)

    with st.expander("Show frequency totals", expanded=False):
        tbl = agg.sort_values("occurrences", ascending=False)[["category", "occurrences", "spend"]].copy()
        tbl["spend"] = tbl["spend"].apply(format_currency)
        tbl = tbl.rename(columns={"category": "Category", "occurrences": "Occurrences", "spend": "Total Spend"})
        st.dataframe(tbl, use_container_width=True, hide_index=True)


# -----------------------------
# Public entry point
# -----------------------------
def render_dashboard_tab(transactions: pd.DataFrame) -> None:
    tx_all = _ensure_datetime(_coerce_df(transactions))

    st.markdown("# Dashboard (Core Rebuild)")
    st.markdown("## Dashboard Overview")

    if tx_all.empty or "date" not in tx_all.columns or "amount" not in tx_all.columns:
        st.info("No transactions available. Upload Monarch CSV exports to begin.")
        return

    # Date controls (Ledger-style) + filtered scope
    tx_filtered, start_date, end_date, preset_label = _render_date_controls(tx_all)

    # Snapshot + Health strip + trend indicators
    _render_snapshot_and_health(tx_filtered, tx_all, start_date, end_date)

    # Configurator (collapsed by default) + charts
    income_selected, expense_selected, freq_selected = _render_configurator(tx_filtered)

    c1, c2, c3 = st.columns(3)
    with c1:
        _render_income_section(tx_filtered, income_selected)
    with c2:
        _render_expense_section(tx_filtered, expense_selected)
    with c3:
        _render_frequency_section(tx_filtered, freq_selected)
