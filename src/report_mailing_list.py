from __future__ import annotations

import json
import os

import requests
from jinja2 import Environment, FileSystemLoader

from .config import Config
from .gmail_client import GmailClient


def send_mailing_list_report() -> bool:
    """Send report of mailing list messages to Google Chat and Email.

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

    # Load and render template
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("mailing_list_report.jinja")

    message = template.render(log_data=log_data)

    try:
        webhook_url = str(Config.GOOGLE_CHAT_WEBHOOK)
        response = requests.post(webhook_url, json={"text": message})
        response.raise_for_status()
        print(f"✅ Report mailing list inviato ({len(log_data)} messaggi)")
        
        # Send Email Report
        try:
            gmail = GmailClient()
            subject = "[Janus] Report Mailing List Archiviate"
            gmail.send_email(Config.USER_EMAIL, subject, message)
        except Exception as email_err:
            print(f"❌ Errore invio email report: {email_err}")

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
