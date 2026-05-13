from __future__ import annotations

import json
import sys
from datetime import datetime

from .config import Config
from .feedback import collect_label_feedback
from .gmail_client import GmailClient
from .llm_processor import LLMProcessor
from .notifier import Notifier


def _log_processed_message(
    thread_id: str,
    subject: str,
    classification: str,
    urgency: int,
    analysis: str,
    notified: bool,
    from_addr: str = "N/A",
    to_addr: str = "N/A",
) -> None:
    """Log processed messages to appropriate file.

    Args:
        thread_id: The thread ID.
        subject: Email subject.
        classification: Email classification.
        urgency: Urgency level.
        analysis: Analysis text.
        notified: Whether notification was sent.
        from_addr: Email sender address.
        to_addr: Email recipient address.
    """
    import os

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "thread_id": thread_id,
        "subject": subject,
        "from": from_addr,
        "to": to_addr,
        "classification": classification,
        "urgency": urgency,
        "analysis": analysis,
    }

    # Choose file based on notification status
    log_file = Config.NOTIFIED_LOG_FILE if notified else Config.PROCESSED_LOG_FILE

    # Read existing log
    log_data = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                log_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            log_data = []

    # Append new entry
    log_data.append(log_entry)

    # Write back
    with open(log_file, "w") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)


def _log_mailing_list_message(
    thread_id: str,
    subject: str,
    from_addr: str,
) -> None:
    """Log mailing list messages to separate file.

    Args:
        thread_id: The thread ID.
        subject: Email subject.
        from_addr: Email sender address.
    """
    import os

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "thread_id": thread_id,
        "subject": subject,
        "from": from_addr,
    }

    # Read existing log
    log_data = []
    if os.path.exists(Config.MAILING_LIST_LOG_FILE):
        try:
            with open(Config.MAILING_LIST_LOG_FILE, "r") as f:
                log_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            log_data = []

    # Append new entry
    log_data.append(log_entry)

    # Write back
    with open(Config.MAILING_LIST_LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)


