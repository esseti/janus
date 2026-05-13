#!/usr/bin/env python3
"""Command to provide feedback on email evaluations."""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path

from .config import Config


def _load_processed_log() -> list[dict]:
    """Load all processed messages (both notified and not notified).

    Returns:
        List of unique processed message entries with 'notified' flag.
    """
    all_messages = []

    # Load not notified messages
    if os.path.exists(Config.PROCESSED_LOG_FILE):
        try:
            with open(Config.PROCESSED_LOG_FILE, "r") as f:
                not_notified = json.load(f)
                for msg in not_notified:
                    msg["notified"] = False
                all_messages.extend(not_notified)
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # Load notified messages
    if os.path.exists(Config.NOTIFIED_LOG_FILE):
        try:
            with open(Config.NOTIFIED_LOG_FILE, "r") as f:
                notified = json.load(f)
                for msg in notified:
                    msg["notified"] = True
                all_messages.extend(notified)
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # Remove duplicates by thread_id (keep most recent)
    seen_threads = {}
    for msg in all_messages:
        thread_id = msg.get("thread_id")
        timestamp = msg.get("timestamp", "")
        if thread_id:
            if thread_id not in seen_threads or timestamp > seen_threads[thread_id].get(
                "timestamp", ""
            ):
                seen_threads[thread_id] = msg

    # Convert back to list and sort by timestamp (most recent first)
    unique_messages = list(seen_threads.values())
    unique_messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return unique_messages


def _add_sender_to_excluded(sender_email: str) -> bool:
    """Add sender email to excluded_senders.txt file.

    Args:
        sender_email: The email address to add to exclusion list.

    Returns:
        True if successfully added, False otherwise.
    """
    excluded_file = Config.EXCLUDED_SENDERS_FILE

    try:
        # Read existing entries
        existing_entries = []
        if excluded_file.exists():
            with open(excluded_file, "r", encoding="utf-8") as f:
                existing_entries = [
                    line.strip().lower()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]

        # Check if already exists
        sender_lower = sender_email.lower()
        if sender_lower in existing_entries:
            print(f"ℹ️  '{sender_email}' already in excluded_senders.txt")
            return True

        # Append to file
        with open(excluded_file, "a", encoding="utf-8") as f:
            f.write(f"{sender_email}\n")

        print(f"✅ '{sender_email}' aggiunto a excluded_senders.txt")
        return True

    except Exception as e:
        print(f"❌ Errore aggiunta sender a excluded_senders.txt: {e}")
        return False


