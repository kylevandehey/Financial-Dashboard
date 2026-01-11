"""
CANONICAL CASH FLOW ENGINE

Single source of truth for all income, expense, and net calculations.

RULES:
- Income = sum(amount > 0)
- Expenses = sum(abs(amount < 0))
- Exclusions are CATEGORY-driven
- transaction_type is intentionally ignored
- Keyword fallback applies if category is missing

ALL dashboards, charts, exports, and reports MUST call this module.
"""

import pandas as pd
from typing import TypedDict


class CashFlowResult(TypedDict):
    income: float
    expenses: float
    net: float
    included_rows: int
    excluded_rows: int
    excluded_positive: float
    excluded_negative: float
    excluded_total: float
    exclusion_mask: pd.Series


def _norm(val: object) -> str:
    return " ".join(
        str(val or "")
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def build_exclusion_mask(df: pd.DataFrame) -> pd.Series:
    """
    CATEGORY-first exclusion logic.
    """
    if df.empty:
        return pd.Series(False, index=df.index)

    excluded_categories = {
        "transfer",
        "credit card payment",
        "refund",
    }

    if "category" in df.columns:
        cat_norm = df["category"].apply(_norm)
        return cat_norm.isin(excluded_categories)

    scan_cols = [c for c in ["merchant", "notes", "original_statement"] if c in df.columns]
    if scan_cols:
        haystack = (
            df[scan_cols]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .apply(_norm)
        )
        return haystack.apply(
            lambda txt: any(x in txt for x in excluded_categories)
        )

    return pd.Series(False, index=df.index)


def calculate_cash_flow(df: pd.DataFrame) -> CashFlowResult:
    """
    Canonical cash flow calculation.
    """
    if df.empty or "amount" not in df.columns:
        return {
            "income": 0.0,
            "expenses": 0.0,
            "net": 0.0,
            "included_rows": 0,
            "excluded_rows": 0,
            "excluded_positive": 0.0,
            "excluded_negative": 0.0,
            "excluded_total": 0.0,
            "exclusion_mask": pd.Series(dtype=bool),
        }

    amounts = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    exclusion_mask = build_exclusion_mask(df)

    included = amounts.loc[~exclusion_mask]
    excluded = amounts.loc[exclusion_mask]

    income = float(included[included > 0].sum())
    expenses = float((-included[included < 0]).sum())
    net = float(income - expenses)

    return {
        "income": income,
        "expenses": expenses,
        "net": net,
        "included_rows": int((~exclusion_mask).sum()),
        "excluded_rows": int(exclusion_mask.sum()),
        "excluded_positive": float(excluded[excluded > 0].sum()),
        "excluded_negative": float(excluded[excluded < 0].sum()),
        "excluded_total": float(excluded.sum()),
        "exclusion_mask": exclusion_mask,
    }
