#!/usr/bin/env python3
"""Command to provide feedback on email evaluations."""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime

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


def _save_feedback(
    thread_id: str,
    subject: str,
    original_urgency: int,
    correct_urgency: int,
    original_classification: str,
    correct_classification: str,
    notes: str,
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

    print(f"✅ Feedback salvato per: {subject}")


def provide_feedback() -> None:
    """Interactive command to provide feedback on processed emails."""
    print("📝 Sistema di Feedback per Valutazione Email\n")

    while True:
        # Load processed messages (reload each time for fresh data)
        processed = _load_processed_log()

        if not processed:
            print("❌ Nessun messaggio processato da valutare.")
            print("   Esegui prima 'poetry run python -m src.main'")
            return

        print(f"\nTrovati {len(processed)} messaggi processati.\n")

        # Show list
        for i, entry in enumerate(processed, 1):
            subject = entry.get("subject", "N/A")
            urgency = entry.get("urgency", 0)
            classification = entry.get("classification", "N/A")
            notified = entry.get("notified", False)
            notified_icon = "🔔" if notified else "🔕"
            print(f"{i}. {notified_icon} {subject}")
            print(f"   Urgenza: {urgency}/5 | Categoria: {classification}\n")

        # Ask user to select
        try:
            choice = input(
                "Seleziona il numero del messaggio da valutare (0 per uscire): "
            )
            choice_num = int(choice)

            if choice_num == 0:
                print("👋 Uscita.")
                return

            if choice_num < 1 or choice_num > len(processed):
                print("❌ Selezione non valida.")
                continue

            selected = processed[choice_num - 1]

        except (ValueError, KeyboardInterrupt):
            print("\n❌ Operazione annullata.")
            return

        # Show details
        print(f"\n{'=' * 60}")
        print(f"Messaggio selezionato: {selected.get('subject', 'N/A')}")
        print(f"Urgenza originale: {selected.get('urgency', 0)}/5")
        print(f"Categoria originale: {selected.get('classification', 'N/A')}")
        print(f"Analisi: {selected.get('analysis', 'N/A')}")
        print(f"{'=' * 60}\n")

        # Get feedback
        try:
            correct_urgency = int(
                input("Urgenza corretta (1-5): ") or selected.get("urgency", 3)
            )
            correct_urgency = max(1, min(5, correct_urgency))

            correct_classification = input(
                f"Categoria corretta [{selected.get('classification', 'N/A')}]: "
            ) or selected.get("classification", "N/A")

            notes = input("Note aggiuntive (opzionale): ") or ""

            # Save feedback
            _save_feedback(
                selected.get("thread_id", ""),
                selected.get("subject", ""),
                selected.get("urgency", 0),
                correct_urgency,
                selected.get("classification", ""),
                correct_classification,
                notes,
            )

            print("\n✅ Feedback registrato con successo!")
            print(
                "\n💡 Usa 'poetry run python -m src.feedback --analyze' "
                "per analizzare i feedback e aggiornare le regole.\n"
            )

        except (ValueError, KeyboardInterrupt):
            print("\n❌ Operazione annullata, torno alla lista.\n")
            continue


def analyze_feedback(clear_logs: bool = False) -> None:
    """Analyze feedback and generate evaluation rules.

    Args:
        clear_logs: If True, clear processed logs after analysis.
    """
    print("🔍 Analisi Feedback e Generazione Regole\n")

    if not os.path.exists(Config.FEEDBACK_FILE):
        print("❌ Nessun feedback disponibile.")
        return

    try:
        with open(Config.FEEDBACK_FILE, "r") as f:
            feedback_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print("❌ Errore lettura file feedback.")
        return

    if not feedback_data:
        print("❌ Nessun feedback disponibile.")
        return

    print(f"Trovati {len(feedback_data)} feedback.\n")

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
    rules.append("# Regole di Valutazione Email - Generate da Feedback\n")
    rules.append(f"# Generato: {datetime.now().isoformat()}\n")
    rules.append(f"# Basato su {len(feedback_data)} feedback\n\n")

    if urgency_adjustments:
        rules.append("## Aggiustamenti Urgenza:\n")
        for adj in urgency_adjustments:
            rules.append(f"- '{adj['subject']}': urgenza {adj['from']} → {adj['to']}")
            if adj["notes"]:
                rules.append(f"  Note: {adj['notes']}")
            rules.append("\n")

    if classification_changes:
        rules.append("\n## Cambiamenti Classificazione:\n")
        for change in classification_changes:
            rules.append(f"- '{change['subject']}': {change['from']} → {change['to']}")
            if change["notes"]:
                rules.append(f"  Note: {change['notes']}")
            rules.append("\n")

    # Add general patterns
    rules.append("\n## Regole Generali da Applicare:\n")
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

    print(f"✅ Regole salvate in: {Config.RULES_FILE}\n")
    print("Contenuto regole:")
    print("".join(rules))

    # Clear logs if requested
    if clear_logs:
        print("\n" + "=" * 60)
        _clear_processed_logs_silent()


def _clear_processed_logs_silent() -> None:
    """Clear processed logs without confirmation (internal use)."""
    print("\n🗑️  Svuotamento File Log Messaggi Processati\n")

    files_to_clear = []
    if os.path.exists(Config.PROCESSED_LOG_FILE):
        files_to_clear.append((Config.PROCESSED_LOG_FILE, "non notificati"))
    if os.path.exists(Config.NOTIFIED_LOG_FILE):
        files_to_clear.append((Config.NOTIFIED_LOG_FILE, "notificati"))

    if not files_to_clear:
        print("✅ Nessun file log da svuotare.")
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
            print(f"✅ Svuotato: {desc} ({count} messaggi)")
            cleared += 1
        except Exception as e:
            print(f"❌ Errore svuotamento {desc}: {e}")

    print(f"\n✅ {cleared} file svuotati con successo!")


def clear_processed_logs() -> None:
    """Clear processed message log files after learning from feedback."""
    print("🗑️  Svuotamento File Log Messaggi Processati\n")

    files_to_clear = []
    if os.path.exists(Config.PROCESSED_LOG_FILE):
        files_to_clear.append((Config.PROCESSED_LOG_FILE, "non notificati"))
    if os.path.exists(Config.NOTIFIED_LOG_FILE):
        files_to_clear.append((Config.NOTIFIED_LOG_FILE, "notificati"))

    if not files_to_clear:
        print("✅ Nessun file log da svuotare.")
        return

    print("File da svuotare:")
    for filepath, desc in files_to_clear:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                count = len(data)
            print(f"  • {desc}: {count} messaggi")
        except Exception:
            print(f"  • {desc}: file vuoto o non valido")

    print("\n⚠️  Questa operazione cancellerà tutti i messaggi processati dai file log.")
    print(
        "Assicurati di aver già dato feedback e analizzato con "
        "'--analyze' prima di procedere.\n"
    )

    response = input("Vuoi procedere? (y/n): ")

    if not response.lower().startswith("y"):
        print("❌ Operazione annullata.")
        return

    # Clear files
    cleared = 0
    for filepath, desc in files_to_clear:
        try:
            with open(filepath, "w") as f:
                json.dump([], f)
            print(f"✅ Svuotato: {desc}")
            cleared += 1
        except Exception as e:
            print(f"❌ Errore svuotamento {desc}: {e}")

    print(f"\n✅ {cleared} file svuotati con successo!")
    print("\nI messaggi futuri verranno salvati nei file log per nuovi feedback.")


def export_feedback_template() -> None:
    """Export processed messages to CSV for manual feedback editing."""
    print("📤 Esportazione Template Feedback\n")

    processed = _load_processed_log()

    if not processed:
        print("❌ Nessun messaggio processato da esportare.")
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
                    "original_urgency",
                    "correct_urgency",
                    "original_classification",
                    "correct_classification",
                    "notes",
                ],
            )
            writer.writeheader()

            for entry in processed:
                writer.writerow(
                    {
                        "thread_id": entry.get("thread_id", ""),
                        "subject": entry.get("subject", ""),
                        "original_urgency": entry.get("urgency", ""),
                        "correct_urgency": "",  # Da compilare
                        "original_classification": entry.get("classification", ""),
                        "correct_classification": "",  # Da compilare
                        "notes": "",  # Da compilare
                    }
                )

        print(f"✅ Template esportato: {csv_file}")
        print(f"   Messaggi esportati: {len(processed)}\n")
        print("📝 Istruzioni:")
        print("   1. Apri il file CSV con Excel/Numbers/LibreOffice")
        print("   2. Compila le colonne:")
        print("      - correct_urgency: urgenza corretta (1-5)")
        print("      - correct_classification: categoria corretta (opzionale)")
        print("      - notes: note aggiuntive (opzionale)")
        print("   3. Salva il file")
        print(
            "   4. Importa: poetry run python -m src.feedback --import "
            "feedback_template.csv\n"
        )

    except Exception as e:
        print(f"❌ Errore esportazione: {e}")


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
                original_urgency = row.get("original_urgency", "").strip()
                correct_urgency = row.get("correct_urgency", "").strip()
                original_classification = row.get("original_classification", "").strip()
                correct_classification = row.get("correct_classification", "").strip()
                notes = row.get("notes", "").strip()

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

                # Save feedback
                _save_feedback(
                    thread_id,
                    subject,
                    original_urgency_int,
                    correct_urgency_int,
                    original_classification,
                    correct_classification,
                    notes,
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
