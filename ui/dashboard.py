"""
Dashboard Tab (Core Rebuild) — Ledger-Style Date Preset Bar

This file intentionally:
- DOES NOT use year tabs (ALL YEARS / 2026 / 2025 ...) on Dashboard.
- DOES use a single active date range selection that drives all metrics/charts.
- DOES rely on canonical cash flow logic (src.cash_flow) for all calculations.

Dashboard is date-range driven.
Transactions tab is where year tabs live.
"""

from __future__ import annotations

from datetime import date as date_cls, timedelta
import pandas as pd
import streamlit as st
import altair as alt

from src.formatting import format_currency, format_date_range
from src.cash_flow import compute_cash_flow, build_exclusion_mask


# -----------------------------
# Session keys
# -----------------------------
_DASH_RANGE_PRESET_KEY = "dashboard_range_preset"
_DASH_CUSTOM_RANGE_KEY = "dashboard_custom_range"  # tuple[date, date]


# -----------------------------
# Helpers
# -----------------------------
def _coerce_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    return pd.DataFrame(df).copy()


def _derive_data_bounds(df: pd.DataFrame) -> tuple[date_cls, date_cls] | None:
    if df.empty or "date" not in df.columns:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return dates.min().date(), dates.max().date()


def _resolve_preset_range(preset: str, *, anchor_end: date_cls) -> tuple[date_cls, date_cls]:
    """
    anchor_end is the effective "today" for this dataset, typically max(date) in the CSV.
    """
    if preset == "Last 7 Days":
        return anchor_end - timedelta(days=6), anchor_end
    if preset == "Last 30 Days":
        return anchor_end - timedelta(days=29), anchor_end
    if preset == "Last 90 Days":
        return anchor_end - timedelta(days=89), anchor_end
    if preset == "Last 180 Days":
        return anchor_end - timedelta(days=179), anchor_end
    if preset == "Last Full Year":
        prior_year = anchor_end.year - 1
        return date_cls(prior_year, 1, 1), date_cls(prior_year, 12, 31)

    # Custom Range is handled elsewhere
    return anchor_end, anchor_end


def _filter_by_date_range(df: pd.DataFrame, start: date_cls, end: date_cls) -> pd.DataFrame:
    if df.empty or "date" not in df.columns:
        return df
    dates = pd.to_datetime(df["date"], errors="coerce")
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    return df.loc[(dates >= start_ts) & (dates <= end_ts)]


def _monthly_cash_flow_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Monthly Income / Net Expenses / Net Cash using canonical cash flow,
    computed by grouping the already-date-filtered scoped_tx.
    """
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    work = df.copy()
    work["month_start"] = pd.to_datetime(work["date"]).dt.to_period("M").dt.to_timestamp()

    rows = []
    for month, month_df in work.groupby("month_start"):
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
    long = wide.melt(
        id_vars="month_start",
        value_vars=["Income", "Net Expenses", "Net Cash"],
        var_name="metric",
        value_name="value",
    )
    long["value_fmt"] = long["value"].apply(format_currency)
    return long


def _monthly_net_cash_wide(df: pd.DataFrame) -> pd.DataFrame:
    """
    Wide monthly net cash frame for rolling smoothing.
    """
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    work = df.copy()
    work["month_start"] = pd.to_datetime(work["date"]).dt.to_period("M").dt.to_timestamp()

    rows = []
    for month, month_df in work.groupby("month_start"):
        r = compute_cash_flow(month_df)
        rows.append({"month_start": month, "net_cash": r.net_cash})

    out = pd.DataFrame(rows).sort_values("month_start")
    if out.empty:
        return out
    out["net_cash_fmt"] = out["net_cash"].apply(format_currency)
    out["roll_3"] = out["net_cash"].rolling(window=3, min_periods=1).mean()
    out["roll_6"] = out["net_cash"].rolling(window=6, min_periods=1).mean()
    out["roll_3_fmt"] = out["roll_3"].apply(format_currency)
    out["roll_6_fmt"] = out["roll_6"].apply(format_currency)
    return out


def _category_monthly_net_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Monthly net cash impact per category using canonical cash flow.
    """
    if df.empty or "category" not in df.columns or "date" not in df.columns:
        return pd.DataFrame()

    work = df.copy()
    work["month_start"] = pd.to_datetime(work["date"]).dt.to_period("M").dt.to_timestamp()

    rows = []
    for (category, month), group in work.groupby(["category", "month_start"]):
        r = compute_cash_flow(group)
        rows.append(
            {
                "category": category or "(Uncategorized)",
                "month_start": month,
                "net_cash": r.net_cash,
            }
        )

    return pd.DataFrame(rows)


