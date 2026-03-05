#!/usr/bin/env python3
"""Script to preview Google Chat notification templates with dummy data."""

from __future__ import annotations

import argparse
from .notifier import Notifier

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
            "draft_body": "Ciao, ho ricevuto la segnalazione. Me ne occupo subito e vi aggiorno tra 15 minuti."
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
            "draft_body": "Ciao Mario, ferie approvate. Buona vacanza!"
        }
    ]

def get_dummy_processed_data():
    return [
        {
            "subject": "Newsletter mensile Chino.io",
            "from": "marketing@chino.io",
            "urgency": 1,
            "analysis": "Email informativa mensile per i dipendenti.",
            "thread_id": "194208c8c8c8c8c8"
        },
        {
            "subject": "Accepted: Weekly Sync",
            "from": "collega@chino.io",
            "urgency": 1,
            "analysis": "Conferma automatica di partecipazione al meeting.",
            "thread_id": "194208d8d8d8d8d8"
        },
        {
            "subject": "[console.PROD] WARNING Finance",
            "from": "stripe@chino.io",
            "urgency": 2,
            "analysis": "Notifica di pagamento fallito per un cliente, ma gestito dal team finance.",
            "thread_id": "194208e8e8e8e8e8"
        }
    ]

def main():
    parser = argparse.ArgumentParser(description="Preview Janus notification templates")
    parser.add_argument("template", choices=["urgent", "processed", "all"], default="all", nargs="?",
                        help="The template to preview (default: all)")
    
    args = parser.parse_args()
    notifier = Notifier()

    if args.template in ["urgent", "all"]:
        print("\n" + "="*20 + " PREVIEW: URGENT REPORT " + "="*20)
        template = notifier.env.get_template("urgent_report.jinja")
        output = template.render(notifications=get_dummy_urgent_data())
        print(output)
        print("="*64 + "\n")

    if args.template in ["processed", "all"]:
        print("\n" + "="*20 + " PREVIEW: PROCESSED REPORT " + "="*20)
        template = notifier.env.get_template("processed_report.jinja")
        output = template.render(log_data=get_dummy_processed_data())
        print(output)
        print("="*64 + "\n")

if __name__ == "__main__":
    main()
