#!/usr/bin/env python3
"""Send the out-of-office recap email on return.

Designed to run daily via cron: it is a no-op unless an active OOO period has
ended (or `force=True`). On send it summarizes the important emails held during
the absence (thematic LLM summary + per-email detail), emails the user, then
disables the OOO period so it does not fire again.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import zoneinfo
from jinja2 import Environment, FileSystemLoader

from .config import Config
from .gmail_client import GmailClient
from .llm_processor import LLMProcessor
from .ooo_state import clear_held, is_ooo_finished, load_held, load_ooo, save_ooo


def _non_urgent_count() -> int:
    """Count low-urgency messages processed during the absence."""
    if not os.path.exists(Config.PROCESSED_LOG_FILE):
        return 0
    try:
        with open(Config.PROCESSED_LOG_FILE, "r") as f:
            return len(json.load(f) or [])
    except (json.JSONDecodeError, FileNotFoundError):
        return 0


def maybe_send_recap(force: bool = False) -> bool:
    """Send the OOO recap email if the period has ended (or forced).

    Args:
        force: Send the recap now regardless of the end date.

    Returns:
        True if a recap was sent, False otherwise.
    """
    state = load_ooo()
    if not state or state.get("recap_sent"):
        return False
    if not force and not is_ooo_finished():
        return False

    try:
        Config.validate()
    except Exception as e:
        print(f"❌ Errore configurazione: {e}")
        sys.exit(1)

    important = load_held()
    non_urgent = _non_urgent_count()

    # Thematic summary of the important emails (single LLM call).
    thematic_summary = ""
    if important:
        thematic_summary = LLMProcessor().summarize_period(important)

    tz = zoneinfo.ZoneInfo(Config.TIMEZONE)
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("ooo_recap.jinja")
    body = template.render(
        generated_at=datetime.now(tz).strftime("%Y-%m-%d %H:%M"),
        timezone=Config.TIMEZONE,
        period_start=state.get("start", "?"),
        period_end=state.get("end", "?"),
        important=important,
        non_urgent_count=non_urgent,
        thematic_summary=thematic_summary,
    )

    subject = (
        f"🏖️ Recap out-of-office ({state.get('start', '?')} → "
        f"{state.get('end', '?')}) — {len(important)} importanti"
    )

    gmail = GmailClient()
    if not gmail.send_email(str(Config.USER_EMAIL), subject, body):
        print("❌ Invio recap fallito")
        return False

    # Mark sent, disable OOO, clear held notifications.
    state["recap_sent"] = True
    state["active"] = False
    save_ooo(state)
    clear_held()
    print(f"✅ Recap inviato a {Config.USER_EMAIL} ({len(important)} email importanti)")
    return True


def main() -> None:
    """Entry point for `python -m src.recap`."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Invia il recap out-of-office al rientro"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Invia il recap subito, anche se il periodo non è ancora terminato",
    )
    args = parser.parse_args()

    if not maybe_send_recap(force=args.force):
        print("ℹ️  Nessun recap da inviare")


if __name__ == "__main__":
    main()
