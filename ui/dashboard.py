import streamlit as st
import pandas as pd
from datetime import date

from src.formatting import format_currency, format_date_range
from src.cash_flow import (
    compute_cash_flow,
    classify_transactions,
    load_cash_flow_rules,
)


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


@st.cache_data(show_spinner=False)
def _get_rules_cached(rules_path_hint: str | None) -> tuple[object, str]:
    rules, resolved_path = load_cash_flow_rules(rules_path_hint)
    return rules, (resolved_path or "DEFAULT_RULES (no file found)")


def _safe_cols(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


def _rules_json_template_from_data(df: pd.DataFrame) -> str:
    """
    Generate a starter JSON template based on observed categories.
    This does NOT auto-write rules; it just produces copy/paste guidance.
    """
    categories = []
    if "category" in df.columns and not df.empty:
        categories = (
            df["category"]
            .fillna("")
            .astype(str)
            .str.strip()
            .loc[lambda s: s.ne("")]
            .value_counts()
            .head(25)
            .index
            .tolist()
        )

    template = {
        "excluded_categories": [
            "transfer",
            "credit card payment"
        ],
        "force_income_categories": [
            "income",
            "salary",
            "paycheck"
        ],
        "force_non_income_categories": [
            "shopping",
            "groceries",
            "restaurants"
        ],
        "income_text_keywords": [
            "direct deposit",
            "payroll"
        ],
        "_notes": {
            "observed_top_categories_sample": categories[:15],
            "tips": [
                "Add categories you want excluded entirely to excluded_categories.",
                "Add categories that represent true income (paycheck, salary, interest, dividends) to force_income_categories.",
                "Add categories where positive amounts should be treated as offsets (returns, reimbursements categorized to spending buckets) to force_non_income_categories.",
                "Use replace_* flags only if you want to fully replace defaults rather than extend them."
            ]
        }
    }

    import json
    return json.dumps(template, indent=2)


def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
    date_range: tuple[date, date] | None = None,
) -> None:
    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    rules_path_hint = None
    rules, rules_source = _get_rules_cached(rules_path_hint)
    st.caption(f"Cash Flow Rules Source: {rules_source}")

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

            # Canonical engine
            result = compute_cash_flow(scoped_tx, rules=rules)
            classification = classify_transactions(scoped_tx, rules=rules)
            audit = classification.audit

            st.markdown("### Key Metrics (Core Cash Flow)")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Income", format_currency(result.income))
            with c2:
                st.metric("Expenses", format_currency(result.net_expenses))
            with c3:
                st.metric("Net", format_currency(result.net_cash))

            st.caption(
                f"Income confidence → High:{result.income_conf_high} | "
                f"Medium:{result.income_conf_med} | Low:{result.income_conf_low}"
            )

            st.divider()
            st.markdown("### Classification Audit (Robustness Layer)")

            a1, a2, a3, a4 = st.columns(4)
            with a1:
                st.metric("Included Rows", f"{audit.included_rows:,}")
            with a2:
                st.metric("Excluded Rows", f"{audit.excluded_rows:,}")
            with a3:
                st.metric("Income Rows", f"{audit.income_rows:,}")
            with a4:
                st.metric("Offset Rows", f"{audit.offset_rows:,}")

            b1, b2, b3, b4 = st.columns(4)
            with b1:
                st.metric("Income Total", format_currency(audit.income_total))
            with b2:
                st.metric("Offsets Total", format_currency(audit.offset_total))
            with b3:
                st.metric("Gross Expenses", format_currency(audit.gross_expenses_total))
            with b4:
                st.metric("Excluded Net", format_currency(audit.excluded_total))

            st.caption(
                "Interpretation: Offsets are positive non-income transactions (returns/reimbursements) "
                "that reduce expenses rather than inflating income."
            )

            st.divider()

            # Excluded totals line (requested previously)
            excluded_amounts = pd.to_numeric(scoped_tx.loc[classification.exclusion_mask, "amount"], errors="coerce").fillna(0.0)
            excluded_net = float(excluded_amounts.sum())
            excluded_pos = float(excluded_amounts[excluded_amounts > 0].sum())
            excluded_neg_abs = float((-excluded_amounts[excluded_amounts < 0]).sum())

            st.markdown(
                f"**Excluded totals:** {format_currency(excluded_net)} "
                f"({format_currency(excluded_pos)} / {format_currency(-excluded_neg_abs)})"
            )

            with st.expander("Show excluded rows (audit)", expanded=False):
                cols = _safe_cols(scoped_tx, ["date", "merchant", "category", "notes", "amount"])
                st.dataframe(scoped_tx.loc[classification.exclusion_mask, cols], use_container_width=True)

            with st.expander("Show income rows (audit)", expanded=False):
                cols = _safe_cols(scoped_tx, ["date", "merchant", "category", "notes", "amount"])
                st.dataframe(scoped_tx.loc[classification.income_mask, cols], use_container_width=True)

            with st.expander("Show offset rows (audit)", expanded=False):
                cols = _safe_cols(scoped_tx, ["date", "merchant", "category", "notes", "amount"])
                st.dataframe(scoped_tx.loc[classification.offset_mask, cols], use_container_width=True)

            with st.expander("Rules helper (generate a starter cash_flow_rules.json)", expanded=False):
                st.caption(
                    "If income or offsets look wrong for a user, add a cash_flow_rules.json file "
                    "to override categories/keywords without changing application code."
                )
                st.code(_rules_json_template_from_data(scoped_tx), language="json")







