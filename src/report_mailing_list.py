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
        print("error")
        return True

    if not log_data:
        print("no data")
        return True

    # Load and render template
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("mailing_list_report.jinja")

    message = template.render(log_data=log_data)

    print("\n--- REPORT MAILING LIST ---")
    print(message)
    print("---------------------------\n")

    # Send Email Report
    email_sent = False
    chat_sent = False
    try:
        email_sent = True
        gmail = GmailClient()
        subject = "[Janus] Report Mailing List Archiviate"
        gmail.send_email(Config.USER_EMAIL, subject, message)
    except Exception as email_err:
        print(f"❌ Errore invio email report: {email_err}")

    try:
        chat_sent = True
        webhook_url = str(Config.GOOGLE_CHAT_WEBHOOK)
        response = requests.post(webhook_url, json={"text": message})
        response.raise_for_status()
        print(
            f"✅ Report mailing list inviato su Google Chat ({len(log_data)} messaggi)"
        )

    except Exception as e:
        print(f"❌ Errore invio report mailing list: {e}")
        return False

    if email_sent or chat_sent:
        # Clear the log file after successful send
        with open(Config.MAILING_LIST_LOG_FILE, "w") as f:
            json.dump([], f)
        print(f"✅ File log mailing list svuotato")

        return True
    else:
        return False


if __name__ == "__main__":
    send_mailing_list_report()
