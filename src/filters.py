"""Transaction filtering utilities shared across Monarch+ tabs.

Business rules for transaction inclusion/exclusion live here so that Streamlit
surfaces stay thin and declarative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import pandas as pd


def _normalize_keywords(raw_keywords: Iterable[str]) -> list[str]:
    return [kw.strip() for kw in raw_keywords if kw and kw.strip()]


@dataclass
class TransactionFilterConfig:
    excluded_types: set[str] = field(default_factory=set)
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_keyword_strings(
        cls,
        *,
        excluded_types: Iterable[str] | None = None,
        include_keywords: str | Sequence[str] | None = None,
        exclude_keywords: str | Sequence[str] | None = None,
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
        )

    def normalized_excluded_types(self) -> set[str]:
        return {t.lower() for t in self.excluded_types if t}

    def normalized_include_keywords(self) -> list[str]:
        return [kw.lower() for kw in self.include_keywords if kw]

    def normalized_exclude_keywords(self) -> list[str]:
        return [kw.lower() for kw in self.exclude_keywords if kw]


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
        excluded = config.normalized_excluded_types()
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
