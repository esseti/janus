from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration for Janus email processor."""

    # Base directory for all runtime data files (secrets, state, logs).
    # Set JANUS_DATA_DIR env var when running in Docker with a mounted volume.
    DATA_DIR = Path(os.getenv("JANUS_DATA_DIR", "."))

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3-flash-preview")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    GOOGLE_CHAT_WEBHOOK = os.getenv("GOOGLE_CHAT_WEBHOOK")
    USER_EMAIL = os.getenv("USER_EMAIL")
    USER_NAME = os.getenv("USER_NAME", "")
    TARGET_LABEL = os.getenv("TARGET_LABEL", "janus")
    POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "600"))
    CREDENTIALS_FILE = DATA_DIR / "credentials.json"
    TOKEN_FILE = DATA_DIR / "token.json"
    LAST_RUN_FILE = DATA_DIR / "last_run.txt"
    PROCESSED_LOG_FILE = DATA_DIR / "processed_not_notified.json"
    NOTIFIED_LOG_FILE = DATA_DIR / "processed_notified.json"
    FEEDBACK_FILE = DATA_DIR / "feedback.json"
    RULES_FILE = DATA_DIR / "evaluation_rules.txt"
    MAILING_LIST_LOG_FILE = DATA_DIR / "mailing_list.json"
    EXCLUDED_SENDERS_FILE = DATA_DIR / "excluded_senders.txt"
    KEEP_SENDERS_FILE = DATA_DIR / "keep_senders.txt"

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration values.

        Raises:
            ValueError: If required config values are missing.
            FileNotFoundError: If credentials file not found.
        """
        if cls.LLM_PROVIDER == "gemini" and not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing in .env")
        if not cls.GOOGLE_CHAT_WEBHOOK:
            raise ValueError("GOOGLE_CHAT_WEBHOOK is missing in .env")
        if not cls.USER_EMAIL:
            raise ValueError("USER_EMAIL is missing in .env")
        if not os.path.exists(cls.CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"{cls.CREDENTIALS_FILE} not found in root directory"
            )
