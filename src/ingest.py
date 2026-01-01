"""
CSV ingestion and normalization for Monarch Money transaction exports.

This module converts Monarch CSVs into a canonical DataFrame schema with
derived date metadata that downstream tabs (ALL, year breakouts) rely on.

Streamlit-specific handling should remain outside this module; callers
should pass the uploaded file object directly.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
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
    "transaction_type",
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
    "account_id": "account",
    "notes": "notes",
    "memo": "notes",
    "description": "notes",
    "transaction_type": "transaction_type",
    "type": "transaction_type",
}

ACCOUNT_VARIANT_MAP: Mapping[str, str] = {
    "date": "date",
    "as_of_date": "date",
    "as_of": "date",
    "account": "account",
    "account_name": "account",
    "name": "account",
    "type": "type",
    "account_type": "account_type",
    "category": "category",
    "subtype": "subtype",
    "group": "account_group",
    "account_group": "account_group",
    "class": "account_group",
    "balance": "balance",
    "current_balance": "balance",
    "available_balance": "balance",
    "institution": "institution",
    "provider": "institution",
}


@dataclass
class CSVDetection:
    name: str
    transactions_match: bool
    balances_match: bool
    transactions_missing: list[str]
    balances_missing: list[str]


def _normalize_column_name(column: str) -> str:
    """Normalize a raw column header for matching."""
    return column.strip().lower().replace(" ", "_")


def _canonicalized_columns(raw_columns: Iterable[str], variant_map: Mapping[str, str]) -> set[str]:
    """Map raw column names to canonical identifiers based on a variant map."""
    canonical = set()
    for raw in raw_columns:
        normalized = _normalize_column_name(raw)
        if normalized in variant_map:
            canonical.add(variant_map[normalized])
    return canonical


def _readable_list(values: Iterable[str]) -> str:
    sorted_values = sorted(set(values))
    return ", ".join(sorted_values)


def _clone_to_buffer(upload) -> io.BytesIO:
    """Create a reusable BytesIO buffer from an uploaded file-like object."""
    if hasattr(upload, "getvalue"):
        data = upload.getvalue()
    else:
        current_pos = upload.tell() if hasattr(upload, "tell") else None
        data = upload.read()
        if current_pos is not None and hasattr(upload, "seek"):
            upload.seek(current_pos)
    if isinstance(data, str):
        data = data.encode("utf-8")
    buffer = io.BytesIO(data)
    buffer.seek(0)
    return buffer


def _peek_columns(buffer: io.BytesIO) -> Iterable[str]:
    """Read CSV columns without consuming the buffer."""
    buffer.seek(0)
    preview = pd.read_csv(buffer, nrows=0)
    buffer.seek(0)
    return preview.columns


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
    if "transaction_type" not in df.columns:
        df["transaction_type"] = ""
    else:
        df["transaction_type"] = df["transaction_type"].fillna("").astype(str).str.strip()

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


def _detect_transactions_columns(canonical_columns: set[str]) -> tuple[bool, list[str]]:
    missing = [col for col in ("date", "amount") if col not in canonical_columns]
    has_identifier = any(col in canonical_columns for col in ("merchant", "category", "account"))
    if not has_identifier:
        missing.append("merchant/category/account")
    return len(missing) == 0, missing


def _detect_balance_columns(canonical_columns: set[str]) -> tuple[bool, list[str]]:
    missing = [col for col in ("date", "balance", "account") if col not in canonical_columns]
    return len(missing) == 0, missing


def identify_csv_roles(uploaded_files):
    """
    Identify which uploaded CSV corresponds to Transactions vs Balances.

    Returns
    -------
    transactions_file: io.BytesIO | None
        Buffer for the detected Transactions CSV.
    balances_file: io.BytesIO | None
        Buffer for the detected Accounts/Balances CSV.
    diagnostics: list[CSVDetection]
        Per-file diagnostics indicating which required columns were missing.
    error_message: str | None
        Actionable error description when either CSV cannot be identified.
    """
    detections: list[CSVDetection] = []
    transactions_file: io.BytesIO | None = None
    balances_file: io.BytesIO | None = None

    for upload in uploaded_files:
        buffer = _clone_to_buffer(upload)
        columns = _peek_columns(buffer)
        canonical_tx = _canonicalized_columns(columns, VARIANT_COLUMN_MAP)
        canonical_balances = _canonicalized_columns(columns, ACCOUNT_VARIANT_MAP)

        tx_match, tx_missing = _detect_transactions_columns(canonical_tx)
        balance_match, balance_missing = _detect_balance_columns(canonical_balances)

        detections.append(
            CSVDetection(
                name=getattr(upload, "name", "Uploaded CSV"),
                transactions_match=tx_match,
                balances_match=balance_match,
                transactions_missing=tx_missing,
                balances_missing=balance_missing,
            )
        )

        if tx_match and not balance_match and transactions_file is None:
            transactions_file = buffer
        elif balance_match and not tx_match and balances_file is None:
            balances_file = buffer

    error_message = None
    if not transactions_file or not balances_file:
        error_message = _build_identification_error(
            detections,
            missing_transactions=transactions_file is None,
            missing_balances=balances_file is None,
        )

    return transactions_file, balances_file, detections, error_message


def _build_identification_error(
    detections: list[CSVDetection], *, missing_transactions: bool, missing_balances: bool
) -> str | None:
    if not detections:
        return None

    lines = [
        "Could not identify both required CSVs.",
        "Expected:",
        "- Transactions CSV with Date, Amount, and at least one of Merchant/Category/Account.",
        "- Balances CSV with Date, Balance, and Account.",
        "Detected:",
    ]

    for detection in detections:
        status_parts = []
        if detection.transactions_match and detection.balances_match:
            status_parts.append("matches both schemas (ambiguous)")
        elif detection.transactions_match:
            status_parts.append("detected as Transactions CSV")
        elif detection.balances_match:
            status_parts.append("detected as Balances CSV")
        else:
            missing_tx = _readable_list(detection.transactions_missing) or "none"
            missing_bal = _readable_list(detection.balances_missing) or "none"
            status_parts.append(f"missing for Transactions: {missing_tx}; missing for Balances: {missing_bal}")

        lines.append(f"- {detection.name}: " + "; ".join(status_parts))

    missing_parts = []
    if missing_transactions:
        missing_parts.append("Transactions CSV")
    if missing_balances:
        missing_parts.append("Balances CSV")
    if missing_parts:
        lines.append(f"Upload missing: {', '.join(missing_parts)}.")

    return "\n".join(lines)


def _build_account_mapping(raw_columns: Iterable[str]) -> MutableMapping[str, str]:
    mapping: MutableMapping[str, str] = {}
    normalized_columns = {_normalize_column_name(col): col for col in raw_columns}

    required_targets = {"balance", "date", "account"}

    for normalized, original in normalized_columns.items():
        if normalized in ACCOUNT_VARIANT_MAP:
            canonical = ACCOUNT_VARIANT_MAP[normalized]
            if canonical not in mapping:
                mapping[canonical] = original

    missing = [col for col in required_targets if col not in mapping]
    if missing:
        raise ValueError(
            "Accounts CSV could not be processed. "
            "Include Date, Account, and Balance columns to infer assets and liabilities correctly."
        )

    return mapping


def normalize_accounts(csv_file) -> pd.DataFrame:
    """
    Normalize an Accounts CSV into a consistent schema with signed balances.

    Returns columns:
        date, account, type, subtype, balance, signed_balance, is_asset, is_liability, institution
    """
    classification_priority = ("type", "account_type", "subtype", "category", "account_group")

    def _normalize_account_type_value(raw_value: str) -> str:
        text = str(raw_value or "").strip().lower()
        if not text:
            return "Other"

        if any(keyword in text for keyword in ("credit card", "credit", "card")):
            return "Credit"
        if any(keyword in text for keyword in ("loan", "mortgage", "liability", "debt", "payable")):
            return "Liability"
        if any(
            keyword in text
            for keyword in (
                "asset",
                "cash",
                "checking",
                "saving",
                "savings",
                "brokerage",
                "invest",
                "retire",
                "401",
                "ira",
                "roth",
                "property",
                "home",
            )
        ):
            return "Asset"
        if "debit" in text:
            return "Asset"
        return "Other"

    def _infer_account_type(row: pd.Series, available_columns: Iterable[str]) -> str | None:
        for column in available_columns:
            raw_value = str(row.get(column, "")).strip()
            if raw_value:
                normalized = _normalize_account_type_value(raw_value).title()
                if normalized != "Other":
                    return normalized
        return None

    def _infer_from_balance(balance_value: float) -> str:
        if balance_value > 0:
            return "Asset"
        if balance_value < 0:
            return "Liability"
        return "Asset"

    df = pd.read_csv(csv_file, encoding="utf-8", dtype=str)
    mapping = _build_account_mapping(df.columns)
    df = df.rename(columns={original: canonical for canonical, original in mapping.items()})

    classification_columns = [col for col in classification_priority if col in df.columns]

    for column in ("date", "account", *classification_columns):
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str).str.strip()
    if "subtype" not in df.columns:
        df["subtype"] = ""
    if "institution" not in df.columns:
        df["institution"] = ""
    df["institution"] = df["institution"].astype(str).str.strip()
    df["date"] = _parse_dates(df["date"])
    df["balance"] = df["balance"].apply(_parse_amount).astype(float)

    df["type"] = df.apply(
        lambda row: _infer_account_type(row, classification_columns)
        or _infer_from_balance(float(row["balance"])),
        axis=1,
    )
    df["type"] = df["type"].apply(_normalize_account_type_value).str.title()

    df["is_asset"] = df["type"] == "Asset"
    df["is_liability"] = df["type"].isin(["Liability", "Credit"])

    # If neither flag matches, assume asset to avoid hiding money
    df.loc[~(df["is_asset"] | df["is_liability"]), "is_asset"] = True
    df["signed_balance"] = df["balance"]
    df.loc[df["is_liability"], "signed_balance"] = -df.loc[df["is_liability"], "balance"].abs()
    ordered_columns = [
        "date",
        "account",
        "type",
        "subtype",
        "balance",
        "signed_balance",
        "is_asset",
        "is_liability",
        "institution",
    ]
    return df[ordered_columns]
