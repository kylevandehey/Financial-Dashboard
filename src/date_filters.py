from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Optional, Tuple

import pandas as pd

PresetRange = Tuple[date, date]


_PRESET_ALIASES = {
    "last_week_to_date": "last_week_to_date",
    "last_week": "last_week_to_date",
    "last_week_wtd": "last_week_to_date",
    "mtd": "mtd",
    "month_to_date": "mtd",
    "ytd": "ytd",
    "year_to_date": "ytd",
    "q1": "q1",
    "q2": "q2",
    "q3": "q3",
    "q4": "q4",
    "full_year": "full_year",
}


def compute_date_range(
    preset: str = "ytd",
    *,
    year: Optional[int | str] = None,
    custom_start: Optional[date] = None,
    custom_end: Optional[date] = None,
    today: Optional[date] = None,
) -> PresetRange:
    """
    Compute a date range for the requested preset, honoring optional year context or
    custom overrides.

    The precedence is:
        1) Custom range (custom_start and custom_end provided)
        2) Preset + year context

    Args:
        preset: The preset key (e.g., "ytd", "mtd", "q1", "full_year", "last_week_to_date").
        year: A specific calendar year to constrain the range. Use None or "ALL" to ignore.
        custom_start: Optional custom start date override.
        custom_end: Optional custom end date override.
        today: Optional anchor date for deterministic testing. Defaults to date.today().

    Returns:
        Tuple of (start_date, end_date).

    Raises:
        ValueError: When the preset is unknown or when the custom range is invalid.
    """
    if (custom_start is not None) or (custom_end is not None):
        return _validate_custom_range(custom_start, custom_end)

    normalized_preset = _normalize_preset(preset)
    normalized_year = _normalize_year(year)
    anchor_day = today or date.today()

    if normalized_preset == "last_week_to_date":
        return _compute_last_week_to_date(anchor_day)
    if normalized_preset == "mtd":
        return _compute_month_to_date(anchor_day, normalized_year)
    if normalized_preset == "ytd":
        return _compute_year_to_date(anchor_day, normalized_year)
    if normalized_preset in {"q1", "q2", "q3", "q4"}:
        return _compute_quarter(anchor_day, normalized_year, normalized_preset)
    if normalized_preset == "full_year":
        target_year = _determine_target_year(anchor_day, normalized_year)
        return date(target_year, 1, 1), date(target_year, 12, 31)

    raise ValueError(f"Unsupported preset '{preset}'.")


def filter_dataframe_by_date(
    df: pd.DataFrame, date_range: Iterable[date], date_column: str = "Date"
) -> pd.DataFrame:
    """
    Return a filtered copy of the DataFrame constrained to the provided date range.

    Args:
        df: Normalized transactions DataFrame.
        date_range: Iterable with exactly (start_date, end_date).
        date_column: The column containing datelike values.

    Raises:
        ValueError: If the date column is missing or the date_range is invalid.
    """
    try:
        start_date, end_date = date_range
    except Exception as exc:
        raise ValueError("date_range must be an iterable with (start_date, end_date).") from exc

    if date_column not in df.columns:
        raise ValueError(f"DataFrame is missing required date column '{date_column}'.")

    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")

    date_series = pd.to_datetime(df[date_column], errors="coerce")
    mask = (date_series >= pd.Timestamp(start_date)) & (date_series <= pd.Timestamp(end_date))
    return df.loc[mask].copy()


def _normalize_preset(preset: str) -> str:
    key = preset.lower().strip().replace(" ", "_")
    if key not in _PRESET_ALIASES:
        raise ValueError(f"Unknown preset '{preset}'. Supported presets: {sorted(_PRESET_ALIASES)}")
    return _PRESET_ALIASES[key]


def _normalize_year(year: Optional[int | str]) -> Optional[int]:
    if year is None:
        return None
    if isinstance(year, str) and year.lower() == "all":
        return None
    try:
        return int(year)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Year must be an integer or 'ALL', received: {year}") from exc


def _determine_target_year(anchor_day: date, year: Optional[int]) -> int:
    return year or anchor_day.year


def _compute_last_week_to_date(anchor_day: date) -> PresetRange:
    start_of_previous_week = anchor_day - timedelta(days=anchor_day.weekday() + 7)
    end_of_previous_week = start_of_previous_week + timedelta(days=anchor_day.weekday())
    return start_of_previous_week, end_of_previous_week


def _compute_month_to_date(anchor_day: date, year: Optional[int]) -> PresetRange:
    target_year = _determine_target_year(anchor_day, year)
    start_of_month = date(target_year, anchor_day.month, 1)
    end_of_month = _end_of_month(target_year, anchor_day.month)
    if year is None or target_year == anchor_day.year:
        return start_of_month, min(anchor_day, end_of_month)
    return start_of_month, end_of_month


def _compute_year_to_date(anchor_day: date, year: Optional[int]) -> PresetRange:
    target_year = _determine_target_year(anchor_day, year)
    start_of_year = date(target_year, 1, 1)
    end_of_year = date(target_year, 12, 31)
    if year is None or target_year == anchor_day.year:
        return start_of_year, min(anchor_day, end_of_year)
    return start_of_year, end_of_year


def _compute_quarter(anchor_day: date, year: Optional[int], preset: str) -> PresetRange:
    target_year = _determine_target_year(anchor_day, year)
    quarter_number = int(preset[-1])
    start_month = 3 * (quarter_number - 1) + 1
    end_month = start_month + 2

    start_date = date(target_year, start_month, 1)
    end_date = _end_of_month(target_year, end_month)

    if (year is None or target_year == anchor_day.year) and _is_current_quarter(anchor_day, quarter_number):
        return start_date, min(anchor_day, end_date)
    return start_date, end_date


def _end_of_month(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    next_month = date(year, month + 1, 1)
    return next_month - timedelta(days=1)


def _is_current_quarter(anchor_day: date, quarter: int) -> bool:
    return ((anchor_day.month - 1) // 3) + 1 == quarter


def _validate_custom_range(custom_start: Optional[date], custom_end: Optional[date]) -> PresetRange:
    if custom_start is None or custom_end is None:
        raise ValueError("Both custom_start and custom_end must be provided for a custom range.")
    if custom_start > custom_end:
        raise ValueError("custom_start must be on or before custom_end.")
    return custom_start, custom_end