def _category_volatility_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Volatility = standard deviation of monthly net cash per category.
    """
    monthly = _category_monthly_net_frame(df)
    if monthly.empty:
        return pd.DataFrame()

    agg = (
        monthly.groupby("category")["net_cash"]
        .agg(avg_net="mean", volatility="std", months="count")
        .reset_index()
    )

    agg["avg_net_fmt"] = agg["avg_net"].apply(format_currency)
    agg["volatility_fmt"] = agg["volatility"].fillna(0.0).apply(format_currency)

    return agg.sort_values("volatility", ascending=False)


def _init_dashboard_range_state(bounds: tuple[date_cls, date_cls]) -> None:
    """
    Initialize dashboard range state once we know data bounds.
    Default preset = Last 90 Days anchored to max date in CSV.
    """
    min_d, max_d = bounds

    if _DASH_RANGE_PRESET_KEY not in st.session_state:
        st.session_state[_DASH_RANGE_PRESET_KEY] = "Last 90 Days"

    if _DASH_CUSTOM_RANGE_KEY not in st.session_state:
        # Default custom range = full data bounds
        st.session_state[_DASH_CUSTOM_RANGE_KEY] = (min_d, max_d)

    # If stored custom range is outside bounds, clamp it
    try:
        c0, c1 = st.session_state[_DASH_CUSTOM_RANGE_KEY]
        c0 = max(min_d, c0)
        c1 = min(max_d, c1)
        if c0 > c1:
            c0, c1 = min_d, max_d
        st.session_state[_DASH_CUSTOM_RANGE_KEY] = (c0, c1)
    except Exception:
        st.session_state[_DASH_CUSTOM_RANGE_KEY] = (min_d, max_d)


def _get_active_date_range(bounds: tuple[date_cls, date_cls]) -> tuple[str, tuple[date_cls, date_cls]]:
    """
    Returns (preset_label, (start_date, end_date)).
    Auto recalculates on selection.
    """
    min_d, max_d = bounds
    _init_dashboard_range_state(bounds)

    preset_options = [
        "Last 7 Days",
        "Last 30 Days",
        "Last 90 Days",
        "Last 180 Days",
        "Last Full Year",
        "Custom Range",
    ]

    # Ledger-style horizontal selector
    preset = st.radio(
        "Date Range Presets",
        preset_options,
        index=preset_options.index(st.session_state[_DASH_RANGE_PRESET_KEY])
        if st.session_state[_DASH_RANGE_PRESET_KEY] in preset_options
        else 2,
        horizontal=True,
        label_visibility="collapsed",
        key="dash_preset_radio",
    )
    st.session_state[_DASH_RANGE_PRESET_KEY] = preset

    if preset == "Custom Range":
        c0, c1 = st.session_state[_DASH_CUSTOM_RANGE_KEY]
        picked = st.date_input(
            "Custom Date Range",
            value=(c0, c1),
            min_value=min_d,
            max_value=max_d,
            key="dash_custom_date_input",
        )
        # Streamlit may return a single date if mis-clicked; normalize
        if isinstance(picked, tuple) and len(picked) == 2:
            start, end = picked
        else:
            start, end = c0, c1

        # Clamp + order
        start = max(min_d, start)
        end = min(max_d, end)
        if start > end:
            start, end = end, start

        st.session_state[_DASH_CUSTOM_RANGE_KEY] = (start, end)
        return preset, (start, end)

    start, end = _resolve_preset_range(preset, anchor_end=max_d)
    # Clamp to bounds
    start = max(min_d, start)
    end = min(max_d, end)
    if start > end:
        start, end = min_d, max_d
    return preset, (start, end)


# -----------------------------
# UI
# -----------------------------
def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str] | None = None,  # intentionally unused on Dashboard now
    date_range: tuple[date_cls, date_cls] | None = None,  # intentionally unused (dashboard drives its own range)
) -> None:
    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    # Ledger-style reset button (kept on Dashboard)
    if st.button("Reset Dashboard", key="dash_reset_btn"):
        st.session_state.clear()
        st.rerun()

    tx = _coerce_df(transactions)
    bounds = _derive_data_bounds(tx)

    if tx.empty or bounds is None or "amount" not in tx.columns:
        st.info("Upload Monarch CSVs to view the dashboard.")
        return

    preset_label, (start_d, end_d) = _get_active_date_range(bounds)

    st.caption(f"Scope: {preset_label}")
    st.caption("Date Range")
    st.caption(format_date_range((start_d, end_d)))

    # Filtered scope drives everything below
    scoped_tx = _filter_by_date_range(tx, start_d, end_d)

    if scoped_tx.empty:
        st.warning("No transactions found in the selected date range.")
        return

    # -----------------------------
    # Canonical Cash Flow
    # -----------------------------
    result = compute_cash_flow(scoped_tx)

    st.markdown("### Snapshot (Canonical Cash Flow)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Income", format_currency(result.income))
    with c2:
        st.metric("Expenses", format_currency(result.net_expenses))
    with c3:
        st.metric("Net Cash", format_currency(result.net_cash))

    st.caption(
        f"Expense offsets (positive non-income): {format_currency(result.expense_offsets)} | "
        f"Gross expenses: {format_currency(result.gross_expenses)}"
    )

    st.divider()

    # -----------------------------
    # Monthly Charts (Canonical)
    # -----------------------------
    monthly_long = _monthly_cash_flow_frame(scoped_tx)

    if not monthly_long.empty:
        st.markdown("### Cash Flow Charts (Canonical)")

        show_net = st.toggle(
            "Show Net Cash line overlay",
            value=True,
            key="dash_cf_show_net_toggle",
        )

        bars = monthly_long[monthly_long["metric"].isin(["Income", "Net Expenses"])]

        bar_chart = (
            alt.Chart(bars)
            .mark_bar()
            .encode(
                x=alt.X("month_start:T", title="Month"),
                xOffset="metric:N",
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
            net_line = (
                alt.Chart(monthly_long[monthly_long["metric"] == "Net Cash"])
                .mark_line(point=True)
                .encode(
                    x="month_start:T",
                    y="value:Q",
                    tooltip=[
                        alt.Tooltip("month_start:T", title="Month"),
                        alt.Tooltip("value_fmt:N", title="Net Cash"),
                    ],
                )
            )
            st.altair_chart(bar_chart + net_line, use_container_width=True)
        else:
            st.altair_chart(bar_chart, use_container_width=True)

    st.divider()

    # -----------------------------
    # Rolling Smoothing (ADD — does not replace anything)
    # -----------------------------
    st.markdown("### Net Cash Trend (Rolling Smoothing)")

    monthly_net = _monthly_net_cash_wide(scoped_tx)
    if monthly_net.empty or len(monthly_net) < 2:
        st.info("Not enough monthly data for rolling analysis.")
    else:
        base = alt.Chart(monthly_net).encode(x=alt.X("month_start:T", title="Month"))

        bars = base.mark_bar(opacity=0.35).encode(
            y=alt.Y("net_cash:Q", title="Net Cash"),
            tooltip=[
                alt.Tooltip("month_start:T", title="Month"),
                alt.Tooltip("net_cash_fmt:N", title="Net Cash"),
            ],
        )

        line_3 = base.mark_line(point=True).encode(
            y=alt.Y("roll_3:Q", title="Rolling Avg"),
            tooltip=[alt.Tooltip("roll_3_fmt:N", title="3-Month Avg")],
        )

        line_6 = base.mark_line(strokeDash=[6, 3]).encode(
            y=alt.Y("roll_6:Q"),
            tooltip=[alt.Tooltip("roll_6_fmt:N", title="6-Month Avg")],
        )

        st.altair_chart(bars + line_3 + line_6, use_container_width=True)

        st.caption(
            "Interpretation: Rolling averages smooth short-term volatility to reveal underlying cash flow trends."
        )

    st.divider()

    # -----------------------------
    # Category Contribution (Net Impact)
    # -----------------------------
    st.markdown("### Category Contribution (Net Impact)")

    if "category" in scoped_tx.columns:
        contrib = (
            scoped_tx.groupby("category", dropna=False)
            .apply(lambda g: compute_cash_flow(g).net_cash)
            .reset_index(name="net_cash")
            .sort_values("net_cash")
        )
        contrib["net_cash_fmt"] = contrib["net_cash"].apply(format_currency)

        if not contrib.empty:
            chart = (
                alt.Chart(contrib)
                .mark_bar()
                .encode(
                    y=alt.Y("category:N", sort=alt.SortField("net_cash")),
                    x=alt.X("net_cash:Q", title="Net Cash Impact"),
                    tooltip=[
                        alt.Tooltip("category:N", title="Category"),
                        alt.Tooltip("net_cash_fmt:N", title="Net Impact"),
                    ],
                )
                .properties(height=350)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No category contribution data available for this range.")
    else:
        st.info("Category column not found; cannot compute contribution chart.")

    st.divider()

    # -----------------------------
    # Category Volatility (Monthly Net)
    # -----------------------------
    st.markdown("### Category Volatility (Monthly Net)")

    volatility = _category_volatility_frame(scoped_tx)

    if volatility.empty:
        st.info("Not enough data to compute volatility.")
    else:
        vol_chart = (
            alt.Chart(volatility)
            .mark_bar()
            .encode(
                y=alt.Y(
                    "category:N",
                    sort=alt.SortField("volatility", order="descending"),
                    title="Category",
                ),
                x=alt.X("volatility:Q", title="Volatility (Std Dev)"),
                tooltip=[
                    alt.Tooltip("category:N", title="Category"),
                    alt.Tooltip("volatility_fmt:N", title="Volatility"),
                    alt.Tooltip("avg_net_fmt:N", title="Avg Monthly Net"),
                    alt.Tooltip("months:Q", title="Months Observed"),
                ],
            )
            .properties(height=350)
        )
        st.altair_chart(vol_chart, use_container_width=True)

        with st.expander("Show category volatility table", expanded=False):
            st.dataframe(volatility[["category", "avg_net", "volatility", "months"]], use_container_width=True)

    st.divider()

    # -----------------------------
    # Exclusions Audit
    # -----------------------------
    mask = build_exclusion_mask(scoped_tx)
    excluded_amounts = pd.to_numeric(scoped_tx.loc[mask, "amount"], errors="coerce").fillna(0.0)

    st.markdown(f"**Excluded totals:** {format_currency(float(excluded_amounts.sum()))}")

    with st.expander("Show excluded rows (audit)", expanded=False):
        cols = [c for c in ["date", "merchant", "category", "amount"] if c in scoped_tx.columns]
        st.dataframe(scoped_tx.loc[mask, cols], use_container_width=True, hide_index=True)
