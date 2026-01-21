import streamlit as st
import pandas as pd
import altair as alt
from datetime import date

from src.formatting import format_currency, format_date_range
from src.cash_flow import compute_cash_flow, build_exclusion_mask


# -----------------------------
# Helpers (safe, UI-level only)
# -----------------------------

_INCOME_FALLBACK_KEYWORDS = (
    "income",
    "salary",
    "pay",
    "payroll",
    "paycheck",
    "wage",
    "wages",
    "bonus",
    "commission",
    "dividend",
    "interest",
    "distribution",
    "direct deposit",
)

def _coerce_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    return pd.DataFrame(df).copy()

def _safe_cols(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns]

def _derive_date_range(df: pd.DataFrame) -> tuple[date, date] | None:
    if df.empty or "date" not in df.columns:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return dates.min().date(), dates.max().date()

def _canonical_included_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    mask = build_exclusion_mask(df)
    return df.loc[~mask].copy()

def _get_classification_masks(df: pd.DataFrame) -> dict[str, pd.Series] | None:
    """
    Optional: If your cash_flow module exposes a classification helper, use it.
    Otherwise, fall back to simple heuristics for Snapshot Details.
    This is UI-only and does NOT override canonical totals (totals always come from compute_cash_flow).
    """
    try:
        # If you later add a canonical classifier (recommended), the UI will automatically benefit.
        from src.cash_flow import classify_transactions  # type: ignore
        classification = classify_transactions(df)  # expected to carry exclusion_mask/income_mask/offset_mask
        # Support either attribute style or dict style.
        if isinstance(classification, dict):
            return classification
        out = {}
        for k in ("exclusion_mask", "income_mask", "offset_mask"):
            if hasattr(classification, k):
                out[k] = getattr(classification, k)
        return out if out else None
    except Exception:
        return None

def _fallback_income_mask(included_df: pd.DataFrame) -> pd.Series:
    """
    Heuristic only (used for Snapshot Details ranking if no classifier exists).
    Income mask = positive + category/merchant/notes keyword match.
    """
    if included_df.empty or "amount" not in included_df.columns:
        return pd.Series(False, index=included_df.index)

    amt = pd.to_numeric(included_df["amount"], errors="coerce").fillna(0.0)
    pos = amt > 0

    hay_cols = _safe_cols(included_df, ["category", "merchant", "notes", "original_statement"])
    if not hay_cols:
        return pd.Series(False, index=included_df.index)

    hay = (
        included_df[hay_cols]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .str.lower()
    )
    kw = _INCOME_FALLBACK_KEYWORDS
    return pos & hay.apply(lambda s: any(k in s for k in kw))