def _save_feedback(
    thread_id: str,
    subject: str,
    original_urgency: int,
    correct_urgency: int,
    original_classification: str,
    correct_classification: str,
    notes: str,
    add_to_excluded: bool = False,
    sender_email: str = "",
) -> None:
    """Save feedback to file.

    Args:
        thread_id: The thread ID.
        subject: Email subject.
        original_urgency: Original urgency assigned by LLM.
        correct_urgency: Correct urgency provided by user.
        original_classification: Original classification by LLM.
        correct_classification: Correct classification by user.
        notes: User notes.
        add_to_excluded: If True, add sender to excluded_senders.txt.
        sender_email: The sender email address (required if add_to_excluded is True).
    """
    feedback_entry = {
        "timestamp": datetime.now().isoformat(),
        "thread_id": thread_id,
        "subject": subject,
        "original_urgency": original_urgency,
        "correct_urgency": correct_urgency,
        "original_classification": original_classification,
        "correct_classification": correct_classification,
        "notes": notes,
        "add_to_excluded": add_to_excluded,
        "sender_email": sender_email,
    }

    # Read existing feedback
    feedback_data = []
    if os.path.exists(Config.FEEDBACK_FILE):
        try:
            with open(Config.FEEDBACK_FILE, "r") as f:
                feedback_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            feedback_data = []

    # Append new feedback
    feedback_data.append(feedback_entry)

    # Write back
    with open(Config.FEEDBACK_FILE, "w") as f:
        json.dump(feedback_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Feedback saved for: {subject}")

    # Add sender to excluded list if requested
    if add_to_excluded and sender_email:
        _add_sender_to_excluded(sender_email)


def collect_label_feedback(gmail) -> int:
    """Read feedback labels from Gmail and save entries to feedback.json.

    Looks for threads labeled janus/urgent or janus/not-urgent, saves a
    feedback entry for each one (matching against the processed log for the
    original urgency/classification), then removes the feedback label.

    Args:
        gmail: An authenticated GmailClient instance.

    Returns:
        Number of feedback entries collected.
    """
    labeled = gmail.get_feedback_labeled_threads()
    if not labeled:
        return 0

    processed = _load_processed_log()
    processed_by_thread = {m.get("thread_id"): m for m in processed}

    count = 0
    for item in labeled:
        thread_id = item["thread_id"]
        feedback_type = item["feedback_type"]
        label_id = item["label_id"]
        subject = item["subject"]
        from_addr = item["from_addr"]

        original = processed_by_thread.get(thread_id)
        original_urgency = original.get("urgency", 0) if original else 0
        original_classification = original.get("classification", "N/A") if original else "N/A"

        correct_urgency = 5 if feedback_type == "urgent" else 1

        _save_feedback(
            thread_id=thread_id,
            subject=subject,
            original_urgency=original_urgency,
            correct_urgency=correct_urgency,
            original_classification=original_classification,
            correct_classification=original_classification,
            notes=f"label-feedback:{feedback_type}",
            add_to_excluded=False,
            sender_email=from_addr,
        )
        gmail.remove_label_from_thread(thread_id, label_id)
        direction = "↑ urgent" if feedback_type == "urgent" else "↓ not-urgent"
        print(f"  📝 Feedback [{direction}]: {subject[:50]}")
        count += 1

    return count


def provide_feedback() -> None:
    """Interactive command to provide feedback on processed emails."""
    print("📝 Email Feedback System\n")

    while True:
        # Load processed messages (reload each time for fresh data)
        processed = _load_processed_log()

        if not processed:
            print("❌ No processed messages to review.")
            print("   Run 'python -m src.main' first.")
            return

        print(f"\n{len(processed)} processed messages found.\n")

        # Show list
        for i, entry in enumerate(processed, 1):
            subject = entry.get("subject", "N/A")
            urgency = entry.get("urgency", 0)
            classification = entry.get("classification", "N/A")
            notified = entry.get("notified", False)
            notified_icon = "🔔" if notified else "🔕"
            print(f"{i}. {notified_icon} {subject}")
            print(f"   Urgency: {urgency}/5 | Category: {classification}\n")

        # Ask user to select
        try:
            choice = input(
                "Select message number to review (0 to exit): "
            )
            choice_num = int(choice)

            if choice_num == 0:
                print("👋 Exiting.")
                return

            if choice_num < 1 or choice_num > len(processed):
                print("❌ Invalid selection.")
                continue

            selected = processed[choice_num - 1]

        except (ValueError, KeyboardInterrupt):
            print("\n❌ Operation cancelled.")
            return

        # Show details
        print(f"\n{'=' * 60}")
        print(f"Selected message: {selected.get('subject', 'N/A')}")
        print(f"From: {selected.get('from', 'N/A')}")
        print(f"Original urgency: {selected.get('urgency', 0)}/5")
        print(f"Original category: {selected.get('classification', 'N/A')}")
        print(f"Analysis: {selected.get('analysis', 'N/A')}")
        print(f"{'=' * 60}\n")

        # Get feedback
        try:
            correct_urgency = int(
                input("Correct urgency (1-5): ") or selected.get("urgency", 3)
            )
            correct_urgency = max(1, min(5, correct_urgency))

            correct_classification = input(
                f"Correct category [{selected.get('classification', 'N/A')}]: "
            ) or selected.get("classification", "N/A")

            notes = input("Additional notes (optional): ") or ""

            # Ask if sender should be added to excluded list
            add_to_excluded_input = input(
                "Add this sender to the exclusion list? (y/n) [n]: "
            ).lower()
            add_to_excluded = add_to_excluded_input.startswith("y")

            sender_email = selected.get("from", "")

            # Save feedback
            _save_feedback(
                selected.get("thread_id", ""),
                selected.get("subject", ""),
                selected.get("urgency", 0),
                correct_urgency,
                selected.get("classification", ""),
                correct_classification,
                notes,
                add_to_excluded,
                sender_email,
            )

            print("\n✅ Feedback recorded successfully!")
            print(
                "\n💡 Run 'python -m src.feedback --analyze' "
                "to analyse feedback and update the rules.\n"
            )

        except (ValueError, KeyboardInterrupt):
            print("\n❌ Operation cancelled, returning to list.\n")
            continue


def analyze_feedback(clear_logs: bool = False) -> None:
    """Analyze feedback and generate evaluation rules.

    Args:
        clear_logs: If True, clear processed logs after analysis.
    """
    print("🔍 Feedback Analysis & Rule Generation\n")

    if not os.path.exists(Config.FEEDBACK_FILE):
        print("❌ No feedback available.")
        return

    try:
        with open(Config.FEEDBACK_FILE, "r") as f:
            feedback_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print("❌ Error reading feedback file.")
        return

    if not feedback_data:
        print("❌ No feedback available.")
        return

    print(f"{len(feedback_data)} feedback entries found.\n")

    # Analyze patterns
    urgency_adjustments = []
    classification_changes = []

    for entry in feedback_data:
        orig_urg = entry.get("original_urgency", 0)
        corr_urg = entry.get("correct_urgency", 0)
        orig_class = entry.get("original_classification", "")
        corr_class = entry.get("correct_classification", "")
        subject = entry.get("subject", "")
        notes = entry.get("notes", "")

        if orig_urg != corr_urg:
            urgency_adjustments.append(
                {
                    "subject": subject,
                    "from": orig_urg,
                    "to": corr_urg,
                    "notes": notes,
                }
            )

        if orig_class != corr_class:
            classification_changes.append(
                {
                    "subject": subject,
                    "from": orig_class,
                    "to": corr_class,
                    "notes": notes,
                }
            )

    # Generate rules
    rules = []
    rules.append("# Email Evaluation Rules - Generated from Feedback\n")
    rules.append(f"# Generated: {datetime.now().isoformat()}\n")
    rules.append(f"# Based on {len(feedback_data)} feedback entries\n\n")

    if urgency_adjustments:
        rules.append("## Urgency Adjustments:\n")
        for adj in urgency_adjustments:
            rules.append(f"- '{adj['subject']}': urgency {adj['from']} → {adj['to']}")
            if adj["notes"]:
                rules.append(f"  Notes: {adj['notes']}")
            rules.append("\n")

    if classification_changes:
        rules.append("\n## Classification Changes:\n")
        for change in classification_changes:
            rules.append(f"- '{change['subject']}': {change['from']} → {change['to']}")
            if change["notes"]:
                rules.append(f"  Notes: {change['notes']}")
            rules.append("\n")

    # Add general patterns
    rules.append("\n## General Rules to Apply:\n")
    rules.append(
        "- Email di calendario (Accepted/Declined): urgenza 1, categoria Information\n"
    )
    rules.append("- Newsletter commerciali: urgenza 1-2, categoria Information\n")
    rules.append(
        "- Email con richieste esplicite di azione: "
        "urgenza minima 3, categoria Inquiry/Urgent\n"
    )

    # Save rules
    with open(Config.RULES_FILE, "w") as f:
        f.writelines(rules)

    print(f"✅ Rules saved to: {Config.RULES_FILE}\n")
    print("Contenuto regole:")
    print("".join(rules))

    # Clear logs if requested
    if clear_logs:
        print("\n" + "=" * 60)
        _clear_processed_logs_silent()


def _clear_processed_logs_silent() -> None:
    """Clear processed logs without confirmation (internal use)."""
    print("\n🗑️  Clearing Processed Message Log Files\n")

    files_to_clear = []
    if os.path.exists(Config.PROCESSED_LOG_FILE):
        files_to_clear.append((Config.PROCESSED_LOG_FILE, "not notified"))
    if os.path.exists(Config.NOTIFIED_LOG_FILE):
        files_to_clear.append((Config.NOTIFIED_LOG_FILE, "notified"))

    if not files_to_clear:
        print("✅ No log files to clear.")
        return

    # Clear files
    cleared = 0
    for filepath, desc in files_to_clear:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                count = len(data)
            with open(filepath, "w") as f:
                json.dump([], f)
            print(f"✅ Cleared: {desc} ({count} messages)")
            cleared += 1
        except Exception as e:
            print(f"❌ Error clearing {desc}: {e}")

    print(f"\n✅ {cleared} files cleared successfully!")


def clear_processed_logs() -> None:
    """Clear processed message log files after learning from feedback."""
    print("🗑️  Clearing Processed Message Log Files\n")

    files_to_clear = []
    if os.path.exists(Config.PROCESSED_LOG_FILE):
        files_to_clear.append((Config.PROCESSED_LOG_FILE, "not notified"))
    if os.path.exists(Config.NOTIFIED_LOG_FILE):
        files_to_clear.append((Config.NOTIFIED_LOG_FILE, "notified"))

    if not files_to_clear:
        print("✅ No log files to clear.")
        return

    print("Files to clear:")
    for filepath, desc in files_to_clear:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                count = len(data)
            print(f"  • {desc}: {count} messages")
        except Exception:
            print(f"  • {desc}: empty or invalid file")

    print("\n⚠️  This will permanently delete all processed messages from the log files.")
    print(
        "Make sure you have already provided feedback and run "
        "'--analyze' before proceeding.\n"
    )

    response = input("Proceed? (y/n): ")

    if not response.lower().startswith("y"):
        print("❌ Operation cancelled.")
        return

    # Clear files
    cleared = 0
    for filepath, desc in files_to_clear:
        try:
            with open(filepath, "w") as f:
                json.dump([], f)
            print(f"✅ Cleared: {desc}")
            cleared += 1
        except Exception as e:
            print(f"❌ Error clearing {desc}: {e}")

    print(f"\n✅ {cleared} files cleared successfully!")
    print("\nFuture messages will be saved to the log files for new feedback.")


def export_feedback_template() -> None:
    """Export processed messages to CSV for manual feedback editing."""
    print("📤 Exporting Feedback Template\n")

    processed = _load_processed_log()

    if not processed:
        print("❌ No processed messages to export.")
        return

    # Create exports directory if it doesn't exist
    exports_dir = "exports"
    if not os.path.exists(exports_dir):
        os.makedirs(exports_dir)

    csv_file = os.path.join(exports_dir, "feedback_template.csv")

    try:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "thread_id",
                    "subject",
                    "sender_email",
                    "original_urgency",
                    "correct_urgency",
                    "original_classification",
                    "correct_classification",
                    "notes",
                    "add_to_excluded",
                ],
            )
            writer.writeheader()

            for entry in processed:
                writer.writerow(
                    {
                        "thread_id": entry.get("thread_id", ""),
                        "subject": entry.get("subject", ""),
                        "sender_email": entry.get("from", ""),
                        "original_urgency": entry.get("urgency", ""),
                        "correct_urgency": "",  # Fill in
                        "original_classification": entry.get("classification", ""),
                        "correct_classification": "",  # Fill in
                        "notes": "",  # Fill in
                        "add_to_excluded": "",  # Fill in (y/n)
                    }
                )

        print(f"✅ Template exported: {csv_file}")
        print(f"   Messages exported: {len(processed)}\n")
        print("📝 Instructions:")
        print("   1. Open the CSV file with Excel/Numbers/LibreOffice")
        print("   2. Fill in the columns:")
        print("      - correct_urgency: correct urgency (1-5)")
        print("      - correct_classification: correct category (optional)")
        print("      - notes: additional notes (optional)")
        print("      - add_to_excluded: y to add to exclusion list (optional)")
        print("   3. Save the file")
        print(
            "   4. Import: python -m src.feedback --import "
            "feedback_template.csv\n"
        )

    except Exception as e:
        print(f"❌ Export error: {e}")


