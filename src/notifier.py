from __future__ import annotations

import json
import os

import requests
from jinja2 import Environment, FileSystemLoader

from .config import Config


class Notifier:
    """Notifier for sending email analysis to Google Chat."""

    def __init__(self) -> None:
        """Initialize the notifier with Google Chat webhook URL and templates."""
        self.webhook_url = str(Config.GOOGLE_CHAT_WEBHOOK)
        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.env.globals["format_stars"] = self._format_urgency_stars

    def _format_urgency_stars(self, urgency: int) -> str:
        """Format urgency level as filled and empty stars.

        Args:
            urgency: Urgency level from 1 to 5.

        Returns:
            String with filled (★) and empty (☆) stars.
        """
        urgency = max(1, min(5, urgency))  # Clamp between 1 and 5
        filled = "★" * urgency
        empty = "☆" * (5 - urgency)
        return filled + empty

    def send_consolidated_report(self, notifications: list[dict]) -> bool:
        """Send consolidated report of all urgent emails.

        Args:
            notifications: List of notification dicts with email details.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not notifications:
            return True

        try:
            template = self.env.get_template("urgent_report.jinja")
            message = template.render(notifications=notifications)

            response = requests.post(self.webhook_url, json={"text": message})
            response.raise_for_status()
            print(f"✅ Report consolidato inviato ({len(notifications)} email)")
            return True
        except Exception as e:
            print(f"❌ Errore invio report: {e}")
            return False

    def send_processed_log_report(self) -> bool:
        """Send report of processed but not notified messages to Google Chat.

        Returns:
            True if report sent successfully, False otherwise.
        """
        if not os.path.exists(Config.PROCESSED_LOG_FILE):
            return True

        try:
            with open(Config.PROCESSED_LOG_FILE, "r") as f:
                log_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print("❌ Errore lettura file log")
            return False

        if not log_data:
            return True

        try:
            template = self.env.get_template("processed_report.jinja")
            message = template.render(log_data=log_data)

            response = requests.post(self.webhook_url, json={"text": message})
            response.raise_for_status()
            print(f"✅ Report inviato ({len(log_data)} messaggi)")

            # Clear the log file after successful send
            with open(Config.PROCESSED_LOG_FILE, "w") as f:
                json.dump([], f)
            print(f"✅ File log svuotato")

            return True
        except Exception as e:
            print(f"❌ Errore invio report: {e}")
            return False

    def clear_processed_log(self) -> bool:
        """Clear the processed log file.

        Returns:
            True if cleared successfully, False otherwise.
        """
        try:
            if os.path.exists(Config.PROCESSED_LOG_FILE):
                os.remove(Config.PROCESSED_LOG_FILE)
                print("✅ File log svuotato")
            return True
        except Exception as e:
            print(f"❌ Errore svuotamento log: {e}")
            return False