def run_janus() -> None:
    """Orchestrate Gmail LLM processing workflow with new logic.

    New workflow:
    1. Get unread messages since last run (or last 2 days if first run)
    2. Filter messages where user is in To/CC (exclude mailing lists)
    3. Analyze with LLM
    4. Send notification only if urgency > 2
    5. Mark as read and save timestamp
    """
    start_time = datetime.now()
    print(f"🚀 Inizializzazione Janus... [{start_time.strftime('%Y-%m-%d %H:%M:%S')}]")
    try:
        Config.validate()
    except Exception as e:
        print(f"❌ Errore configurazione: {e}")
        sys.exit(1)

    gmail = GmailClient()
    llm = LLMProcessor()
    notifier = Notifier()

    # Collect any Gmail-label feedback before processing new mail
    n_feedback = collect_label_feedback(gmail)
    if n_feedback:
        print(f"📝 Raccolti {n_feedback} feedback da label Gmail")

    # Get unread messages since last run
    messages = gmail.get_unread_messages_since_last_run(Config.TARGET_LABEL)

    if not messages:
        end_time = datetime.now()
        print(
            f"✅ Nessun nuovo messaggio da processare. [{end_time.strftime('%Y-%m-%d %H:%M:%S')}]"
        )
        gmail._save_last_run_timestamp()
        return

    # Filter messages where user is recipient and sender is not no-reply
    print(f"🔍 Filtering messages where {Config.USER_EMAIL} is a recipient...")
    filtered_messages = []
    mailing_list_count = 0

    for msg in messages:
        msg_id = msg["id"]
        thread_id = msg["threadId"]

        # First, check if this is the Janus report email
        is_recipient, msg_info = gmail.is_user_recipient(msg_id, Config.USER_EMAIL)
        subject = msg_info.get("subject", "N/A")
        
        if subject.startswith("[Janus]"):
            print(f"  ⏭️  Saltato messaggio {msg_id[:8]}... (Report Janus mantenuto in inbox)")
            continue

        # Check if sender is valid (not no-reply)
        if not gmail.is_valid_sender(msg_id):
            # Get message info for logging (already have it, but for safety in case of changes)
            from_addr = msg_info.get("from", "N/A")

            print(f"  📧 Mailing list {msg_id[:8]}... ({from_addr})")

            # Log mailing list message
            _log_mailing_list_message(thread_id, subject, from_addr)

            # Add janus-ml label and archive
            gmail.mark_as_read(thread_id, "janus-ml")
            gmail.archive_thread(thread_id)
            mailing_list_count += 1
            continue

        # Check if user is in To/CC
        if is_recipient:
            filtered_messages.append(msg)
        else:
            # Log detailed info for skipped messages
            from_addr = msg_info.get("from", "N/A")
            to_addr = msg_info.get("to", "N/A")
            print(
                f"  ⏭️  Saltato messaggio {msg_id[:8]}... "
                f"(utente non in To/CC)\n"
                f"      Da: {from_addr}\n"
                f"      A: {to_addr}\n"
                f"      Oggetto: {subject}"
            )

    if mailing_list_count > 0:
        print(f"📧 {mailing_list_count} messaggi da mailing list archiviati")

    if not filtered_messages:
        end_time = datetime.now()
        print(
            f"✅ Nessun messaggio rilevante dopo il filtro. [{end_time.strftime('%Y-%m-%d %H:%M:%S')}]"
        )
        gmail._save_last_run_timestamp()
        return

    print(f"📦 {len(filtered_messages)} messaggi rilevanti da analizzare.")

    # Group messages by thread
    threads_map = {}
    for msg in filtered_messages:
        thread_id = msg["threadId"]
        if thread_id not in threads_map:
            threads_map[thread_id] = []
        threads_map[thread_id].append(msg)

    print(f"📧 Organizzati in {len(threads_map)} thread unici.")

    processed_count = 0
    notified_count = 0
    notifications_to_send = []  # Collect all notifications

    # Process threads in batches
    BATCH_SIZE = 10
    thread_ids = list(threads_map.keys())

    for batch_start in range(0, len(thread_ids), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(thread_ids))
        batch_thread_ids = thread_ids[batch_start:batch_end]

        print(f"\n{'=' * 60}")
        print(
            f"📦 Batch {batch_start // BATCH_SIZE + 1}: processando {len(batch_thread_ids)} thread..."
        )

        # Collect thread contents for batch
        batch_contents = []
        thread_details_map = {}

        for thread_id in batch_thread_ids:
            details = gmail.get_thread_details(thread_id)
            if details:
                batch_contents.append((thread_id, details["content"]))
                thread_details_map[thread_id] = details
            else:
                print(f"⚠️  Thread {thread_id[:8]}... dettagli non recuperabili")

        if not batch_contents:
            continue

        # Batch LLM Analysis
        print(f"🤖 Analisi batch con Gemini ({len(batch_contents)} thread)...")
        batch_results = llm.analyze_threads_batch(batch_contents)

        # Process results
        for thread_id, analysis in batch_results:
            if thread_id not in thread_details_map:
                continue

            details = thread_details_map[thread_id]

            print(f"\n  📧 {details['subject'][:50]}...")

            if not analysis:
                print("  ⚠️  Errore nell'analisi LLM.")
                continue

            urgency = getattr(analysis, "urgency", 3)
            classification = getattr(analysis, "classification", "N/A")
            analysis_text = getattr(analysis, "analysis", "N/A")
            summary = getattr(analysis, "summary", "")
            latest_message_summary = getattr(analysis, "latest_message_summary", "")
            needs_reply = getattr(analysis, "needs_reply", False)
            draft_body = getattr(analysis, "draft_body", None)
            is_mailing_list = getattr(analysis, "is_mailing_list", False)
            print(f"  📊 Urgenza: {urgency}/5 | {classification}")

            # If identified as mailing list, add sender to exclusion list
            if is_mailing_list:
                from_addr = details.get("from", "N/A")
                print(f"  📧 Rilevata mailing list: {from_addr}")
                if gmail.add_to_excluded_senders(from_addr):
                    print(f"  ✅ Sender escluso dalle future elaborazioni")
                # Archive and mark with janus-ml label
                gmail.mark_as_read(thread_id, "janus-ml")
                gmail.archive_thread(thread_id)
                _log_mailing_list_message(thread_id, details["subject"], from_addr)
                processed_count += 1
                continue

            # Collect notification if urgency > 2
            notified = False
            if urgency > 2:
                notifications_to_send.append(
                    {
                        "thread_id": thread_id,
                        "subject": details["subject"],
                        "from": details.get("from", "N/A"),
                        "to": details.get("to", "N/A"),
                        "urgency": urgency,
                        "classification": classification,
                        "analysis": analysis_text,
                        "summary": summary,
                        "latest_message_summary": latest_message_summary,
                        "needs_reply": needs_reply,
                        "draft_body": draft_body,
                    }
                )
                notified_count += 1
                notified = True

            # Log all processed messages (notified or not)
            _log_processed_message(
                thread_id,
                details["subject"],
                classification,
                urgency,
                analysis_text,
                notified,
                details.get("from", "N/A"),
                details.get("to", "N/A"),
            )

            # Mark thread as read and add janus label
            gmail.mark_as_read(thread_id, Config.TARGET_LABEL)

            # Archive non-priority emails (urgency 1-2)
            if urgency <= 2:
                gmail.archive_thread(thread_id)
                print(f"  📦 Archiviato (non prioritario)")

            processed_count += 1

    # Send consolidated notification report
    if notifications_to_send:
        print(f"\n{'=' * 60}")
        print(
            f"📤 Invio report riepilogativo ({len(notifications_to_send)} email urgenti)..."
        )
        notifier.send_consolidated_report(notifications_to_send)

    # Save timestamp for next run
    gmail._save_last_run_timestamp()

    end_time = datetime.now()
    print(f"\n{'=' * 60}")
    print(f"✅ Elaborazione completata [{end_time.strftime('%Y-%m-%d %H:%M:%S')}]:")
    print(f"   • Thread processati: {processed_count}")
    print(f"   • Notifiche inviate: {notified_count}")


if __name__ == "__main__":
    run_janus()