def import_feedback_from_csv(csv_file: str) -> None:
    """Import feedback from manually edited CSV file."""
    print(f"📥 Importazione Feedback da {csv_file}\n")

    # Se il file non esiste, prova in exports/
    if not os.path.exists(csv_file):
        exports_path = os.path.join("exports", csv_file)
        if os.path.exists(exports_path):
            csv_file = exports_path
        else:
            print(f"❌ File non trovato: {csv_file}")
            return

    try:
        imported_count = 0
        skipped_count = 0

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                thread_id = row.get("thread_id", "").strip()
                subject = row.get("subject", "").strip()
                sender_email = row.get("sender_email", "").strip()
                original_urgency = row.get("original_urgency", "").strip()
                correct_urgency = row.get("correct_urgency", "").strip()
                original_classification = row.get("original_classification", "").strip()
                correct_classification = row.get("correct_classification", "").strip()
                notes = row.get("notes", "").strip()
                add_to_excluded_str = row.get("add_to_excluded", "").strip().lower()

                # Skip if no corrections provided
                if not correct_urgency and not correct_classification:
                    skipped_count += 1
                    continue

                # Use original values if corrections not provided
                if not correct_urgency:
                    correct_urgency = original_urgency
                if not correct_classification:
                    correct_classification = original_classification

                try:
                    correct_urgency_int = int(correct_urgency)
                    original_urgency_int = int(original_urgency)
                except ValueError:
                    print(f"⚠️  Riga saltata (urgenza non valida): {subject[:30]}...")
                    skipped_count += 1
                    continue

                # Parse add_to_excluded flag
                add_to_excluded = add_to_excluded_str.startswith("y")

                # Save feedback
                _save_feedback(
                    thread_id,
                    subject,
                    original_urgency_int,
                    correct_urgency_int,
                    original_classification,
                    correct_classification,
                    notes,
                    add_to_excluded,
                    sender_email,
                )
                imported_count += 1

        print(f"✅ Feedback importati: {imported_count}")
        if skipped_count > 0:
            print(f"⏭️  Righe saltate: {skipped_count}")
        print(
            "\n💡 Usa 'poetry run python -m src.feedback --analyze' "
            "per generare le regole.\n"
        )

    except Exception as e:
        print(f"❌ Errore importazione: {e}")


def main() -> None:
    """Main entry point for feedback command."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Sistema di feedback per valutazione email"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analizza i feedback e genera regole di valutazione",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Svuota i file log dei messaggi processati (o usalo con --analyze)",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Esporta messaggi processati in CSV per feedback manuale",
    )
    parser.add_argument(
        "--import",
        dest="import_file",
        metavar="FILE",
        help="Importa feedback da file CSV modificato manualmente",
    )

    args = parser.parse_args()

    if args.analyze:
        analyze_feedback(clear_logs=args.clear)
    elif args.clear:
        clear_processed_logs()
    elif args.export:
        export_feedback_template()
    elif args.import_file:
        import_feedback_from_csv(args.import_file)
    else:
        provide_feedback()


if __name__ == "__main__":
    main()
