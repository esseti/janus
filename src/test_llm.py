#!/usr/bin/env python3
"""Script di test per validare la classificazione LLM delle email."""

from __future__ import annotations

import argparse
import json
import os
import sys

from src.config import Config
from src.llm_processor import LLMProcessor


def load_test_emails(filepath: str = "test_emails.json") -> list[dict]:
    """Carica le email di test dal file JSON.

    Args:
        filepath: Percorso del file JSON con le email di test.

    Returns:
        Lista di dizionari contenenti le email di test.
    """
    # Cerca il file nella directory src se non esiste nella directory corrente
    if not os.path.exists(filepath):
        filepath = os.path.join("src", filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def format_email_content(email: dict) -> str:
    """Formatta il contenuto dell'email per l'analisi LLM.

    Args:
        email: Dizionario con i dati dell'email.

    Returns:
        Stringa formattata con il contenuto dell'email.
    """
    return f"""Subject: {email["subject"]}
From: {email["from"]}
To: {email["to"]}

{email["content"]}"""


def print_separator(char: str = "=", length: int = 80) -> None:
    """Stampa una linea separatrice."""
    print(char * length)


def print_analysis_result(email: dict, analysis) -> None:
    """Stampa i risultati dell'analisi in formato leggibile.

    Args:
        email: Dizionario con i dati dell'email originale.
        analysis: Oggetto EmailAnalysis con i risultati.
    """
    print_separator()
    print(f"📧 EMAIL ID: {email['id']}")
    print(f"📌 OGGETTO: {email['subject']}")
    print(f"👤 DA: {email['from']}")
    print(f"📨 A: {email['to']}")
    print_separator("-")

    if analysis:
        urgency_stars = "⭐" * analysis.urgency
        print(f"\n🏷️  CLASSIFICAZIONE: {analysis.classification}")
        print(f"🔥 URGENZA: {analysis.urgency}/5 {urgency_stars}")
        print(f"📝 ANALISI: {analysis.analysis}")
        print(f"✉️  RICHIEDE RISPOSTA: {'Sì' if analysis.needs_reply else 'No'}")

        if analysis.needs_reply and analysis.draft_body:
            print("\n💬 BOZZA RISPOSTA SUGGERITA:")
            print_separator("-", 60)
            print(analysis.draft_body)
            print_separator("-", 60)
    else:
        print("\n❌ ERRORE: Analisi fallita")

    print()


def test_individual_analysis(llm: LLMProcessor, emails: list[dict]) -> None:
    """Testa l'analisi individuale di ogni email.

    Args:
        llm: Istanza di LLMProcessor.
        emails: Lista di email da analizzare.
    """
    print("\n" + "=" * 80)
    print("🧪 TEST ANALISI INDIVIDUALE")
    print("=" * 80 + "\n")

    for email in emails:
        content = format_email_content(email)
        analysis = llm.analyze_thread(content)
        print_analysis_result(email, analysis)


def test_batch_analysis(llm: LLMProcessor, emails: list[dict]) -> None:
    """Testa l'analisi batch di tutte le email.

    Args:
        llm: Istanza di LLMProcessor.
        emails: Lista di email da analizzare.
    """
    print("\n" + "=" * 80)
    print("🧪 TEST ANALISI BATCH")
    print("=" * 80 + "\n")

    # Prepara i contenuti per l'analisi batch
    thread_contents = [(email["id"], format_email_content(email)) for email in emails]

    print("\n📦 Analizzando " + str(len(thread_contents)) + " email in batch...\n")

    # Esegui analisi batch
    results = llm.analyze_threads_batch(thread_contents)

    # Stampa risultati
    for (thread_id, analysis), email in zip(results, emails):
        print_analysis_result(email, analysis)


def test_connection(llm: LLMProcessor) -> bool:
    """Testa la connessione al modello LLM.

    Args:
        llm: Istanza di LLMProcessor.

    Returns:
        True se la connessione è riuscita, False altrimenti.
    """
    print("\n" + "=" * 80)
    print("🔌 TEST CONNESSIONE LLM")
    print("=" * 80 + "\n")

    test_email = {
        "id": "test_connection",
        "subject": "Test connessione",
        "from": "test@example.com",
        "to": "stefano@chino.io",
        "content": "Questo è un messaggio di test per verificare la connessione al modello LLM.",
    }

    content = format_email_content(test_email)

    print("📤 Invio messaggio di test al modello LLM...")
    print(f"   Provider: {Config.LLM_PROVIDER}")
    print(f"   Model: {Config.LLM_MODEL}")
    if Config.LLM_PROVIDER == "ollama":
        print(f"   URL: {Config.OLLAMA_BASE_URL}")
    print()

    try:
        analysis = llm.analyze_thread(content)
        if analysis:
            print("✅ CONNESSIONE RIUSCITA!\n")
            print(f"🏷️  Classificazione: {analysis.classification}")
            print(f"🔥 Urgenza: {analysis.urgency}/5")
            print(f"📝 Analisi: {analysis.analysis}")
            print("\n" + "=" * 80)
            print("✅ Il modello LLM è raggiungibile e funzionante")
            print("=" * 80 + "\n")
            return True
        else:
            print("❌ CONNESSIONE FALLITA: Nessuna risposta dal modello")
            return False
    except Exception as e:
        print(f"❌ CONNESSIONE FALLITA: {e}")
        print("\n" + "=" * 80)
        print("💡 SUGGERIMENTI:")
        if Config.LLM_PROVIDER == "ollama":
            print("   - Verifica che Ollama sia in esecuzione: ollama serve")
            print(
                f"   - Verifica che il modello '{Config.LLM_MODEL}' sia installato: ollama list"
            )
            print(f"   - Se non installato, esegui: ollama pull {Config.LLM_MODEL}")
            print(f"   - Verifica l'URL: {Config.OLLAMA_BASE_URL}")
        elif Config.LLM_PROVIDER == "gemini":
            print("   - Verifica che GEMINI_API_KEY sia configurata correttamente")
            print("   - Verifica la connessione internet")
        print("=" * 80 + "\n")
        return False


def main() -> None:
    """Funzione principale del test."""
    # Parse argomenti
    parser = argparse.ArgumentParser(
        description="Test per validare la classificazione LLM delle email"
    )
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Esegui solo il test di connessione al modello LLM",
    )
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("🚀 JANUS LLM TEST - Classificazione Email")
    print("=" * 80)

    # Valida configurazione
    try:
        Config.validate()
    except Exception as e:
        print(f"\n❌ Errore configurazione: {e}")
        print("\nAssicurati di aver configurato correttamente il file .env")
        sys.exit(1)

    # Mostra configurazione LLM
    print("\n⚙️  CONFIGURAZIONE LLM:")
    print(f"   Provider: {Config.LLM_PROVIDER}")
    print(f"   Model: {Config.LLM_MODEL}")
    print(f"   Temperature: {Config.LLM_TEMPERATURE}")
    if Config.LLM_PROVIDER == "ollama":
        print(f"   Ollama URL: {Config.OLLAMA_BASE_URL}")

    # Inizializza LLM processor
    print("\n🤖 Inizializzazione LLM processor...")
    try:
        llm = LLMProcessor()
        print("✅ LLM processor inizializzato correttamente")
    except Exception as e:
        print(f"❌ Errore inizializzazione LLM: {e}")
        sys.exit(1)

    # Se richiesto solo test connessione
    if args.test_connection:
        success = test_connection(llm)
        sys.exit(0 if success else 1)

    # Carica email di test
    try:
        emails = load_test_emails()
        print(f"\n✅ Caricate {len(emails)} email di test")
    except FileNotFoundError:
        print("\n❌ File test_emails.json non trovato!")
        sys.exit(1)

    # Chiedi all'utente quale test eseguire
    print("\n" + "=" * 80)
    print("Scegli il tipo di test:")
    print("  1 - Analisi individuale (una email alla volta)")
    print("  2 - Analisi batch (tutte le email insieme)")
    print("  3 - Entrambi")
    print("=" * 80)

    choice = input("\nScelta [1/2/3]: ").strip()

    if choice == "1":
        test_individual_analysis(llm, emails)
    elif choice == "2":
        test_batch_analysis(llm, emails)
    elif choice == "3":
        test_individual_analysis(llm, emails)
        test_batch_analysis(llm, emails)
    else:
        print("❌ Scelta non valida")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETATO")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
