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
    # Categories to exclude entirely (ignored in all calculations)
    excluded_categories: set[str] = field(default_factory=set)

    # Categories that FORCE positive amounts to be treated as income
    force_income_categories: set[str] = field(default_factory=set)

    # Categories that FORCE positive amounts to NOT be treated as income
    # (i.e., they become expense offsets when positive)
    force_non_income_categories: set[str] = field(default_factory=set)

    # Keyword signals (category-based and text-based)
    income_category_keywords: set[str] = field(default_factory=set)
    income_text_keywords: set[str] = field(default_factory=set)


DEFAULT_RULES = CashFlowRules(
    excluded_categories={
        "transfer",
        "credit card payment",
    },
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
    # All overrides are additive unless explicitly provided as full lists
    exc = set(base.excluded_categories) | _norm_set(override.get("excluded_categories"))
    finc = set(base.force_income_categories) | _norm_set(override.get("force_income_categories"))
    fnon = set(base.force_non_income_categories) | _norm_set(override.get("force_non_income_categories"))

    cat_kw = set(base.income_category_keywords) | _norm_set(override.get("income_category_keywords"))
    txt_kw = set(base.income_text_keywords) | _norm_set(override.get("income_text_keywords"))

    # Allow "replace_*" flags if user wants a full replacement rather than additive
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
    """
    Resolution order:
    1) explicit `path` argument if provided
    2) repo root: cash_flow_rules.json
    3) config/cash_flow_rules.json
    """
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
    """
    Loads optional JSON overrides. Returns (rules, resolved_path_str).
    If no file exists, returns DEFAULT_RULES.
    """
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


def _income_category_mask(df: pd.DataFrame, rules: CashFlowRules) -> pd.Series:
    if "category" not in df.columns:
        return pd.Series(False, index=df.index)

    cat_norm = df["category"].apply(_norm)

    # Forced classification has priority
    forced_income = cat_norm.isin(rules.force_income_categories)
    forced_non_income = cat_norm.isin(rules.force_non_income_categories)

    # Keyword signal (category-based)
    keyword_income = cat_norm.apply(lambda s: any(k in s for k in rules.income_category_keywords))

    # Forced non-income removes income classification
    return (forced_income | keyword_income) & (~forced_non_income)


def _income_keyword_mask(df: pd.DataFrame, rules: CashFlowRules) -> pd.Series:
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
    # High: category signal
    high = int((income_mask & category_signal).sum())
    # Medium: keyword signal only
    med = int((income_mask & ~category_signal & keyword_signal).sum())
    # Low: should be 0 with current detection, but retained for future expansions
    low = int((income_mask & ~category_signal & ~keyword_signal).sum())
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


def compute_cash_flow(transactions: pd.DataFrame, rules: CashFlowRules | None = None) -> CashFlowResult:
    r = rules or DEFAULT_RULES

    if transactions is None or transactions.empty or "amount" not in transactions.columns:
        return CashFlowResult(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    df = pd.DataFrame(transactions).copy()
    amounts = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    exclusion_mask = build_exclusion_mask(df, rules=r)
    included_mask = ~exclusion_mask

    included_df = df.loc[included_mask]
    included_amounts = amounts.loc[included_mask]

    pos_mask = included_amounts > 0
    neg_mask = included_amounts < 0

    category_income_signal = _income_category_mask(included_df, r)
    keyword_income_signal = _income_keyword_mask(included_df, r)

    income_mask = pos_mask & (category_income_signal | keyword_income_signal)
    offset_mask = pos_mask & (~income_mask)

    income = float(included_amounts.loc[income_mask].sum())
    gross_expenses = float((-included_amounts.loc[neg_mask]).sum())
    expense_offsets = float(included_amounts.loc[offset_mask].sum())

    net_expenses = float(gross_expenses - expense_offsets)
    net_cash = float(income - net_expenses)

    conf_high, conf_med, conf_low = _income_confidence_counts(
        income_mask=income_mask,
        category_signal=category_income_signal,
        keyword_signal=keyword_income_signal,
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




