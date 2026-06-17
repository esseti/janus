"""Out-of-office state management.

Stores the out-of-office period in a small JSON file in the data dir so it can be
toggled via CLI without restarting the process or editing .env. While an OOO period
is active, Janus holds notifications instead of sending them to chat, and a single
email recap is sent automatically on return.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime

import zoneinfo

from .config import Config


def _today(now: datetime | None = None) -> date:
    """Return today's date in the configured timezone."""
    tz = zoneinfo.ZoneInfo(Config.TIMEZONE)
    return (now or datetime.now(tz)).astimezone(tz).date()


def load_ooo() -> dict | None:
    """Load the out-of-office state, or None if not configured.

    Returns:
        The state dict (active, start, end, recap_sent) or None.
    """
    if not os.path.exists(Config.OOO_FILE):
        return None
    try:
        with open(Config.OOO_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None
    return data or None


def save_ooo(state: dict) -> None:
    """Persist the out-of-office state to disk."""
    with open(Config.OOO_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def set_ooo(start: str, end: str) -> dict:
    """Create/overwrite the out-of-office period.

    Args:
        start: Start date, ISO format YYYY-MM-DD (inclusive).
        end: End date, ISO format YYYY-MM-DD (inclusive).

    Returns:
        The saved state dict.

    Raises:
        ValueError: If dates are malformed or start > end.
    """
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    if start_d > end_d:
        raise ValueError("start deve essere <= end")
    state = {
        "active": True,
        "start": start_d.isoformat(),
        "end": end_d.isoformat(),
        "recap_sent": False,
    }
    save_ooo(state)
    return state


def clear_ooo() -> None:
    """Disable the out-of-office period without sending a recap."""
    state = load_ooo()
    if state is None:
        return
    state["active"] = False
    save_ooo(state)


def is_ooo_active(now: datetime | None = None) -> bool:
    """Whether an out-of-office period is currently active.

    Active means the state flag is set and today is within [start, end] inclusive.
    """
    state = load_ooo()
    if not state or not state.get("active"):
        return False
    try:
        start_d = date.fromisoformat(state["start"])
        end_d = date.fromisoformat(state["end"])
    except (KeyError, ValueError):
        return False
    return start_d <= _today(now) <= end_d


def is_ooo_finished(now: datetime | None = None) -> bool:
    """Whether an active OOO period has ended (today is past end date)."""
    state = load_ooo()
    if not state or not state.get("active"):
        return False
    try:
        end_d = date.fromisoformat(state["end"])
    except (KeyError, ValueError):
        return False
    return _today(now) > end_d


def append_held(notifications: list[dict]) -> None:
    """Append urgent notifications held during the OOO period.

    Args:
        notifications: Notification dicts (same shape built in main.run_janus).
    """
    if not notifications:
        return
    held = load_held()
    held.extend(notifications)
    with open(Config.OOO_HELD_FILE, "w") as f:
        json.dump(held, f, indent=2, ensure_ascii=False)


def load_held() -> list[dict]:
    """Load notifications held during the OOO period."""
    if not os.path.exists(Config.OOO_HELD_FILE):
        return []
    try:
        with open(Config.OOO_HELD_FILE, "r") as f:
            return json.load(f) or []
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def clear_held() -> None:
    """Empty the held-notifications file."""
    with open(Config.OOO_HELD_FILE, "w") as f:
        json.dump([], f)