def _snapshot_details_frames(scoped_tx: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns:
      - top_income_sources: merchant, total, total_fmt
      - top_expenses: merchant, total, total_fmt (negative totals)
      - frequent_expenses: merchant, occurrences
    Notes:
      - Exclusions removed (transfer/cc payment) using canonical exclusion mask
      - If a canonical classifier exists, income/offset masks are honored for "income sources"
      - Otherwise uses a conservative heuristic to avoid counting refunds as income
    """
    if scoped_tx.empty or "amount" not in scoped_tx.columns:
        empty = pd.DataFrame()
        return empty, empty, empty

    df = _canonical_included_df(scoped_tx)
    if df.empty:
        empty = pd.DataFrame()
        return empty, empty, empty

    df = df.copy()
    df["merchant"] = df.get("merchant", "").fillna("").astype(str).str.strip()
    df.loc[df["merchant"] == "", "merchant"] = "(Unknown)"

    amt = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    classification = _get_classification_masks(df)
    if classification and "income_mask" in classification:
        income_mask = classification["income_mask"].reindex(df.index, fill_value=False)
    else:
        income_mask = _fallback_income_mask(df)

    # Income sources (merchant totals)
    income_df = df.loc[income_mask].copy()
    if not income_df.empty:
        income_totals = (
            pd.to_numeric(income_df["amount"], errors="coerce").fillna(0.0)
            .groupby(income_df["merchant"])
            .sum()
            .reset_index(name="total")
            .sort_values("total", ascending=False)
            .head(5)
        )
        income_totals["total_fmt"] = income_totals["total"].apply(format_currency)
    else:
        income_totals = pd.DataFrame(columns=["merchant", "total", "total_fmt"])

    # Top expenses (merchant totals, most negative)
    exp_mask = amt < 0
    exp_df = df.loc[exp_mask].copy()
    if not exp_df.empty:
        exp_totals = (
            pd.to_numeric(exp_df["amount"], errors="coerce").fillna(0.0)
            .groupby(exp_df["merchant"])
            .sum()
            .reset_index(name="total")
            .sort_values("total", ascending=True)  # most negative first
            .head(5)
        )
        exp_totals["total_fmt"] = exp_totals["total"].apply(format_currency)
    else:
        exp_totals = pd.DataFrame(columns=["merchant", "total", "total_fmt"])

    # Most frequent expenses (count of negative rows by merchant)
    if not exp_df.empty:
        freq = (
            exp_df.groupby("merchant")
            .size()
            .reset_index(name="occurrences")
            .sort_values("occurrences", ascending=False)
            .head(5)
        )
    else:
        freq = pd.DataFrame(columns=["merchant", "occurrences"])

    return income_totals, exp_totals, freq

def _monthly_cash_flow_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Canonical monthly Income / Net Expenses / Net Cash (long format).
    """
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["month_start"] = pd.to_datetime(df["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    df = df.dropna(subset=["month_start"])
    if df.empty:
        return pd.DataFrame()

    rows = []
    for month, month_df in df.groupby("month_start"):
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

def _monthly_net_cash_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Canonical monthly Net Cash only (wide format).
    """
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["month_start"] = pd.to_datetime(df["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    df = df.dropna(subset=["month_start"])
    if df.empty:
        return pd.DataFrame()

    rows = []
    for month, month_df in df.groupby("month_start"):
        r = compute_cash_flow(month_df)
        rows.append({"month_start": month, "net_cash": r.net_cash})

    out = pd.DataFrame(rows).sort_values("month_start")
    out["net_cash_fmt"] = out["net_cash"].apply(format_currency)
    return out

def _apply_rolling(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=1).mean()

def _category_monthly_net_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Monthly net cash impact per category using canonical cash flow.
    """
    if df.empty or "category" not in df.columns or "date" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["category"] = df["category"].fillna("").astype(str).str.strip()
    df.loc[df["category"] == "", "category"] = "(Uncategorized)"
    df["month_start"] = pd.to_datetime(df["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    df = df.dropna(subset=["month_start"])
    if df.empty:
        return pd.DataFrame()

    rows = []
    for (category, month), group in df.groupby(["category", "month_start"]):
        r = compute_cash_flow(group)
        rows.append({"category": category, "month_start": month, "net_cash": r.net_cash})

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

def _widget_scope_key(prefix: str, scope_label: str, derived_range: tuple[date, date] | None) -> str:
    """
    Stable widget key per tab scope + applied date range.
    """
    if not derived_range:
        return f"{prefix}__{scope_label}__none"
    return f"{prefix}__{scope_label}__{derived_range[0].isoformat()}__{derived_range[1].isoformat()}"


# -----------------------------
# UI
# -----------------------------

def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
    date_range: tuple[date, date] | None = None,
    selected_preset: str | None = None,
) -> None:
    """
    Dashboard is intended to be fed a transaction DataFrame that has already been
    filtered by the Control Panel (date preset bar). This UI will display the
    applied range and compute all metrics canonically from that input.
    """
    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    # Display applied preset/range (selection UI lives in control_panel/main.py)
    applied_range = date_range or _derive_date_range(_coerce_df(transactions))
    if selected_preset:
        st.caption(f"Preset: {selected_preset}")
    if applied_range:
        st.caption("Date Range")
        st.caption(format_date_range(applied_range))

    # Keep tabs structurally for future expansion; for now, dashboard is scope-driven by date presets.
    # If you later reintroduce multiple scopes, this structure is already in place.
    year_tabs = st.tabs(available_years)

    for tab, year_label in zip(year_tabs, available_years):
        with tab:
            scoped_tx = _coerce_df(transactions)
            derived_range = _derive_date_range(scoped_tx)

            # -----------------------------
            # Canonical Cash Flow Snapshot
            # -----------------------------
            if scoped_tx.empty or "amount" not in scoped_tx.columns:
                st.info("No transactions in scope.")
                continue

            result = compute_cash_flow(scoped_tx)

            st.markdown("### Snapshot")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Income", format_currency(result.income))
            with c2:
                st.metric("Expenses", format_currency(result.net_expenses))
            with c3:
                st.metric("Net Cash Flow", format_currency(result.net_cash))

            # -----------------------------
            # Snapshot Details (Top 5s)
            # -----------------------------
            st.markdown("### Snapshot Details")

            top_income, top_expenses, freq_expenses = _snapshot_details_frames(scoped_tx)

            d1, d2, d3 = st.columns(3)

            with d1:
                st.markdown("**Top Income Sources**")
                if top_income.empty:
                    st.caption("No income-like rows detected in this range.")
                else:
                    chart = (
                        alt.Chart(top_income)
                        .mark_bar()
                        .encode(
                            y=alt.Y("merchant:N", sort="-x", title=None),
                            x=alt.X("total:Q", title="Income"),
                            tooltip=[
                                alt.Tooltip("merchant:N", title="Merchant"),
                                alt.Tooltip("total_fmt:N", title="Total"),
                            ],
                        )
                        .properties(height=220)
                    )
                    st.altair_chart(chart, use_container_width=True)

            with d2:
                st.markdown("**Top Expenses**")
                if top_expenses.empty:
                    st.caption("No expense rows detected in this range.")
                else:
                    chart = (
                        alt.Chart(top_expenses)
                        .mark_bar()
                        .encode(
                            y=alt.Y("merchant:N", sort="x", title=None),
                            x=alt.X("total:Q", title="Expense"),
                            tooltip=[
                                alt.Tooltip("merchant:N", title="Merchant"),
                                alt.Tooltip("total_fmt:N", title="Total"),
                            ],
                        )
                        .properties(height=220)
                    )
                    st.altair_chart(chart, use_container_width=True)

            with d3:
                st.markdown("**Most Frequent Expenses**")
                if freq_expenses.empty:
                    st.caption("No recurring expenses detected in this range.")
                else:
                    chart = (
                        alt.Chart(freq_expenses)
                        .mark_bar()
                        .encode(
                            y=alt.Y("merchant:N", sort="-x", title=None),
                            x=alt.X("occurrences:Q", title="Occurrences"),
                            tooltip=[
                                alt.Tooltip("merchant:N", title="Merchant"),
                                alt.Tooltip("occurrences:Q", title="Occurrences"),
                            ],
                        )
                        .properties(height=220)
                    )
                    st.altair_chart(chart, use_container_width=True)

            st.divider()

            # -----------------------------
            # Monthly Cash Flow Charts (Canonical)
            # -----------------------------
            monthly_long = _monthly_cash_flow_frame(scoped_tx)
            if not monthly_long.empty:
                st.markdown("### Cash Flow Charts (Canonical)")

                show_net = st.toggle(
                    "Show Net Cash line overlay",
                    value=True,
                    key=_widget_scope_key("cf_show_net", year_label, derived_range),
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

            st.divider()

            # -----------------------------
            # Net Cash Trend (Rolling Smoothing) - ADDITIVE
            # -----------------------------
            st.markdown("### Net Cash Trend (Rolling Smoothing)")

            monthly_net = _monthly_net_cash_frame(scoped_tx)
            if monthly_net.empty or len(monthly_net) < 2:
                st.info("Not enough monthly data for rolling analysis in this scope.")
            else:
                # 3-mo / 6-mo rolling averages
                monthly_net = monthly_net.copy()
                monthly_net["roll_3"] = _apply_rolling(monthly_net["net_cash"], 3)
                monthly_net["roll_6"] = _apply_rolling(monthly_net["net_cash"], 6)

                base = alt.Chart(monthly_net).encode(
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
                    y=alt.Y("roll_6:Q", title="Rolling Avg"),
                    tooltip=[alt.Tooltip("roll_6:Q", title="6-Month Avg")],
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
                contrib["category"] = contrib["category"].fillna("").astype(str).str.strip()
                contrib.loc[contrib["category"] == "", "category"] = "(Uncategorized)"
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
                        .properties(height=350)
                    )
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.caption("No category contribution data available for this scope.")
            else:
                st.caption("Category column not present; cannot compute category contribution.")

            st.divider()

            # -----------------------------
            # Category Volatility (Monthly Net)
            # -----------------------------
            st.markdown("### Category Volatility (Monthly Net)")

            volatility = _category_volatility_frame(scoped_tx)
            if volatility.empty:
                st.info("Not enough data to compute volatility in this scope.")
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
                    st.dataframe(
                        volatility[["category", "avg_net", "volatility", "months"]],
                        use_container_width=True,
                    )

            st.divider()

            # -----------------------------
            # Exclusions Audit (Canonical)
            # -----------------------------
            exclusion_mask = build_exclusion_mask(scoped_tx)
            excluded_amounts = pd.to_numeric(scoped_tx.loc[exclusion_mask, "amount"], errors="coerce").fillna(0.0)

            excluded_net = float(excluded_amounts.sum())
            excluded_pos = float(excluded_amounts[excluded_amounts > 0].sum())
            excluded_neg_abs = float((-excluded_amounts[excluded_amounts < 0]).sum())

            st.markdown(
                f"**Excluded totals:** {format_currency(excluded_net)} "
                f"({format_currency(excluded_pos)} / {format_currency(-excluded_neg_abs)})"
            )

            with st.expander("Show excluded rows (audit)", expanded=False):
                cols = _safe_cols(scoped_tx, ["date", "merchant", "category", "notes", "amount"])
                st.dataframe(scoped_tx.loc[exclusion_mask, cols], use_container_width=True)

            st.caption(
                f"Expense offsets: {format_currency(result.expense_offsets)} | "
                f"Gross expenses: {format_currency(result.gross_expenses)}"
            )
