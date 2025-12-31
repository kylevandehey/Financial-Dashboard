"""
CSV ingestion and normalization for Monarch Money transaction exports.

This module converts Monarch CSVs into a canonical DataFrame schema with
derived date metadata that downstream tabs (ALL, year breakouts) rely on.

Streamlit-specific handling should remain outside this module; callers
should pass the uploaded file object directly.
"""

from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime
from typing import Iterable, Mapping, MutableMapping, Sequence

import pandas as pd

# Canonical column names expected downstream
CANONICAL_COLUMNS: Sequence[str] = (
    "date",
    "amount",
    "merchant",
    "category",
    "account",
    "notes",
    "is_income",
    "is_expense",
    "year",
    "month",
    "year_month",
    "quarter",
    "is_ytd",
)

# Common Monarch column variants mapped to canonical names
VARIANT_COLUMN_MAP: Mapping[str, str] = {
    "date": "date",
    "transaction_date": "date",
    "transactiondate": "date",
    "posted_date": "date",
    "amount": "amount",
    "transaction_amount": "amount",
    "merchant": "merchant",
    "payee": "merchant",
    "category": "category",
    "category_name": "category",
    "account": "account",
    "account_name": "account",
    "notes": "notes",
    "memo": "notes",
    "description": "notes",
}

ACCOUNT_VARIANT_MAP: Mapping[str, str] = {
    "account": "account",
    "account_name": "account",
    "name": "account",
    "type": "type",
    "account_type": "type",
    "category": "type",
    "subtype": "subtype",
    "group": "subtype",
    "class": "subtype",
    "balance": "balance",
    "current_balance": "balance",
    "available_balance": "balance",
    "institution": "institution",
    "provider": "institution",
}


def _normalize_column_name(column: str) -> str:
    """Normalize a raw column header for matching."""
    return column.strip().lower().replace(" ", "_")


def _build_column_mapping(raw_columns: Iterable[str]) -> MutableMapping[str, str]:
    """Map raw CSV columns to canonical names, raising on missing required fields."""
    mapping: MutableMapping[str, str] = {}
    normalized_columns = {_normalize_column_name(col): col for col in raw_columns}

    required_targets = {"date", "amount", "merchant", "category", "account"}
    for normalized, original in normalized_columns.items():
        if normalized in VARIANT_COLUMN_MAP:
            canonical = VARIANT_COLUMN_MAP[normalized]
            if canonical not in mapping:
                mapping[canonical] = original

    missing = [col for col in required_targets if col not in mapping]
    if missing:
        readable_missing = ", ".join(sorted(missing))
        raise ValueError(
            "Missing required columns in uploaded file. "
            f"Add the following fields to your Monarch export: {readable_missing}."
        )

    # Notes are optional; add if available
    if "notes" not in mapping:
        for candidate in ("notes", "memo", "description"):
            if candidate in normalized_columns:
                mapping["notes"] = normalized_columns[candidate]
                break

    return mapping


def _parse_amount(raw_amount: str) -> float:
    """Coerce a raw amount string into a float, surfacing readable errors."""
    if pd.isna(raw_amount):
        raise ValueError("Amount column contains empty values. Please fill or remove blanks.")

    value = str(raw_amount).strip()
    if value == "":
        raise ValueError("Amount column contains empty strings. Please fill or remove blanks.")

    # Handle parentheses accounting format
    is_negative = value.startswith("(") and value.endswith(")")
    sanitized = value.replace("(", "").replace(")", "")
    sanitized = (
        sanitized.replace("$", "").replace(",", "").replace(" ", "").replace("\u00a0", "")
    )

    try:
        parsed = float(sanitized)
    except ValueError as exc:  # pragma: no cover - precise message surfaced via ValueError
        raise ValueError(
            f"Unable to parse amount value '{raw_amount}'. "
            "Ensure amounts are numeric and remove currency symbols."
        ) from exc

    return -parsed if is_negative else parsed


