"""
CORE CASH FLOW — CANONICAL LOGIC

This module defines the single source of truth for income, expense,
and net cash flow calculations across the entire application.

RULES:
- Exclusions are CATEGORY-driven for non-cash-flow rows (transfers/CC payments)
- Income = sum(positive amounts WHERE category is an income category)
- Expense offsets = sum(positive amounts WHERE category is NOT an income category)
  (e.g., refunds/returns categorized as Shopping offset Shopping spend)
- Gross expenses = sum(abs(negative amounts))
- Net expenses = gross expenses - expense offsets
- Net cash = income + expense offsets - gross expenses

IMPORTANT:
- transaction_type is intentionally ignored for exclusions/income classification
- Keyword fallback applies only if category is missing
- All dashboards, charts, and exports MUST consume this logic

DO NOT:
- Recalculate income/expenses elsewhere
- Use transaction_type for exclusion logic
- Bypass this module for UI metrics

Any changes here require explicit audit validation + unit test updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


def _norm(val: object) -> str:
    return " ".join(str(val or "").lower().replace("_", " ").replace("-", " ").split())


# Exclude rows that are not meaningful cash flow for spend/income metrics
DEFAULT_EXCLUDED_CATEGORIES: set[str] = {
    "transfer",
    "credit card payment",
}

# Categories treated as true income when amount > 0
DEFAULT_INCOME_CATEGORIES: set[str] = {
    "salary",
    "wages",
    "paycheck",
    "income",
    "bonus",
    "interest",
    "dividend",
    "dividends",
    "investment income",
}


@dataclass(frozen=True)
class CashFlowResult:
    income: float
    gross_expenses: float
    expense_offsets: float
    net_expenses: float
    net_cash: float
    included_rows: int
    excluded_rows: int


def build_exclusion_mask(
    df: pd.DataFrame,
    *,
    excluded_categories: Iterable[str] | None = None,
) -> pd.Series:
    """
    Exclude rows based on Category first (Monarch-authoritative),
    with keyword fallback if Category is missing.
    """
    if df is None or df.empty:
        return pd.Series(False, index=getattr(df, "index", None))

    excluded = {_norm(x) for x in (excluded_categories or DEFAULT_EXCLUDED_CATEGORIES)}

    if "category" in df.columns:
        cat_norm = df["category"].apply(_norm)
        return cat_norm.isin(excluded)

    scan_cols = [c for c in ["merchant", "notes", "original_statement"] if c in df.columns]
    if scan_cols:
        haystack = (
            df[scan_cols]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .apply(_norm)
        )
        return haystack.apply(lambda txt: any(x in txt for x in excluded))

    return pd.Series(False, index=df.index)


def compute_cash_flow(
    df: pd.DataFrame,
    *,
    excluded_categories: Iterable[str] | None = None,
    income_categories: Iterable[str] | None = None,
) -> CashFlowResult:
    """
    Compute canonical cash flow metrics.

    - Income: positive amounts where category is an income category
    - Expense offsets: positive amounts where category is NOT an income category
    - Gross expenses: abs(negative amounts)
    - Net expenses: gross expenses - expense offsets
    - Net cash: income + offsets - gross expenses
    """
    if df is None or df.empty or "amount" not in df.columns:
        return CashFlowResult(
            income=0.0,
            gross_expenses=0.0,
            expense_offsets=0.0,
            net_expenses=0.0,
            net_cash=0.0,
            included_rows=0,
            excluded_rows=0,
        )

    working = pd.DataFrame(df).copy()

    amounts = pd.to_numeric(working["amount"], errors="coerce").fillna(0.0)

    exclusion_mask = build_exclusion_mask(working, excluded_categories=excluded_categories)
    included_mask = ~exclusion_mask

    included_amounts = amounts.loc[included_mask]

    income_cats = {_norm(x) for x in (income_categories or DEFAULT_INCOME_CATEGORIES)}

    # Determine category membership for "income category" logic
    if "category" in working.columns:
        cat_norm = working["category"].apply(_norm).loc[included_mask]
    else:
        # If category is missing, we conservatively treat positives as offsets (not income)
        cat_norm = pd.Series([""] * int(included_mask.sum()), index=included_amounts.index)

    pos_mask = included_amounts > 0
    neg_mask = included_amounts < 0

    income_mask = pos_mask & cat_norm.isin(income_cats)
    offset_mask = pos_mask & ~income_mask

    income = float(included_amounts.loc[income_mask].sum())
    gross_expenses = float((-included_amounts.loc[neg_mask]).sum())
    expense_offsets = float(included_amounts.loc[offset_mask].sum())

    net_expenses = float(gross_expenses - expense_offsets)
    net_cash = float(income + expense_offsets - gross_expenses)

    return CashFlowResult(
        income=income,
        gross_expenses=gross_expenses,
        expense_offsets=expense_offsets,
        net_expenses=net_expenses,
        net_cash=net_cash,
        included_rows=int(included_mask.sum()),
        excluded_rows=int(exclusion_mask.sum()),
    )

