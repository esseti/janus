from __future__ import annotations

import json
import os

import requests

from .config import Config


def send_mailing_list_report() -> bool:
    """Send report of mailing list messages to Google Chat.

    Returns:
        True if report sent successfully, False otherwise.
    """
    if not os.path.exists(Config.MAILING_LIST_LOG_FILE):
        return True

    try:
        with open(Config.MAILING_LIST_LOG_FILE, "r") as f:
            log_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return True

    if not log_data:
        return True

    message_parts = [
        "📧 *Report Mailing List (Messaggi Archiviati)*\n",
    ]

    for entry in log_data:
        subject = entry.get("subject", "N/A")
        from_addr = entry.get("from", "N/A")
        thread_id = entry.get("thread_id", "")

        # Create Gmail link
        gmail_link = ""
        if thread_id:
            gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"

        # Compact format: MITTENTE | TITOLO | LINK
        link_text = f"<{gmail_link}|🔗>" if gmail_link else ""

        message_parts.append(f"{subject[:50]} | {from_addr[:40]}  | {link_text}")

    message = "\n - ".join(message_parts)

    try:
        webhook_url = str(Config.GOOGLE_CHAT_WEBHOOK)
        response = requests.post(webhook_url, json={"text": message})
        response.raise_for_status()
        print(f"✅ Report mailing list inviato ({len(log_data)} messaggi)")

        # Clear the log file after successful send
        with open(Config.MAILING_LIST_LOG_FILE, "w") as f:
            json.dump([], f)
        print(f"✅ File log mailing list svuotato")

        return True
    except Exception as e:
        print(f"❌ Errore invio report mailing list: {e}")
        return False


if __name__ == "__main__":
    send_mailing_list_report()