def _parse_dates(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.isna().any():
        invalid_rows = parsed[parsed.isna()]
        sample_indices = invalid_rows.index.tolist()[:3]
        raise ValueError(
            "Date parsing failed for one or more rows. "
            f"Review the date format in rows: {sample_indices}."
        )
    return parsed.dt.tz_localize(None)


def normalize_transactions(csv_file, *, today: date_cls | None = None) -> pd.DataFrame:
    """
    Normalize a Monarch Transactions CSV into the canonical schema with derived metadata.

    Parameters
    ----------
    csv_file: File-like object or path
        The uploaded CSV file object from Streamlit or a filesystem path.
    today: datetime.date, optional
        Reference date for YTD calculations (defaults to current date).

    Returns
    -------
    pandas.DataFrame
        DataFrame containing canonical columns and derived date fields.
    """
    today = today or datetime.now().date()
    df = pd.read_csv(csv_file, encoding="utf-8", dtype=str)

    column_mapping = _build_column_mapping(df.columns)
    df = df.rename(columns={original: canonical for canonical, original in column_mapping.items()})

    # Ensure notes column exists
    if "notes" not in df.columns:
        df["notes"] = ""

    df["date"] = _parse_dates(df["date"])
    df["amount"] = df["amount"].apply(_parse_amount).astype(float)
    df["merchant"] = df["merchant"].fillna("").astype(str).str.strip()
    df["category"] = df["category"].fillna("").astype(str).str.strip()
    df["account"] = df["account"].fillna("").astype(str).str.strip()
    df["notes"] = df["notes"].fillna("").astype(str).str.strip()

    df["is_income"] = df["amount"] > 0
    df["is_expense"] = df["amount"] < 0

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    df["quarter"] = "Q" + ((df["date"].dt.month.sub(1).floordiv(3).add(1)).astype(str))

    start_of_year = datetime(today.year, 1, 1).date()
    df["is_ytd"] = (df["date"].dt.date >= start_of_year) & (df["date"].dt.date <= today)

    ordered_columns = [col for col in CANONICAL_COLUMNS if col in df.columns]
    return df[ordered_columns]


def _build_account_mapping(raw_columns: Iterable[str]) -> MutableMapping[str, str]:
    mapping: MutableMapping[str, str] = {}
    normalized_columns = {_normalize_column_name(col): col for col in raw_columns}

    required_targets = {"type", "balance"}

    for normalized, original in normalized_columns.items():
        if normalized in ACCOUNT_VARIANT_MAP:
            canonical = ACCOUNT_VARIANT_MAP[normalized]
            if canonical not in mapping:
                mapping[canonical] = original

    missing = [col for col in required_targets if col not in mapping]
    if missing:
        raise ValueError(
            "Accounts CSV is missing required fields. "
            f"Add the following columns: {', '.join(sorted(missing))}."
        )

    if "account" not in mapping:
        mapping["account"] = next(iter(normalized_columns.values()))

    return mapping


def normalize_accounts(csv_file) -> pd.DataFrame:
    """
    Normalize an Accounts CSV into a consistent schema with signed balances.

    Returns columns:
        account, type, subtype, balance, signed_balance, is_asset, is_liability, institution
    """
    df = pd.read_csv(csv_file, encoding="utf-8", dtype=str)
    mapping = _build_account_mapping(df.columns)
    df = df.rename(columns={original: canonical for canonical, original in mapping.items()})

    df["account"] = df["account"].astype(str).str.strip()
    df["type"] = df["type"].astype(str).str.strip().str.lower()
    if "subtype" not in df.columns:
        df["subtype"] = ""
    if "institution" not in df.columns:
        df["institution"] = ""
    df["subtype"] = df["subtype"].astype(str).str.strip().str.lower()
    df["institution"] = df["institution"].astype(str).str.strip()
    df["balance"] = df["balance"].apply(_parse_amount).astype(float)

    df["is_asset"] = df["type"].str.contains("asset", na=False)
    df["is_liability"] = df["type"].str.contains("liability|debt|loan|credit", na=False)

    # If neither flag matches, assume asset to avoid hiding money
    df.loc[~(df["is_asset"] | df["is_liability"]), "is_asset"] = True
    df["signed_balance"] = df["balance"]
    df.loc[df["is_liability"], "signed_balance"] = -df.loc[df["is_liability"], "balance"].abs()
    return df[["account", "type", "subtype", "balance", "signed_balance", "is_asset", "is_liability", "institution"]]
