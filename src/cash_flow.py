"""
CORE CASH FLOW — CANONICAL LOGIC

Single source of truth for income, expense, and net cash flow.

RULES (DEFAULT BEHAVIOR)
- Exclusions are CATEGORY-driven (transaction_type is ignored)
- Exclude: Transfers, Credit Card Payments
- Refunds are NOT excluded (they offset expenses when positive)
- Income = POSITIVE amounts that match income-like category/keywords
- Positive non-income amounts are EXPENSE OFFSETS (reduce expenses, not income)

ENHANCEMENT 2 — USER OVERRIDES
- Optional JSON rules file can override:
  - excluded categories
  - force-income categories
  - force-non-income categories (treat positive as offsets)
  - income category keywords / income text keywords

ENHANCEMENT 3 — AUDITABILITY / ROBUSTNESS
- Canonical classification helper `classify_transactions()`:
  - returns masks for excluded / income / offsets / expense rows
  - returns rollups for dashboard auditing
- UI MUST use this helper (no re-deriving logic in UI)

DO NOT
- Recalculate income/expenses elsewhere
- Use transaction_type for exclusion logic
- Bypass this module for UI metrics

Any changes here require explicit audit validation + tests updates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import json
import pandas as pd


# -----------------------------
# Normalization helpers
# -----------------------------

def _norm(val: object) -> str:
    return " ".join(str(val or "").lower().replace("_", " ").replace("-", " ").split())


def _norm_set(values: Any) -> set[str]:
    if not values:
        return set()
    if isinstance(values, (set, tuple, list)):
        return {_norm(v) for v in values if str(v).strip()}
    return {_norm(values)}


# -----------------------------
# Rules (defaults + overrides)
# -----------------------------

@dataclass(frozen=True)
class CashFlowRules:
    excluded_categories: set[str] = field(default_factory=set)
    force_income_categories: set[str] = field(default_factory=set)
    force_non_income_categories: set[str] = field(default_factory=set)
    income_category_keywords: set[str] = field(default_factory=set)
    income_text_keywords: set[str] = field(default_factory=set)


DEFAULT_RULES = CashFlowRules(
    excluded_categories={"transfer", "credit card payment"},
    force_income_categories=set(),
    force_non_income_categories=set(),
    income_category_keywords={
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
    },
    income_text_keywords={
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
    },
)


def _merge_rules(base: CashFlowRules, override: dict[str, Any]) -> CashFlowRules:
    exc = set(base.excluded_categories) | _norm_set(override.get("excluded_categories"))
    finc = set(base.force_income_categories) | _norm_set(override.get("force_income_categories"))
    fnon = set(base.force_non_income_categories) | _norm_set(override.get("force_non_income_categories"))
    cat_kw = set(base.income_category_keywords) | _norm_set(override.get("income_category_keywords"))
    txt_kw = set(base.income_text_keywords) | _norm_set(override.get("income_text_keywords"))

    if override.get("replace_excluded_categories") is True:
        exc = _norm_set(override.get("excluded_categories"))
    if override.get("replace_force_income_categories") is True:
        finc = _norm_set(override.get("force_income_categories"))
    if override.get("replace_force_non_income_categories") is True:
        fnon = _norm_set(override.get("force_non_income_categories"))
    if override.get("replace_income_category_keywords") is True:
        cat_kw = _norm_set(override.get("income_category_keywords"))
    if override.get("replace_income_text_keywords") is True:
        txt_kw = _norm_set(override.get("income_text_keywords"))

    return CashFlowRules(
        excluded_categories=exc,
        force_income_categories=finc,
        force_non_income_categories=fnon,
        income_category_keywords=cat_kw,
        income_text_keywords=txt_kw,
    )


def resolve_rules_path(path: str | None = None) -> Path | None:
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    candidates.append(Path("cash_flow_rules.json"))
    candidates.append(Path("config") / "cash_flow_rules.json")

    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def load_cash_flow_rules(path: str | None = None) -> tuple[CashFlowRules, str | None]:
    resolved = resolve_rules_path(path)
    if resolved is None:
        return DEFAULT_RULES, None

    raw = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return DEFAULT_RULES, str(resolved)

    return _merge_rules(DEFAULT_RULES, raw), str(resolved)


# -----------------------------
# Masks (exclusion + income-like)
# -----------------------------

def build_exclusion_mask(df: pd.DataFrame, rules: CashFlowRules | None = None) -> pd.Series:
    r = rules or DEFAULT_RULES

    if df is None or df.empty:
        return pd.Series(False, index=getattr(df, "index", None))

    if "category" in df.columns:
        cat_norm = df["category"].apply(_norm)
        return cat_norm.isin(r.excluded_categories)

    scan_cols = [c for c in ["merchant", "notes", "original_statement"] if c in df.columns]
    if scan_cols:
        haystack = (
            df[scan_cols]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .apply(_norm)
        )
        return haystack.apply(lambda txt: any(k in txt for k in r.excluded_categories))

    return pd.Series(False, index=df.index)


def _income_category_signal(df: pd.DataFrame, rules: CashFlowRules) -> pd.Series:
    if "category" not in df.columns:
        return pd.Series(False, index=df.index)

    cat_norm = df["category"].apply(_norm)

    forced_income = cat_norm.isin(rules.force_income_categories)
    forced_non_income = cat_norm.isin(rules.force_non_income_categories)
    keyword_income = cat_norm.apply(lambda s: any(k in s for k in rules.income_category_keywords))

    return (forced_income | keyword_income) & (~forced_non_income)


def _income_keyword_signal(df: pd.DataFrame, rules: CashFlowRules) -> pd.Series:
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
    return haystack.apply(lambda s: any(k in s for k in rules.income_text_keywords))


def _income_confidence_counts(
    *,
    income_mask: pd.Series,
    category_signal: pd.Series,
    keyword_signal: pd.Series,
) -> tuple[int, int, int]:
    high = int((income_mask & category_signal).sum())
    med = int((income_mask & ~category_signal & keyword_signal).sum())
    low = int((income_mask & ~category_signal & ~keyword_signal).sum())
    return high, med, low


# -----------------------------
# Canonical classification output
# -----------------------------

@dataclass(frozen=True)
class CashFlowAudit:
    included_rows: int
    excluded_rows: int

    income_rows: int
    offset_rows: int
    expense_rows: int

    income_total: float
    offset_total: float
    gross_expenses_total: float
    excluded_total: float

    income_conf_high: int
    income_conf_med: int
    income_conf_low: int


@dataclass(frozen=True)
class CashFlowClassification:
    exclusion_mask: pd.Series
    included_mask: pd.Series
    income_mask: pd.Series
    offset_mask: pd.Series
    expense_mask: pd.Series
    audit: CashFlowAudit


def classify_transactions(transactions: pd.DataFrame, rules: CashFlowRules | None = None) -> CashFlowClassification:
    r = rules or DEFAULT_RULES

    if transactions is None or transactions.empty or "amount" not in transactions.columns:
        empty_index = getattr(transactions, "index", pd.RangeIndex(0))
        false = pd.Series(False, index=empty_index)
        audit = CashFlowAudit(
            included_rows=0,
            excluded_rows=0,
            income_rows=0,
            offset_rows=0,
            expense_rows=0,
            income_total=0.0,
            offset_total=0.0,
            gross_expenses_total=0.0,
            excluded_total=0.0,
            income_conf_high=0,
            income_conf_med=0,
            income_conf_low=0,
        )
        return CashFlowClassification(
            exclusion_mask=false,
            included_mask=false,
            income_mask=false,
            offset_mask=false,
            expense_mask=false,
            audit=audit,
        )

    df = pd.DataFrame(transactions).copy()
    amounts = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    exclusion_mask = build_exclusion_mask(df, rules=r)
    included_mask = ~exclusion_mask

    included_df = df.loc[included_mask]
    included_amounts = amounts.loc[included_mask]

    pos_mask = included_amounts > 0
    neg_mask = included_amounts < 0

    category_signal = _income_category_signal(included_df, r)
    keyword_signal = _income_keyword_signal(included_df, r)

    income_mask = pos_mask & (category_signal | keyword_signal)
    offset_mask = pos_mask & (~income_mask)
    expense_mask = neg_mask

    income_total = float(included_amounts.loc[income_mask].sum())
    offset_total = float(included_amounts.loc[offset_mask].sum())
    gross_expenses_total = float((-included_amounts.loc[expense_mask]).sum())

    excluded_total = float(amounts.loc[exclusion_mask].sum())

    conf_high, conf_med, conf_low = _income_confidence_counts(
        income_mask=income_mask,
        category_signal=category_signal,
        keyword_signal=keyword_signal,
    )

    audit = CashFlowAudit(
        included_rows=int(included_mask.sum()),
        excluded_rows=int(exclusion_mask.sum()),
        income_rows=int(income_mask.sum()),
        offset_rows=int(offset_mask.sum()),
        expense_rows=int(expense_mask.sum()),
        income_total=income_total,
        offset_total=offset_total,
        gross_expenses_total=gross_expenses_total,
        excluded_total=excluded_total,
        income_conf_high=conf_high,
        income_conf_med=conf_med,
        income_conf_low=conf_low,
    )

    # Return masks aligned to original df index (for UI slicing)
    full_income_mask = pd.Series(False, index=df.index)
    full_offset_mask = pd.Series(False, index=df.index)
    full_expense_mask = pd.Series(False, index=df.index)

    full_income_mask.loc[included_df.index] = income_mask
    full_offset_mask.loc[included_df.index] = offset_mask
    full_expense_mask.loc[included_df.index] = expense_mask

    return CashFlowClassification(
        exclusion_mask=exclusion_mask,
        included_mask=included_mask,
        income_mask=full_income_mask,
        offset_mask=full_offset_mask,
        expense_mask=full_expense_mask,
        audit=audit,
    )


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


def compute_cash_flow(transactions: pd.DataFrame, rules: CashFlowRules | None = None) -> CashFlowResult:
    classification = classify_transactions(transactions, rules=rules)
    a = classification.audit

    net_expenses = float(a.gross_expenses_total - a.offset_total)
    net_cash = float(a.income_total - net_expenses)

    return CashFlowResult(
        income=float(a.income_total),
        gross_expenses=float(a.gross_expenses_total),
        expense_offsets=float(a.offset_total),
        net_expenses=net_expenses,
        net_cash=net_cash,
        included_rows=int(a.included_rows),
        excluded_rows=int(a.excluded_rows),
        income_conf_high=int(a.income_conf_high),
        income_conf_med=int(a.income_conf_med),
        income_conf_low=int(a.income_conf_low),
    )





