from __future__ import annotations

import json
import os

import requests

from .config import Config


class Notifier:
    """Notifier for sending email analysis to Google Chat."""

    def __init__(self) -> None:
        """Initialize the notifier with Google Chat webhook URL."""
        self.webhook_url = str(Config.GOOGLE_CHAT_WEBHOOK)

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

        message_parts = [
            f"📬 Riepilogo Email Urgenti ({len(notifications)} messaggi)\n"
        ]

        for i, notif in enumerate(notifications, 1):
            thread_id = notif["thread_id"]
            subject = notif["subject"]
            from_addr = notif["from"]
            to_addr = notif["to"]
            urgency = notif["urgency"]
            classification = notif["classification"]
            analysis = notif["analysis"]
            needs_reply = notif["needs_reply"]
            draft_body = notif["draft_body"]

            # Format urgency as stars
            urgency_stars = self._format_urgency_stars(urgency)

            # Create Gmail link
            gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"

            # Format message without bold for category
            message_parts.append(f"\n{i}. {subject}")
            message_parts.append(f"   Da: {from_addr}")
            message_parts.append(f"   A: {to_addr}")
            message_parts.append(f"   {urgency_stars} | {classification}")
            message_parts.append(f"   {analysis}")
            message_parts.append(f"   🔗 <{gmail_link}|Apri in Gmail>")

            # Only add draft if addressed to Stefano (not stefano@chino.io)
            if needs_reply and draft_body:
                # Check if email is addressed to "Stefano" (not an email address)
                # to_lower = to_addr.lower()
                # if "stefano@chino.io" not in to_lower and "stefano" in to_lower:
                message_parts.append(f"   📝 Bozza: {draft_body[:200]}...")

        message = "\n".join(message_parts)

        try:
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
            message = (
                "📋 *Report Messaggi Processati*\n\n"
                "Nessun messaggio processato da segnalare."
            )
            try:
                response = requests.post(self.webhook_url, json={"text": message})
                response.raise_for_status()
                return True
            except Exception as e:
                print(f"❌ Errore invio report: {e}")
                return False

        try:
            with open(Config.PROCESSED_LOG_FILE, "r") as f:
                log_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print("❌ Errore lettura file log")
            return False

        if not log_data:
            message = (
                "📋 *Report Messaggi Processati*\n\n"
                "Nessun messaggio processato da segnalare."
            )
        else:
            message_parts = [
                "📋 *Report Messaggi Processati (Urgenza ≤ 2)*\n",
                f"Totale messaggi: {len(log_data)}\n",
            ]

            for i, entry in enumerate(log_data, 1):
                timestamp = entry.get("timestamp", "N/A")
                subject = entry.get("subject", "N/A")
                from_addr = entry.get("from", "N/A")
                to_addr = entry.get("to", "N/A")
                classification = entry.get("classification", "N/A")
                urgency = entry.get("urgency", 0)
                analysis = entry.get("analysis", "N/A")
                thread_id = entry.get("thread_id", "")

                # Format urgency as stars
                urgency_stars = self._format_urgency_stars(urgency)

                # Create Gmail link
                gmail_link = ""
                if thread_id:
                    gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"

                message_parts.append(f"\n{i}. *{subject}*")
                message_parts.append(f"   • Da: {from_addr}")
                message_parts.append(f"   • A: {to_addr}")
                message_parts.append(
                    f"   • Categoria: {classification} | Urgenza: {urgency_stars}"
                )
                message_parts.append(f"   • Analisi: {analysis}")
                message_parts.append(f"   • Data: {timestamp[:16]}")
                if gmail_link:
                    message_parts.append(f"   • 🔗 <{gmail_link}|Apri in Gmail>")

            message = "\n".join(message_parts)

        try:
            response = requests.post(self.webhook_url, json={"text": message})
            response.raise_for_status()
            print(f"✅ Report inviato ({len(log_data)} messaggi)")
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
