"""
CORE CASH FLOW — CANONICAL LOGIC

Single source of truth for income, expense, and net cash flow.

RULES
- Exclusions are CATEGORY-driven (transaction_type is ignored)
- Exclude: Transfers, Credit Card Payments
- Refunds are NOT excluded (they should offset expenses when positive)
- Income is POSITIVE amounts that match income-like category/keywords
- Positive non-income amounts are EXPENSE OFFSETS (reduce expenses, not counted as income)

DO NOT
- Recalculate income/expenses elsewhere
- Use transaction_type for exclusion logic
- Bypass this module for UI metrics

Any changes here require explicit audit validation + tests updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


# -----------------------------
# Normalization helpers
# -----------------------------

def _norm(val: object) -> str:
    return " ".join(str(val or "").lower().replace("_", " ").replace("-", " ").split())


# -----------------------------
# Category-driven exclusions
# -----------------------------

# NOTE: Refunds intentionally NOT excluded.
_EXCLUDED_CATEGORIES = {
    "transfer",
    "credit card payment",
}


def build_exclusion_mask(df: pd.DataFrame) -> pd.Series:
    """
    Category-authoritative exclusion mask.
    - Uses `category` first
    - Ignores transaction_type entirely
    - Falls back to keyword scan if category missing
    """
    if df is None or df.empty:
        return pd.Series(False, index=getattr(df, "index", None))

    if "category" in df.columns:
        cat_norm = df["category"].apply(_norm)
        return cat_norm.isin(_EXCLUDED_CATEGORIES)

    scan_cols = [c for c in ["merchant", "notes", "original_statement"] if c in df.columns]
    if scan_cols:
        haystack = (
            df[scan_cols]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .apply(_norm)
        )
        return haystack.apply(lambda txt: any(k in txt for k in _EXCLUDED_CATEGORIES))

    return pd.Series(False, index=df.index)


# -----------------------------
# Income detection
# -----------------------------

# These are not "categories you personally use"—they are common English patterns we can safely generalize.
# They are used as *signals*; category is preferred, but we also scan text fields.
_INCOME_CATEGORY_KEYWORDS = {
    "income",
    "salary",
    "pay",
    "paycheck",
    "pay roll",
    "payroll",
    "wage",
    "wages",
    "bonus",
    "commission",
    "reimbursement",
    "reimburs",
    "dividend",
    "interest",
    "distribution",
    "refund from employer",
}

_INCOME_TEXT_KEYWORDS = {
    "payroll",
    "paycheck",
    "direct deposit",
    "dd ",
    "salary",
    "wage",
    "bonus",
    "commission",
    "reimbursement",
    "reimburs",
    "employer",
    "paystub",
    "bhsach",  # your payroll descriptor example (safe as additive signal, not required)
}


def _is_income_row(df: pd.DataFrame) -> pd.Series:
    """
    Returns a boolean mask where rows are "income-like".
    Strategy:
    1) Category keyword match (preferred)
    2) Fallback scan merchant/notes/original_statement
    """
    if df is None or df.empty:
        return pd.Series(False, index=getattr(df, "index", None))

    mask = pd.Series(False, index=df.index)

    if "category" in df.columns:
        cat_norm = df["category"].apply(_norm)
        mask = mask | cat_norm.apply(lambda s: any(k in s for k in _INCOME_CATEGORY_KEYWORDS))

    scan_cols = [c for c in ["merchant", "notes", "original_statement"] if c in df.columns]
    if scan_cols:
        haystack = (
            df[scan_cols]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .apply(_norm)
        )
        mask = mask | haystack.apply(lambda s: any(k in s for k in _INCOME_TEXT_KEYWORDS))

    return mask


# -----------------------------
# Cash flow computation
# -----------------------------

@dataclass(frozen=True)
class CashFlowResult:
    income: float
    gross_expenses: float
    expense_offsets: float
    net_expenses: float
    net_cash: float
    included_rows: int
    excluded_rows: int


def compute_cash_flow(transactions: pd.DataFrame) -> CashFlowResult:
    """
    Compute cash flow for a set of transactions.

    Included rows:
    - everything EXCEPT excluded categories (transfer, credit card payment)

    Income:
    - positive amounts that are income-like

    Expense offsets:
    - positive amounts that are NOT income-like (reduces expenses)

    Expenses:
    - abs(sum(negative amounts)) minus expense_offsets
    """
    if transactions is None or transactions.empty or "amount" not in transactions.columns:
        return CashFlowResult(
            income=0.0,
            gross_expenses=0.0,
            expense_offsets=0.0,
            net_expenses=0.0,
            net_cash=0.0,
            included_rows=0,
            excluded_rows=0,
        )

    df = pd.DataFrame(transactions).copy()

    amounts = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    exclusion_mask = build_exclusion_mask(df)
    included_mask = ~exclusion_mask

    included_amounts = amounts.loc[included_mask]
    included_df = df.loc[included_mask]

    pos_mask = included_amounts > 0
    neg_mask = included_amounts < 0

    income_like_mask = _is_income_row(included_df)

    income_mask = pos_mask & income_like_mask
    offset_mask = pos_mask & (~income_like_mask)

    income = float(included_amounts.loc[income_mask].sum())
    gross_expenses = float((-included_amounts.loc[neg_mask]).sum())
    expense_offsets = float(included_amounts.loc[offset_mask].sum())

    net_expenses = float(gross_expenses - expense_offsets)
    net_cash = float(income - net_expenses)

    return CashFlowResult(
        income=income,
        gross_expenses=gross_expenses,
        expense_offsets=expense_offsets,
        net_expenses=net_expenses,
        net_cash=net_cash,
        included_rows=int(included_mask.sum()),
        excluded_rows=int(exclusion_mask.sum()),
    )


