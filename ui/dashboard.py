# ui/dashboard.py

import streamlit as st
import pandas as pd
import altair as alt

from datetime import date, datetime, timedelta
from typing import Optional, Tuple, List

from src.formatting import format_currency, format_date_range
from src.cash_flow import compute_cash_flow, build_exclusion_mask


# =====================================================================
# Session keys (stable)
# =====================================================================

_SS_PRESET = "dash_date_preset"
_SS_YEAR = "dash_year_scope"
_SS_CUSTOM_START = "dash_custom_start"
_SS_CUSTOM_END = "dash_custom_end"


# =====================================================================
# Core helpers
# =====================================================================

def _coerce_df(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    return pd.DataFrame(df).copy()


def _ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def _available_years(df: pd.DataFrame) -> List[int]:
    if df.empty or "date" not in df.columns:
        return []
    dates = pd.to_datetime(df["date"], errors="coerce")
    years = dates.dt.year.dropna().astype(int).unique().tolist()
    years = sorted(years, reverse=True)
    return years


def _min_max_dates(df: pd.DataFrame) -> Optional[Tuple[date, date]]:
    if df.empty or "date" not in df.columns:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return (dates.min().date(), dates.max().date())


def _filter_by_year(df: pd.DataFrame, year_label: str) -> pd.DataFrame:
    if df.empty or "date" not in df.columns:
        return df
    if year_label == "ALL YEARS":
        return df
    try:
        y = int(year_label)
    except Exception:
        return df
    dates = pd.to_datetime(df["date"], errors="coerce")
    return df.loc[dates.dt.year == y]


def _apply_date_range(df: pd.DataFrame, start: Optional[date], end: Optional[date]) -> pd.DataFrame:
    if df.empty or "date" not in df.columns or start is None or end is None:
        return df
    dates = pd.to_datetime(df["date"], errors="coerce")
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    return df.loc[(dates >= start_ts) & (dates <= end_ts)]


# =====================================================================
# Ledger-style date preset UI
# =====================================================================

def _init_date_state(df: pd.DataFrame) -> None:
    # Initialize state once with sane defaults
    if _SS_PRESET not in st.session_state:
        st.session_state[_SS_PRESET] = "ALL YEARS"
    if _SS_YEAR not in st.session_state:
        st.session_state[_SS_YEAR] = "ALL YEARS"
    if _SS_CUSTOM_START not in st.session_state:
        st.session_state[_SS_CUSTOM_START] = None
    if _SS_CUSTOM_END not in st.session_state:
        st.session_state[_SS_CUSTOM_END] = None

    # If custom dates not set, seed them from df range (if available)
    rng = _min_max_dates(df)
    if rng:
        df_min, df_max = rng
        if st.session_state[_SS_CUSTOM_START] is None:
            st.session_state[_SS_CUSTOM_START] = df_min
        if st.session_state[_SS_CUSTOM_END] is None:
            st.session_state[_SS_CUSTOM_END] = df_max


def _resolve_preset_to_range(
    df: pd.DataFrame,
    preset: str,
    year_scope: str,
    custom_start: Optional[date],
    custom_end: Optional[date],
) -> Tuple[Optional[date], Optional[date], str]:
    """
    Returns: (start_date, end_date, human_label)
    Notes:
    - Applies year_scope first (if year selected), then applies preset window within that scope.
    - For ALL YEARS, windows are relative to max date in the data (not "today") to avoid empty windows.
    """
    if df.empty or "date" not in df.columns:
        return (None, None, "No data")

    df = _ensure_datetime(df)
    scoped = _filter_by_year(df, year_scope)
    scoped_rng = _min_max_dates(scoped)
    if not scoped_rng:
        return (None, None, "No dates in scope")
    scope_start, scope_end = scoped_rng

    # Anchor windows to last available transaction date in scope
    anchor_end = scope_end

    preset = (preset or "").strip()

    if preset == "ALL YEARS":
        return (scope_start, scope_end, f"{year_scope}: ALL YEARS")

    if preset == "Last 7 Days":
        return (anchor_end - timedelta(days=6), anchor_end, "Last 7 Days")
    if preset == "Last 30 Days":
        return (anchor_end - timedelta(days=29), anchor_end, "Last 30 Days")
    if preset == "Last 90 Days":
        return (anchor_end - timedelta(days=89), anchor_end, "Last 90 Days")
    if preset == "Last 180 Days":
        return (anchor_end - timedelta(days=179), anchor_end, "Last 180 Days")

    if preset == "Last Full Year":
        # Last complete calendar year relative to anchor_end
        last_year = anchor_end.year - 1
        start = date(last_year, 1, 1)
        end = date(last_year, 12, 31)
        # Clamp to scope
        start = max(start, scope_start)
        end = min(end, scope_end)
        return (start, end, "Last Full Year")

    if preset == "Custom Range":
        if custom_start is None or custom_end is None:
            return (scope_start, scope_end, "Custom Range (defaulted)")
        start = max(custom_start, scope_start)
        end = min(custom_end, scope_end)
        if start > end:
            return (scope_start, scope_end, "Custom Range (invalid → defaulted)")
        return (start, end, "Custom Range")

    # Fallback
    return (scope_start, scope_end, f"{preset} (defaulted)")


def _render_date_controls(df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[date], Optional[date]]:
    """
    Renders the Ledger-style date control system inside the Dashboard tab.
    Returns filtered df + resolved (start,end).
    """
    _init_date_state(df)

    years = _available_years(df)
    year_options = ["ALL YEARS"] + [str(y) for y in years]

    preset_options = [
        "ALL YEARS",
        "Last 7 Days",
        "Last 30 Days",
        "Last 90 Days",
        "Last 180 Days",
        "Last Full Year",
        "Custom Range",
    ]

    st.markdown("### Date Range Presets")

    c1, c2 = st.columns([2, 1])

    with c1:
        st.session_state[_SS_PRESET] = st.selectbox(
            "Date Range Presets",
            preset_options,
            index=preset_options.index(st.session_state.get(_SS_PRESET, "ALL YEARS"))
            if st.session_state.get(_SS_PRESET, "ALL YEARS") in preset_options
            else 0,
            key="dash_preset_selectbox",
            label_visibility="collapsed",
        )

    with c2:
        st.session_state[_SS_YEAR] = st.selectbox(
            "Year Scope",
            year_options,
            index=year_options.index(st.session_state.get(_SS_YEAR, "ALL YEARS"))
            if st.session_state.get(_SS_YEAR, "ALL YEARS") in year_options
            else 0,
            key="dash_year_scope_selectbox",
        )

    if st.session_state[_SS_PRESET] == "Custom Range":
        st.markdown("#### Custom Date Range")
        d1, d2 = st.columns(2)
        with d1:
            st.session_state[_SS_CUSTOM_START] = st.date_input(
                "Start date",
                value=st.session_state.get(_SS_CUSTOM_START),
                key="dash_custom_start",
            )
        with d2:
            st.session_state[_SS_CUSTOM_END] = st.date_input(
                "End date",
                value=st.session_state.get(_SS_CUSTOM_END),
                key="dash_custom_end",
            )

    start, end, _ = _resolve_preset_to_range(
        df=df,
        preset=st.session_state[_SS_PRESET],
        year_scope=st.session_state[_SS_YEAR],
        custom_start=st.session_state.get(_SS_CUSTOM_START),
        custom_end=st.session_state.get(_SS_CUSTOM_END),
    )

    # Apply year + date filter
    scoped = _filter_by_year(df, st.session_state[_SS_YEAR])
    filtered = _apply_date_range(scoped, start, end)
    return filtered, start, end


# =====================================================================
# Analytics frames (canonical)
# =====================================================================

def _monthly_cash_flow_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "date" not in df.columns or "amount" not in df.columns:
        return pd.DataFrame()

    dfx = _ensure_datetime(df).copy()
    dfx = dfx.dropna(subset=["date"])
    if dfx.empty:
        return pd.DataFrame()

    dfx["month_start"] = dfx["date"].dt.to_period("M").dt.to_timestamp()

    rows = []
    for month, month_df in dfx.groupby("month_start"):
        r = compute_cash_flow(month_df)
        rows.append(
            {
                "month_start": month,
                "Income": r.income,
                "Net Expenses": r.net_expenses,
                "Net Cash": r.net_cash,
            }
        )

    wide = pd.DataFrame(rows).sort_values("month_start")
    if wide.empty:
        return pd.DataFrame()

    long = wide.melt(
        id_vars="month_start",
        value_vars=["Income", "Net Expenses", "Net Cash"],
        var_name="metric",
        value_name="value",
    )
    long["value_fmt"] = long["value"].apply(format_currency)
    return long


def _monthly_net_cash_only(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "date" not in df.columns or "amount" not in df.columns:
        return pd.DataFrame()

    dfx = _ensure_datetime(df).copy()
    dfx = dfx.dropna(subset=["date"])
    if dfx.empty:
        return pd.DataFrame()

    dfx["month_start"] = dfx["date"].dt.to_period("M").dt.to_timestamp()

    rows = []
    for month, month_df in dfx.groupby("month_start"):
        r = compute_cash_flow(month_df)
        rows.append({"month_start": month, "net_cash": r.net_cash})

    out = pd.DataFrame(rows).sort_values("month_start")
    if out.empty:
        return out
    out["net_cash_fmt"] = out["net_cash"].apply(format_currency)
    out["roll_3"] = out["net_cash"].rolling(window=3, min_periods=1).mean()
    out["roll_6"] = out["net_cash"].rolling(window=6, min_periods=1).mean()
    return out


def _category_volatility_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Volatility = std dev of monthly *net cash* per category (canonical).
    """
    if df.empty or "date" not in df.columns or "category" not in df.columns:
        return pd.DataFrame()

    dfx = _ensure_datetime(df).copy()
    dfx["category"] = dfx["category"].fillna("").astype(str).str.strip()
    dfx["month_start"] = dfx["date"].dt.to_period("M").dt.to_timestamp()

    rows = []
    for (category, month), group in dfx.groupby(["category", "month_start"]):
        r = compute_cash_flow(group)
        rows.append(
            {
                "category": category if category else "(Uncategorized)",
                "month_start": month,
                "net_cash": r.net_cash,
            }
        )

    monthly = pd.DataFrame(rows)
    if monthly.empty:
        return monthly

    agg = (
        monthly.groupby("category")["net_cash"]
        .agg(avg_net="mean", volatility="std", months="count")
        .reset_index()
    )
    agg["avg_net_fmt"] = agg["avg_net"].apply(format_currency)
    agg["volatility_fmt"] = agg["volatility"].fillna(0.0).apply(format_currency)
    return agg.sort_values("volatility", ascending=False)


def _top_income_sources(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Heuristic: For income, group by merchant first (best “source” proxy for Monarch).
    Only uses positive amounts.
    """
    if df.empty or "amount" not in df.columns:
        return pd.DataFrame()

    dfx = df.copy()
    dfx["merchant"] = dfx.get("merchant", "").fillna("").astype(str).str.strip()
    amounts = pd.to_numeric(dfx["amount"], errors="coerce").fillna(0.0)

    pos = dfx.loc[amounts > 0].copy()
    if pos.empty:
        return pd.DataFrame()

    # Use canonical engine to avoid counting excluded rows:
    ex_mask = build_exclusion_mask(pos)
    pos = pos.loc[~ex_mask].copy()
    if pos.empty:
        return pd.DataFrame()

    pos_amounts = pd.to_numeric(pos["amount"], errors="coerce").fillna(0.0)
    out = (
        pos.assign(_amt=pos_amounts)
        .groupby("merchant")["_amt"]
        .sum()
        .reset_index(name="income")
        .sort_values("income", ascending=False)
        .head(n)
    )
    out["income_fmt"] = out["income"].apply(format_currency)
    out["merchant"] = out["merchant"].replace("", "(Unknown)")
    return out


def _top_expenses(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Group by merchant; negative amounts only (most “expense-like”).
    Output is negative numbers (keeps sign).
    """
    if df.empty or "amount" not in df.columns:
        return pd.DataFrame()

    dfx = df.copy()
    dfx["merchant"] = dfx.get("merchant", "").fillna("").astype(str).str.strip()
    amounts = pd.to_numeric(dfx["amount"], errors="coerce").fillna(0.0)

    neg = dfx.loc[amounts < 0].copy()
    if neg.empty:
        return pd.DataFrame()

    ex_mask = build_exclusion_mask(neg)
    neg = neg.loc[~ex_mask].copy()
    if neg.empty:
        return pd.DataFrame()

    neg_amounts = pd.to_numeric(neg["amount"], errors="coerce").fillna(0.0)

    out = (
        neg.assign(_amt=neg_amounts)
        .groupby("merchant")["_amt"]
        .sum()
        .reset_index(name="expense")
        .sort_values("expense")  # most negative first
        .head(n)
    )
    out["expense_fmt"] = out["expense"].apply(format_currency)
    out["merchant"] = out["merchant"].replace("", "(Unknown)")
    return out


def _most_frequent_expenses(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    if df.empty or "amount" not in df.columns:
        return pd.DataFrame()

    dfx = df.copy()
    dfx["merchant"] = dfx.get("merchant", "").fillna("").astype(str).str.strip()
    amounts = pd.to_numeric(dfx["amount"], errors="coerce").fillna(0.0)

    neg = dfx.loc[amounts < 0].copy()
    if neg.empty:
        return pd.DataFrame()

    ex_mask = build_exclusion_mask(neg)
    neg = neg.loc[~ex_mask].copy()
    if neg.empty:
        return pd.DataFrame()

    out = (
        neg.groupby("merchant")
        .size()
        .reset_index(name="occurrences")
        .sort_values("occurrences", ascending=False)
        .head(n)
    )
    out["merchant"] = out["merchant"].replace("", "(Unknown)")
    return out


# =====================================================================
# UI: Main Dashboard
# =====================================================================

def render_dashboard_tab(transactions: pd.DataFrame) -> None:
    """
    Full-file Dashboard implementation:
    - Ledger-style date preset system (no Apply button; auto recalculates)
    - Snapshot metrics (income/expenses/net) via canonical cash_flow
    - Snapshot Details (top income sources, top expenses, most frequent expenses)
    - Monthly cash flow chart (Income vs Net Expenses + optional Net Cash line)
    - Rolling smoothing net cash trend (3- and 6-month)
    - Category contribution (net impact)
    - Category volatility (monthly net std dev)
    - Exclusions audit + excluded totals
    """
    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    tx = _ensure_datetime(_coerce_df(transactions))
    if tx.empty or "amount" not in tx.columns:
        st.info("No transactions available. Upload Monarch CSVs to begin.")
        return

    # -----------------------------
    # Date system (Ledger-style)
    # -----------------------------
    filtered_tx, start_date, end_date = _render_date_controls(tx)

    # Date Range display (always visible)
    st.caption("Date Range")
    if start_date and end_date:
        st.caption(format_date_range((start_date, end_date)))
    else:
        rng = _min_max_dates(tx)
        if rng:
            st.caption(format_date_range(rng))

    if filtered_tx.empty:
        st.warning("No transactions match the current date range selection.")
        return

    # -----------------------------
    # Snapshot (canonical)
    # -----------------------------
    result = compute_cash_flow(filtered_tx)

    st.markdown("## Snapshot")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("Income", format_currency(result.income))
    with s2:
        st.metric("Expenses", format_currency(result.net_expenses))
    with s3:
        st.metric("Net Cash Flow", format_currency(result.net_cash))

    # -----------------------------
    # Snapshot Details
    # -----------------------------
    st.markdown("## Snapshot Details")

    top_income = _top_income_sources(filtered_tx, n=5)
    top_exp = _top_expenses(filtered_tx, n=5)
    freq_exp = _most_frequent_expenses(filtered_tx, n=5)

    d1, d2, d3 = st.columns(3)

    with d1:
        st.markdown("### Top Income Sources")
        if top_income.empty:
            st.info("No income rows detected in this date range.")
        else:
            chart = (
                alt.Chart(top_income)
                .mark_bar()
                .encode(
                    y=alt.Y("merchant:N", sort="-x", title=None),
                    x=alt.X("income:Q", title="Income"),
                    tooltip=[
                        alt.Tooltip("merchant:N", title="Source"),
                        alt.Tooltip("income_fmt:N", title="Income"),
                    ],
                )
                .properties(height=260)
            )
            st.altair_chart(chart, use_container_width=True)

    with d2:
        st.markdown("### Top Expenses")
        if top_exp.empty:
            st.info("No expense rows detected in this date range.")
        else:
            chart = (
                alt.Chart(top_exp)
                .mark_bar()
                .encode(
                    y=alt.Y("merchant:N", sort="x", title=None),
                    x=alt.X("expense:Q", title="Expense"),
                    tooltip=[
                        alt.Tooltip("merchant:N", title="Payee"),
                        alt.Tooltip("expense_fmt:N", title="Expense"),
                    ],
                )
                .properties(height=260)
            )
            st.altair_chart(chart, use_container_width=True)

    with d3:
        st.markdown("### Most Frequent Expenses")
        if freq_exp.empty:
            st.info("No frequent expense rows detected in this date range.")
        else:
            chart = (
                alt.Chart(freq_exp)
                .mark_bar()
                .encode(
                    y=alt.Y("merchant:N", sort="-x", title=None),
                    x=alt.X("occurrences:Q", title="Occurrences"),
                    tooltip=[
                        alt.Tooltip("merchant:N", title="Merchant"),
                        alt.Tooltip("occurrences:Q", title="Count"),
                    ],
                )
                .properties(height=260)
            )
            st.altair_chart(chart, use_container_width=True)

    st.divider()

    # -----------------------------
    # Monthly Charts (canonical)
    # -----------------------------
    monthly_long = _monthly_cash_flow_frame(filtered_tx)
    if not monthly_long.empty:
        st.markdown("## Cash Flow Charts (Canonical)")

        show_net = st.toggle(
            "Show Net Cash line overlay",
            value=True,
            key="dash_cf_net_overlay",
            help="Net Cash = Income - Net Expenses (canonical).",
        )

        bars_source = monthly_long[monthly_long["metric"].isin(["Income", "Net Expenses"])].copy()

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

        if show_net:
            net_source = monthly_long[monthly_long["metric"] == "Net Cash"].copy()
            net_line = (
                alt.Chart(net_source)
                .mark_line(point=True)
                .encode(
                    x=alt.X("month_start:T", title="Month"),
                    y=alt.Y("value:Q", title="Amount"),
                    tooltip=[
                        alt.Tooltip("month_start:T", title="Month"),
                        alt.Tooltip("value_fmt:N", title="Net Cash"),
                    ],
                )
            )
            st.altair_chart(bar_chart + net_line, use_container_width=True)
        else:
            st.altair_chart(bar_chart, use_container_width=True)
    else:
        st.info("Not enough monthly data to render cash flow charts for this selection.")

    st.divider()

    # -----------------------------
    # Rolling smoothing (net cash)
    # -----------------------------
    st.markdown("## Net Cash Trend (Rolling Smoothing)")

    rolling = _monthly_net_cash_only(filtered_tx)
    if rolling.empty or len(rolling) < 2:
        st.info("Not enough monthly data for rolling analysis.")
    else:
        base = alt.Chart(rolling).encode(
            x=alt.X("month_start:T", title="Month")
        )

        bars = base.mark_bar(opacity=0.35).encode(
            y=alt.Y("net_cash:Q", title="Net Cash"),
            tooltip=[
                alt.Tooltip("month_start:T", title="Month"),
                alt.Tooltip("net_cash_fmt:N", title="Net Cash"),
            ],
        )

        line_3 = base.mark_line(point=True).encode(
            y=alt.Y("roll_3:Q", title="Rolling Avg"),
            tooltip=[alt.Tooltip("roll_3:Q", title="3-Month Avg")],
        )

        line_6 = base.mark_line(strokeDash=[6, 3]).encode(
            y=alt.Y("roll_6:Q"),
            tooltip=[alt.Tooltip("roll_6:Q", title="6-Month Avg")],
        )

        st.altair_chart(bars + line_3 + line_6, use_container_width=True)
        st.caption(
            "Interpretation: Rolling averages smooth short-term volatility to reveal underlying cash flow trends."
        )

    st.divider()

    # -----------------------------
    # Category Contribution (net impact)
    # -----------------------------
    st.markdown("## Category Contribution (Net Impact)")

    if "category" in filtered_tx.columns:
        contrib = (
            filtered_tx.groupby("category", dropna=False)
            .apply(lambda g: compute_cash_flow(g).net_cash)
            .reset_index(name="net_cash")
            .sort_values("net_cash")
        )
        contrib["category"] = contrib["category"].fillna("").astype(str).str.strip().replace("", "(Uncategorized)")
        contrib["net_cash_fmt"] = contrib["net_cash"].apply(format_currency)

        if not contrib.empty:
            chart = (
                alt.Chart(contrib)
                .mark_bar()
                .encode(
                    y=alt.Y("category:N", sort=alt.SortField("net_cash"), title=None),
                    x=alt.X("net_cash:Q", title="Net Cash Impact"),
                    tooltip=[
                        alt.Tooltip("category:N", title="Category"),
                        alt.Tooltip("net_cash_fmt:N", title="Net Impact"),
                    ],
                )
                .properties(height=360)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No category contribution data available.")
    else:
        st.info("Category field not found in transactions.")

    st.divider()

    # -----------------------------
    # Category Volatility (monthly net std dev)
    # -----------------------------
    st.markdown("## Category Volatility (Monthly Net)")

    volatility = _category_volatility_frame(filtered_tx)
    if volatility.empty:
        st.info("Not enough data to compute category volatility.")
    else:
        vol_chart = (
            alt.Chart(volatility)
            .mark_bar()
            .encode(
                y=alt.Y(
                    "category:N",
                    sort=alt.SortField("volatility", order="descending"),
                    title=None,
                ),
                x=alt.X("volatility:Q", title="Volatility (Std Dev)"),
                tooltip=[
                    alt.Tooltip("category:N", title="Category"),
                    alt.Tooltip("volatility_fmt:N", title="Volatility"),
                    alt.Tooltip("avg_net_fmt:N", title="Avg Monthly Net"),
                    alt.Tooltip("months:Q", title="Months Observed"),
                ],
            )
            .properties(height=360)
        )
        st.altair_chart(vol_chart, use_container_width=True)

        with st.expander("Show category volatility table", expanded=False):
            st.dataframe(
                volatility[["category", "avg_net", "volatility", "months"]],
                use_container_width=True,
            )

    st.divider()

    # -----------------------------
    # Exclusions audit (canonical)
    # -----------------------------
    st.markdown("## Exclusions Audit")

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
