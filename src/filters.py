"""Transaction filtering utilities shared across Control Tower tabs.

Business rules for transaction inclusion/exclusion live here so that Streamlit
surfaces stay thin and declarative.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Optional, Sequence

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL
from src.date_filters import filter_dataframe_by_date_and_month

TX_FILTER_STATE_KEY = "tx_filters"
_TX_FILTER_CONFIG_CACHE: TransactionFilterConfig | None = None


def _normalize_keywords(raw_keywords: Iterable[str]) -> list[str]:
    return [kw.strip() for kw in raw_keywords if kw and kw.strip()]


@dataclass
class TransactionFilterConfig:
    excluded_types: set[str] = field(default_factory=set)
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    include_transfers: bool = True
    include_refunds: bool = True

    @classmethod
    def from_keyword_strings(
        cls,
        *,
        excluded_types: Iterable[str] | None = None,
        include_keywords: str | Sequence[str] | None = None,
        exclude_keywords: str | Sequence[str] | None = None,
        include_transfers: bool = True,
        include_refunds: bool = True,
    ) -> "TransactionFilterConfig":
        include_list = []
        if isinstance(include_keywords, str):
            include_list = [part.strip() for part in include_keywords.split(",")]
        elif include_keywords:
            include_list = list(include_keywords)

        exclude_list: list[str] = []
        if isinstance(exclude_keywords, str):
            exclude_list = [part.strip() for part in exclude_keywords.split(",")]
        elif exclude_keywords:
            exclude_list = list(exclude_keywords)

        return cls(
            excluded_types=set(excluded_types or set()),
            include_keywords=_normalize_keywords(include_list),
            exclude_keywords=_normalize_keywords(exclude_list),
            include_transfers=bool(include_transfers),
            include_refunds=bool(include_refunds),
        )

    def normalized_excluded_types(self) -> set[str]:
        return {t.lower() for t in self.excluded_types if t}

    def normalized_include_keywords(self) -> list[str]:
        return [kw.lower() for kw in self.include_keywords if kw]

    def normalized_exclude_keywords(self) -> list[str]:
        return [kw.lower() for kw in self.exclude_keywords if kw]

    def excluded_types_with_toggles(self) -> set[str]:
        base_excluded = self.normalized_excluded_types()
        if not self.include_transfers:
            base_excluded.add("transfer")
        if not self.include_refunds:
            base_excluded.add("refund")
        return base_excluded


def apply_transaction_config(transactions: pd.DataFrame, config: TransactionFilterConfig) -> pd.DataFrame:
    """Apply inclusion/exclusion rules to a transactions DataFrame.

    This function never mutates the input DataFrame and gracefully handles
    missing columns by returning the original DataFrame unchanged.
    """

    if transactions is None or transactions.empty or config is None:
        return transactions

    df = transactions.copy()

    if "transaction_type" in df.columns:
        normalized_types = df["transaction_type"].fillna("").astype(str).str.lower()
        excluded = config.excluded_types_with_toggles()
        if excluded:
            df = df.loc[~normalized_types.isin(excluded)]

    haystack = (
        df[[col for col in ["merchant", "notes", "category"] if col in df.columns]]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .str.lower()
    )

    include_terms = config.normalized_include_keywords()
    if include_terms:
        include_mask = haystack.apply(lambda text: any(term in text for term in include_terms))
        df = df.loc[include_mask]

    exclude_terms = config.normalized_exclude_keywords()
    if exclude_terms:
        exclude_mask = haystack.apply(lambda text: any(term in text for term in exclude_terms))
        df = df.loc[~exclude_mask]

    return df.reset_index(drop=True)


def set_transaction_filter_config(config: TransactionFilterConfig) -> None:
    """Persist the provided filter config to session state and cache."""
    global _TX_FILTER_CONFIG_CACHE
    _TX_FILTER_CONFIG_CACHE = config
    st.session_state[TX_FILTER_STATE_KEY] = config


def get_transaction_filter_config() -> TransactionFilterConfig:
    """Return the active transaction filter config from session state or cache."""
    stored_config = st.session_state.get(TX_FILTER_STATE_KEY, _TX_FILTER_CONFIG_CACHE)
    if isinstance(stored_config, TransactionFilterConfig):
        # Backward compatibility for session state objects created before toggle flags existed.
        if not hasattr(stored_config, "include_transfers"):
            stored_config.include_transfers = True
        if not hasattr(stored_config, "include_refunds"):
            stored_config.include_refunds = True
        return stored_config
    return TransactionFilterConfig()


def reset_transaction_filter_config() -> None:
    """Clear stored transaction filter configuration from session state."""
    global _TX_FILTER_CONFIG_CACHE
    _TX_FILTER_CONFIG_CACHE = None
    if TX_FILTER_STATE_KEY in st.session_state:
        st.session_state.pop(TX_FILTER_STATE_KEY, None)


def get_filtered_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    """Centralized transaction filtering that reads from session state."""
    if transactions is None or transactions.empty:
        return transactions

    stored_config = get_transaction_filter_config()
    set_transaction_filter_config(stored_config)

    return apply_transaction_config(transactions, stored_config)


def period_options_for_scope(year_label: str) -> list[str]:
    """Return the allowed period options for a given year tab."""
    return ["ALL YEARS", "Q1", "Q2", "Q3", "Q4"] if str(year_label).upper() == ALL_YEARS_LABEL else ["FULL YEAR", "Q1", "Q2", "Q3", "Q4"]


def _normalize_year_label(year_label: Optional[str]) -> Optional[int]:
    if year_label is None or str(year_label).upper() == ALL_YEARS_LABEL:
        return None
    try:
        return int(year_label)
    except (TypeError, ValueError):
        return None


def _quarter_months(period_label: str) -> set[int]:
    return {
        "Q1": {1, 2, 3},
        "Q2": {4, 5, 6},
        "Q3": {7, 8, 9},
        "Q4": {10, 11, 12},
    }.get(period_label.upper(), set())


def _available_date_bounds(df: pd.DataFrame) -> tuple[date, date]:
    today = date.today()
    if df is None or df.empty or "date" not in df.columns:
        return today, today

    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return today, today

    return dates.min().date(), dates.max().date()


def compute_scope_date_range(
    transactions: pd.DataFrame,
    *,
    year_label: str,
    period_label: str,
    fallback_df: pd.DataFrame | None = None,
) -> tuple[date, date]:
    """Compute the date bounds for the selected year and period."""
    working_df = transactions if transactions is not None else pd.DataFrame()
    lower, upper = _available_date_bounds(working_df)
    if working_df.empty and fallback_df is not None:
        lower, upper = _available_date_bounds(fallback_df)
    normalized_year = _normalize_year_label(year_label)
    period = period_label.upper()

    if normalized_year is None and period == "ALL YEARS":
        return lower, upper

    if normalized_year is None and period.startswith("Q"):
        quarter_mask = _quarter_months(period)
        if not working_df.empty and "date" in working_df.columns:
            dates = pd.to_datetime(working_df["date"], errors="coerce")
            quarter_dates = dates.loc[dates.dt.month.isin(quarter_mask)].dropna()
            if not quarter_dates.empty:
                return quarter_dates.min().date(), quarter_dates.max().date()
        return lower, upper

    if normalized_year is not None:
        start_of_year = date(normalized_year, 1, 1)
        end_of_year = date(normalized_year, 12, 31)
        if period in {"FULL YEAR", "ALL YEARS"}:
            return start_of_year, end_of_year
        if period.startswith("Q"):
            months = _quarter_months(period)
            if not months:
                return start_of_year, end_of_year
            start_month = min(months)
            end_month = max(months)
            start_date = date(normalized_year, start_month, 1)
            last_day = monthrange(normalized_year, end_month)[1]
            end_candidates = date(normalized_year, end_month, last_day)
            return start_date, end_candidates

    return lower, upper


def filter_transactions_for_scope(
    transactions: pd.DataFrame,
    *,
    year_label: str,
    period_label: str,
    date_range: Optional[Sequence[date]] = None,
) -> pd.DataFrame:
    """Return a canonical filtered transactions DataFrame for the given scope."""
    scoped = get_filtered_transactions(transactions)
    if scoped is None or scoped.empty:
        return pd.DataFrame()

    normalized_year = _normalize_year_label(year_label)
    if normalized_year is not None and "year" in scoped.columns:
        scoped = scoped.loc[scoped["year"] == normalized_year]

    months = _quarter_months(period_label)
    effective_range = date_range or compute_scope_date_range(scoped, year_label=year_label, period_label=period_label)
    try:
        start_date, end_date = effective_range
    except Exception:
        start_date, end_date = compute_scope_date_range(scoped, year_label=year_label, period_label=period_label)
    start_date = getattr(start_date, "date", lambda: start_date)()
    end_date = getattr(end_date, "date", lambda: end_date)()
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    filtered = filter_dataframe_by_date_and_month(
        scoped,
        (start_date, end_date),
        months=months,
        date_column="date",
    )
    return filtered.reset_index(drop=True)
