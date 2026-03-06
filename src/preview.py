#!/usr/bin/env python3
"""Script to preview Google Chat notification templates with dummy data."""

from __future__ import annotations

import argparse
import json
import os
import tempfile

from .config import Config
from .notifier import Notifier
from .report_mailing_list import send_mailing_list_report


def get_dummy_urgent_data():
    return [
        {
            "thread_id": "194208a8a8a8a8a8",
            "subject": "⚠️ Problema critico produzione Edwin",
            "from": "monitoring@chino.io",
            "to": "stefano@chino.io",
            "urgency": 5,
            "classification": "Urgent",
            "analysis": "È stato rilevato un errore critico nel sistema Edwin che richiede intervento immediato.",
            "needs_reply": True,
            "draft_body": "Ciao, ho ricevuto la segnalazione. Me ne occupo subito e vi aggiorno tra 15 minuti.",
        },
        {
            "thread_id": "194208b8b8b8b8b8",
            "subject": "Richiesta ferie: Mario Rossi",
            "from": "mario.rossi@chino.io",
            "to": "stefano@chino.io",
            "urgency": 3,
            "classification": "Inquiry",
            "analysis": "Mario richiede ferie per la prossima settimana. È necessario approvare o rifiutare.",
            "needs_reply": True,
            "draft_body": "Ciao Mario, ferie approvate. Buona vacanza!",
        },
    ]


def get_dummy_processed_data():
    return [
        {
            "subject": "Newsletter mensile Chino.io",
            "from": "marketing@chino.io",
            "urgency": 1,
            "analysis": "Email informativa mensile per i dipendenti.",
            "thread_id": "194208c8c8c8c8c8",
        },
        {
            "subject": "Accepted: Weekly Sync",
            "from": "collega@chino.io",
            "urgency": 1,
            "analysis": "Conferma automatica di partecipazione al meeting.",
            "thread_id": "194208d8d8d8d8d8",
        },
        {
            "subject": "[console.PROD] WARNING Finance",
            "from": "stripe@chino.io",
            "urgency": 2,
            "analysis": "Notifica di pagamento fallito per un cliente, ma gestito dal team finance.",
            "thread_id": "194208e8e8e8e8e8",
        },
    ]


def get_dummy_mailing_list_data():
    return [
        {
            "subject": "[Python-Dev] PEP 789: New async features",
            "from": "python-dev@python.org",
            "thread_id": "194208f8f8f8f8f8",
        },
        {
            "subject": "[Django-Users] Best practices for migrations",
            "from": "noreply@googlegroups.com",
            "thread_id": "194209a9a9a9a9a9",
        },
        {
            "subject": "Re: [Kubernetes] Scaling strategies discussion",
            "from": "kubernetes-discuss@googlegroups.com",
            "thread_id": "194209b9b9b9b9b9",
        },
    ]


def _preview_mailing_list_report():
    """Generate preview of mailing list report."""
    log_data = get_dummy_mailing_list_data()

    message_parts = [
        "📧 *Report Mailing List (Messaggi Archiviati)*\n",
    ]

    for entry in log_data:
        subject = entry.get("subject", "N/A")
        from_addr = entry.get("from", "N/A")
        thread_id = entry.get("thread_id", "")

        gmail_link = ""
        if thread_id:
            gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"

        link_text = f"<{gmail_link}|🔗>" if gmail_link else ""
        message_parts.append(f"{from_addr[:40]:<40} | {subject[:50]:<50} | {link_text}")

    return "\n - ".join(message_parts)


def main():
    parser = argparse.ArgumentParser(description="Preview Janus notification templates")
    parser.add_argument(
        "template",
        choices=["urgent", "processed", "mailing", "all"],
        default="all",
        nargs="?",
        help="The template to preview (default: all)",
    )
    parser.add_argument(
        "--webhook",
        action="store_true",
        help="Send notifications to Google Chat webhook instead of just previewing",
    )

    args = parser.parse_args()
    notifier = Notifier()

    if args.template in ["urgent", "all"]:
        print("\n" + "=" * 20 + " PREVIEW: URGENT REPORT " + "=" * 20)
        template = notifier.env.get_template("urgent_report.jinja")
        output = template.render(notifications=get_dummy_urgent_data())
        print(output)
        print("=" * 64 + "\n")

        if args.webhook:
            print("📤 Invio notifica urgente a Google Chat...")
            success = notifier.send_consolidated_report(get_dummy_urgent_data())
            if success:
                print("✅ Notifica urgente inviata con successo\n")
            else:
                print("❌ Errore nell'invio della notifica urgente\n")

    if args.template in ["processed", "all"]:
        print("\n" + "=" * 20 + " PREVIEW: PROCESSED REPORT " + "=" * 20)
        template = notifier.env.get_template("processed_report.jinja")
        output = template.render(log_data=get_dummy_processed_data())
        print(output)
        print("=" * 64 + "\n")

        if args.webhook:
            print("📤 Invio report processate a Google Chat...")
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                temp_file = f.name
                json.dump(get_dummy_processed_data(), f)

            original_log_file = Config.PROCESSED_LOG_FILE
            Config.PROCESSED_LOG_FILE = temp_file
            success = notifier.send_processed_log_report()
            Config.PROCESSED_LOG_FILE = original_log_file

            try:
                os.unlink(temp_file)
            except Exception:
                pass

            if success:
                print("✅ Report processate inviato con successo\n")
            else:
                print("❌ Errore nell'invio del report processate\n")

    if args.template in ["mailing", "all"]:
        print("\n" + "=" * 20 + " PREVIEW: MAILING LIST REPORT " + "=" * 20)
        output = _preview_mailing_list_report()
        print(output)
        print("=" * 64 + "\n")

        if args.webhook:
            print("📤 Invio report mailing list a Google Chat...")
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                temp_file = f.name
                json.dump(get_dummy_mailing_list_data(), f)

            original_log_file = Config.MAILING_LIST_LOG_FILE
            Config.MAILING_LIST_LOG_FILE = temp_file
            success = send_mailing_list_report()
            Config.MAILING_LIST_LOG_FILE = original_log_file

            try:
                os.unlink(temp_file)
            except Exception:
                pass

            if success:
                print("✅ Report mailing list inviato con successo\n")
            else:
                print("❌ Errore nell'invio del report mailing list\n")


if __name__ == "__main__":
    main()
