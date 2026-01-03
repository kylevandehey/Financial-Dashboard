"""Lightweight debug helpers to improve traceability without polluting the UI.

Diagnostics are only recorded when the debug flag is enabled to avoid leaking
noisy output to end users. This module intentionally depends on Streamlit so
future tabs can opt into the same flag without reworking ingestion.
"""

from __future__ import annotations

from typing import Any, Mapping

import logging
import streamlit as st

DEBUG_FLAG_KEY = "dashboard_debug_enabled"
DEBUG_EVENTS_KEY = "dashboard_debug_events"

logger = logging.getLogger(__name__)


def debug_enabled() -> bool:
    """Return True when diagnostics should be captured."""
    secrets_flag = False
    try:
        secrets_flag = bool(getattr(st, "secrets", {}).get("debug_mode", False))  # type: ignore[arg-type]
    except Exception:
        secrets_flag = False
    return bool(st.session_state.get(DEBUG_FLAG_KEY, False) or secrets_flag)


def log_debug_event(event: str, details: Mapping[str, Any]) -> None:
    """Persist debug events in session state and emit to logger when enabled."""
    if not debug_enabled():
        return

    payload = {"event": event, "details": dict(details)}
    st.session_state.setdefault(DEBUG_EVENTS_KEY, []).append(payload)
    logger.debug("%s | %s", event, details)

