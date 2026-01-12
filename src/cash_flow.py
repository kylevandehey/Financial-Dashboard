"""
CORE CASH FLOW — CANONICAL LOGIC

Single source of truth for income, expense, and net cash flow.

RULES
- Exclusions are CATEGORY-driven (transaction_type is ignored)
- Exclude: Transfers, Credit Card Payments
- Refunds are NOT excluded (they offset expenses when positive)
- Income = POSITIVE amounts that match income-like category/keywords
- Positive non-income amounts are EXPENSE OFFSETS (reduce expenses, not income)

DO NOT
- Recalculate income/expenses elsewhere
- Use transaction_type for exclusion logic
- Bypass this module for UI metrics

Any changes here require explicit audit validation + tests updates.
"""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


# -----------------------------
# Normalization helpers
# -----------------------------

def _norm(val: object) -> str:
    return " ".join(str(val or "").lower().replace("_", " ").replace("-", " ").split())


# -----------------------------
# Category-driven exclusions
# -----------------------------

_EXCLUDED_CATEGORIES = {
    "transfer",
    "credit card payment",
}


def build_exclusion_mask(df: pd.DataFrame) -> pd.Series:
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

_INCOME_CATEGORY_KEYWORDS = {
    "income",
    "salary",
    "pay",
    "paycheck",
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
}

_INCOME_TEXT_KEYWORDS = {
    "payroll",
    "paycheck",
    "direct deposit",
    "salary",
    "wage",
    "bonus",
    "commission",
    "reimbursement",
    "employer",
    "paystub",
}


def _income_category_mask(df: pd.DataFrame) -> pd.Series:
    if "category" not in df.columns:
        return pd.Series(False, index=df.index)
    cat_norm = df["category"].apply(_norm)
    return cat_norm.apply(lambda s: any(k in s for k in _INCOME_CATEGORY_KEYWORDS))


def _income_keyword_mask(df: pd.DataFrame) -> pd.Series:
    scan_cols = [c for c in ["merchant", "notes", "original_statement"] if c in df.columns]
    if not scan_cols:
        return pd.Series(False, index=df.index)

    haystack = (
        df[scan_cols]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .apply(_norm)
    )
    return haystack.apply(lambda s: any(k in s for k in _INCOME_TEXT_KEYWORDS))


def _income_confidence_counts(
    *,
    included_mask: pd.Series,
    income_mask: pd.Series,
    category_mask: pd.Series,
    keyword_mask: pd.Series,
) -> tuple[int, int, int]:
    base = included_mask & income_mask
    high = int((base & category_mask).sum())
    med = int((base & ~category_mask & keyword_mask).sum())
    low = int((base & ~category_mask & ~keyword_mask).sum())
    return high, med, low


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
    income_conf_high: int
    income_conf_med: int
    income_conf_low: int


def compute_cash_flow(transactions: pd.DataFrame) -> CashFlowResult:
    if transactions is None or transactions.empty or "amount" not in transactions.columns:
        return CashFlowResult(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    df = pd.DataFrame(transactions).copy()
    amounts = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    exclusion_mask = build_exclusion_mask(df)
    included_mask = ~exclusion_mask

    included_df = df.loc[included_mask]
    included_amounts = amounts.loc[included_mask]

    pos_mask = included_amounts > 0
    neg_mask = included_amounts < 0

    category_income_mask = _income_category_mask(included_df)
    keyword_income_mask = _income_keyword_mask(included_df)

    income_mask = pos_mask & (category_income_mask | keyword_income_mask)
    offset_mask = pos_mask & (~income_mask)

    income = float(included_amounts.loc[income_mask].sum())
    gross_expenses = float((-included_amounts.loc[neg_mask]).sum())
    expense_offsets = float(included_amounts.loc[offset_mask].sum())

    net_expenses = float(gross_expenses - expense_offsets)
    net_cash = float(income - net_expenses)

    conf_high, conf_med, conf_low = _income_confidence_counts(
        included_mask=included_mask.loc[included_df.index],
        income_mask=income_mask,
        category_mask=category_income_mask,
        keyword_mask=keyword_income_mask,
    )

    return CashFlowResult(
        income=income,
        gross_expenses=gross_expenses,
        expense_offsets=expense_offsets,
        net_expenses=net_expenses,
        net_cash=net_cash,
        included_rows=int(included_mask.sum()),
        excluded_rows=int(exclusion_mask.sum()),
        income_conf_high=conf_high,
        income_conf_med=conf_med,
        income_conf_low=conf_low,
    )



