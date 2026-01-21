# ui/control_panel.py

from __future__ import annotations
import streamlit as st
import pandas as pd
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class ControlState:
    start_date: date | None
    end_date: date | None
    selected_preset: str


def _available_years(df: pd.DataFrame) -> list[int]:
    if df.empty or "date" not in df.columns:
        return []
    years = (
        pd.to_datetime(df["date"], errors="coerce")
        .dt.year.dropna()
        .astype(int)
        .unique()
        .tolist()
    )
    return sorted(years)


def render_control_panel(transactions: pd.DataFrame) -> ControlState:
    st.sidebar.markdown("## 📅 Date Range Presets")

    today = date.today()

    years = _available_years(transactions)
    year_options = [str(y) for y in years]

    preset_options = [
        "Last 7 Days",
        "Last 30 Days",
        "Last 90 Days",
        "Last 180 Days",
        "Last Full Year",
        *year_options,
        "ALL YEARS",
        "Custom Range",
    ]

    preset = st.sidebar.selectbox(
        "Date Range Presets",
        preset_options,
        index=preset_options.index("ALL YEARS") if "ALL YEARS" in preset_options else 0,
    )

    start_date = None
    end_date = None

    if preset == "Last 7 Days":
        start_date = today - timedelta(days=7)
        end_date = today
    elif preset == "Last 30 Days":
        start_date = today - timedelta(days=30)
        end_date = today
    elif preset == "Last 90 Days":
        start_date = today - timedelta(days=90)
        end_date = today
    elif preset == "Last 180 Days":
        start_date = today - timedelta(days=180)
        end_date = today
    elif preset == "Last Full Year":
        start_date = date(today.year - 1, 1, 1)
        end_date = date(today.year - 1, 12, 31)
    elif preset.isdigit():
        year = int(preset)
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
    elif preset == "Custom Range":
        start_date, end_date = st.sidebar.date_input(
            "Custom Date Range",
            value=(today - timedelta(days=30), today),
        )
    elif preset == "ALL YEARS":
        start_date = None
        end_date = None

    return ControlState(
        start_date=start_date,
        end_date=end_date,
        selected_preset=preset,
    )
