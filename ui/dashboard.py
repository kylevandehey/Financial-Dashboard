from src.config import ALL_YEARS_LABEL
from src.formatting import format_currency, format_date_range
from src.metrics import (
    build_category_breakdown,
    build_monthly_cash_flow,
    build_yearly_balance_trends,
    build_yearly_income_expense,
    get_balances_snapshot,
    summarize_cash_flow,
    summarize_accounts,
)

_QUARTER_MONTHS: dict[str, set[int]] = {
    "Q1": {1, 2, 3},
    "Q2": {4, 5, 6},
    "Q3": {7, 8, 9},
    "Q4": {10, 11, 12},
}


def _make_section_id(section: str, year_label: str, selected_period: str) -> str:
    normalized = f"{section}_{year_label}_{selected_period}".lower().replace(" ", "_")
    return f"dashboard_{normalized}"


def _safe_key(prefix: str, section_id: str | None) -> str:
    sid = (section_id or "default").strip().replace(" ", "_")
    return f"{prefix}__{sid}"


def _coerce_dataframe(data: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Return a copy of the incoming data or an empty frame."""
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def _currency_axis(title: str | None = None) -> alt.Axis:
    """Altair axis with accounting-style label formatting."""
    return alt.Axis(
        title=title,
        labelExpr=(
            "datum.value < 0 "
            "? '($' + format(-datum.value, ',.2f') + ')' "
            ": '$' + format(datum.value, ',.2f')"
        ),
    )


def _render_header(
    year_label: str,
    selected_period: str,
    date_range: tuple[date, date],
) -> None:
    st.markdown("### Dashboard Overview")
    st.caption(f"Scope: {year_label} · Period: {selected_period}")
    st.caption("Date Range")
    st.caption(format_date_range(date_range))


def _render_data_grid(
    df: pd.DataFrame,
    *,
    title: str,
    section_id: str | None,
    height: int | None = None,
) -> None:
    row_count = len(df.index) if df is not None else 0
    header = f"{title} ({row_count} rows)"

    if section_id is None:
        st.markdown(f"**{header}**")
        st.dataframe(df, use_container_width=True, height=height)
        return

    expander_key = _safe_key("grid", section_id)
    expanded_default = st.session_state.get(expander_key, False)

    with st.expander(header, expanded=expanded_default, key=expander_key):
        st.dataframe(df, use_container_width=True, height=height)
