#!/usr/bin/env python3
"""Test script for validating LLM email classification."""

from __future__ import annotations

import argparse
import json
import os
import sys

from src.config import Config
from src.llm_processor import LLMProcessor


def load_test_emails(filepath: str = "test_emails.json") -> list[dict]:
    """Load test emails from JSON file.

    Args:
        filepath: Path to the JSON file containing test emails.

    Returns:
        List of dicts with test email data.
    """
    # Fall back to src/ directory if not found in current directory
    if not os.path.exists(filepath):
        filepath = os.path.join("src", filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def format_email_content(email: dict) -> str:
    """Format email content for LLM analysis.

    Args:
        email: Dict with email data.

    Returns:
        Formatted string with email content.
    """
    return f"""Subject: {email["subject"]}
From: {email["from"]}
To: {email["to"]}

{email["content"]}"""


def print_separator(char: str = "=", length: int = 80) -> None:
    """Print a separator line."""
    print(char * length)


def print_analysis_result(email: dict, analysis) -> None:
    """Print analysis results in a readable format.

    Args:
        email: Dict with the original email data.
        analysis: EmailAnalysis object with results.
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
        print(f"✉️  NEEDS REPLY: {'Yes' if analysis.needs_reply else 'No'}")

        if analysis.needs_reply and analysis.draft_body:
            print("\n💬 BOZZA RISPOSTA SUGGERITA:")
            print_separator("-", 60)
            print(analysis.draft_body)
            print_separator("-", 60)
    else:
        print("\n❌ ERRORE: Analisi fallita")

    print()


def test_individual_analysis(llm: LLMProcessor, emails: list[dict]) -> None:
    """Test individual analysis of each email.

    Args:
        llm: LLMProcessor instance.
        emails: List of emails to analyse.
    """
    print("\n" + "=" * 80)
    print("🧪 TEST ANALISI INDIVIDUALE")
    print("=" * 80 + "\n")

    for email in emails:
        content = format_email_content(email)
        analysis = llm.analyze_thread(content)
        print_analysis_result(email, analysis)


def test_batch_analysis(llm: LLMProcessor, emails: list[dict]) -> None:
    """Test batch analysis of all emails.

    Args:
        llm: LLMProcessor instance.
        emails: List of emails to analyse.
    """
    print("\n" + "=" * 80)
    print("🧪 BATCH ANALYSIS TEST")
    print("=" * 80 + "\n")

    thread_contents = [(email["id"], format_email_content(email)) for email in emails]

    print("\n📦 Analysing " + str(len(thread_contents)) + " emails in batch...\n")

    results = llm.analyze_threads_batch(thread_contents)

    for (thread_id, analysis), email in zip(results, emails):
        print_analysis_result(email, analysis)


def test_connection(llm: LLMProcessor) -> bool:
    """Test the LLM model connection.

    Args:
        llm: LLMProcessor instance.

    Returns:
        True if the connection succeeded, False otherwise.
    """
    print("\n" + "=" * 80)
    print("🔌 TEST CONNESSIONE LLM")
    print("=" * 80 + "\n")

    test_email = {
        "id": "test_connection",
        "subject": "Connection test",
        "from": "test@example.com",
        "to": "stefano@chino.io",
        "content": "This is a test message to verify the LLM model connection.",
    }

    content = format_email_content(test_email)

    print("📤 Sending test message to the LLM model...")
    print(f"   Provider: {Config.LLM_PROVIDER}")
    print(f"   Model: {Config.LLM_MODEL}")
    if Config.LLM_PROVIDER == "ollama":
        print(f"   URL: {Config.OLLAMA_BASE_URL}")
    print()

    try:
        analysis = llm.analyze_thread(content)
        if analysis:
            print("✅ CONNECTION SUCCESSFUL!\n")
            print(f"🏷️  Classification: {analysis.classification}")
            print(f"🔥 Urgency: {analysis.urgency}/5")
            print(f"📝 Analysis: {analysis.analysis}")
            print("\n" + "=" * 80)
            print("✅ LLM model is reachable and working")
            print("=" * 80 + "\n")
            return True
        else:
            print("❌ CONNECTION FAILED: No response from model")
            return False
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")
        print("\n" + "=" * 80)
        print("💡 TIPS:")
        if Config.LLM_PROVIDER == "ollama":
            print("   - Check that Ollama is running: ollama serve")
            print(
                f"   - Check that model '{Config.LLM_MODEL}' is installed: ollama list"
            )
            print(f"   - If not installed, run: ollama pull {Config.LLM_MODEL}")
            print(f"   - Check the URL: {Config.OLLAMA_BASE_URL}")
        elif Config.LLM_PROVIDER == "gemini":
            print("   - Check that GEMINI_API_KEY is set correctly")
            print("   - Check your internet connection")
        print("=" * 80 + "\n")
        return False


def main() -> None:
    """Funzione principale del test."""
    # Parse argomenti
    parser = argparse.ArgumentParser(
        description="Test script for LLM email classification"
    )
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Run only the LLM connection test",
    )
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("🚀 JANUS LLM TEST - Email Classification")
    print("=" * 80)

    try:
        Config.validate()
    except Exception as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nMake sure the .env file is set up correctly.")
        sys.exit(1)

    print("\n⚙️  LLM CONFIGURATION:")
    print(f"   Provider: {Config.LLM_PROVIDER}")
    print(f"   Model: {Config.LLM_MODEL}")
    print(f"   Temperature: {Config.LLM_TEMPERATURE}")
    if Config.LLM_PROVIDER == "ollama":
        print(f"   Ollama URL: {Config.OLLAMA_BASE_URL}")

    print("\n🤖 Initialising LLM processor...")
    try:
        llm = LLMProcessor()
        print("✅ LLM processor initialised successfully")
    except Exception as e:
        print(f"❌ LLM initialisation error: {e}")
        sys.exit(1)

    if args.test_connection:
        success = test_connection(llm)
        sys.exit(0 if success else 1)

    try:
        emails = load_test_emails()
        print(f"\n✅ Loaded {len(emails)} test emails")
    except FileNotFoundError:
        print("\n❌ test_emails.json not found!")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("Choose test type:")
    print("  1 - Individual analysis (one email at a time)")
    print("  2 - Batch analysis (all emails together)")
    print("  3 - Both")
    print("=" * 80)

    choice = input("\nChoice [1/2/3]: ").strip()

    if choice == "1":
        test_individual_analysis(llm, emails)
    elif choice == "2":
        test_batch_analysis(llm, emails)
    elif choice == "3":
        test_individual_analysis(llm, emails)
        test_batch_analysis(llm, emails)
    else:
        print("❌ Invalid choice")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
