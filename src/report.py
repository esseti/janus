#!/usr/bin/env python3
"""Command to send report of processed but not notified messages."""

from __future__ import annotations

import sys

from .config import Config
from .notifier import Notifier


def send_report(clear: bool = False) -> None:
    """Send report of processed messages to Google Chat.

    Args:
        clear: If True, clear the log file after sending report.
    """
    print("📋 Invio report messaggi processati...")

    try:
        Config.validate()
    except Exception as e:
        print(f"❌ Errore configurazione: {e}")
        sys.exit(1)

    notifier = Notifier()

    # Send report
    if notifier.send_processed_log_report():
        print("✅ Report inviato con successo")

        # Clear log if requested
        if clear:
            print("🗑️  Svuotamento file log...")
            notifier.clear_processed_log()
    else:
        print("❌ Errore invio report")
        sys.exit(1)


def main() -> None:
    """Main entry point for report command."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Invia report messaggi processati a Google Chat"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Svuota il file log dopo l'invio del report",
    )

    args = parser.parse_args()
    send_report(clear=args.clear)


if __name__ == "__main__":
    main()
