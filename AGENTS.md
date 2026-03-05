# Janus Agent Guidelines

This document provides instructions and standards for AI agents working in the Janus repository.

## 1. Project Overview
Janus is an intelligent assistant that monitors Gmail emails (labeled `janus`), analyzes them using Google Gemini (via LangChain), and sends notifications to Google Chat. It also handles draft creation and automated archiving based on urgency.

The system is designed to be run as a cron job or a background process, ensuring Stefano stays informed about important communications without having to constantly check his inbox.

## 2. Environment & Commands

### Setup
The project uses **uv** for dependency management. Ensure you have `uv` installed on your system.
```bash
uv sync
```

### Execution
Run the main orchestrator:
```bash
uv run python -m src.main
```

Preview message templates with dummy data:
```bash
uv run python -m src.preview
```

### Linting & Formatting
No explicit linter is configured, but code MUST follow PEP 8 and use type hints.
*   **Formatting:** Follow standard `black` formatting.
*   **Type Checking:** Use `mypy` if available. Ensure manual compliance with Python 3.10+ typing.
*   **LSP Support:** The project is compatible with Pyright/Pylance.

### Testing
No test suite currently exists. When adding tests, use **pytest**:
*   **Run all tests:** `uv run pytest`
*   **Run single test:** `uv run pytest tests/test_file.py::test_function`
*   **Mocking:** Use `unittest.mock` or `pytest-mock` to mock Gmail and Gemini API calls.

## 3. Code Style Guidelines

### Python Version & Typing
- **Target:** Python 3.10+
- **Typing:** Use extensive type hinting for all function arguments and return types.
- **Future Annotations:** Always include `from __future__ import annotations` at the top of every file to support modern type hinting syntax.
- **Classes:** Use Pydantic `BaseModel` for all structured data, especially for LLM outputs and internal data transfer objects.

### Naming Conventions
- **Files/Modules:** `snake_case.py`
- **Functions/Variables:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE` (typically defined in `src/config.py`)
- **Private Members:** Use a single leading underscore `_prefix` for internal helper functions or class members.

### Imports
Group imports in the following order, separated by a blank line:
1.  Standard library imports (e.g., `os`, `sys`, `json`).
2.  Third-party library imports (e.g., `langchain`, `pydantic`, `googleapiclient`).
3.  Local module imports (relative imports like `from .config import Config`).

### Documentation
- Use **Google-style docstrings** for all functions and classes.
- Docstrings should include `Args:`, `Returns:`, and `Raises:` sections where applicable.
- Explain *why* something is done, especially for complex logic in `llm_processor.py` or `gmail_client.py`.

### Error Handling
- Use `try...except` blocks for all external API calls (Gmail, Gemini, Google Chat).
- Provide informative log messages. Use `print` for console output, but consider moving to a structured logger for persistent logs.
- Validate configuration at startup using `Config.validate()` to catch environment issues early.

### Configuration
- All configurations must be managed via `src/config.py`.
- Use `.env` for secrets (API keys, webhooks) and environment-specific settings.
- Never hardcode API keys, file paths, or magic numbers outside of the `Config` class.

## 4. Architecture & Component Guidelines

### Gmail Client (`src/gmail_client.py`)
- Handles OAuth2 authentication and token management.
- Responsible for searching, fetching, and modifying emails (marking as read, archiving).
- When fetching threads, ensure the content is cleaned or truncated to fit LLM context limits if necessary.

### LLM Processor (`src/llm_processor.py`)
- **Model:** Currently using `gemini-3-flash-preview`.
- **Structured Output:** Always use Pydantic for structured LLM responses to ensure reliability.
- **Prompts:** Keep prompts concise and professional. They should explicitly mention Stefano as the user.
- **Batching:** Use batch processing for multiple threads to optimize API usage.

### Notifier (`src/notifier.py`)
- Sends reports to Google Chat.
- Prefer consolidated reports over individual notifications to avoid spamming the chat room.
- Uses **Jinja2 templates** located in `src/templates/` for message formatting.

## 5. Message Templates
Messages sent to Google Chat are managed via Jinja2 templates in `src/templates/`:
- `urgent_report.jinja`: Format for the consolidated urgent email report.
- `processed_report.jinja`: Format for the daily/periodic report of low-urgency emails.

**Template Features:**
- `format_stars(urgency)`: Helper function to display ★★★★☆ style ratings.
- Layouts are optimized for mobile readability (bulleted lists, emoji indicators).
- Links to Gmail use the `thread_id` to provide direct access.

## 6. Evaluation & Urgency Rules
The system uses custom rules generated from user feedback in `evaluation_rules.txt`. 
- **Urgency Scale:** 1 (low) to 5 (high).
- **Notification Threshold:** Notifications are sent only if urgency > 2.
- **Standard Rules:** 
    - Calendar notifications (Accepted/Declined) -> Urgency 1.
    - Newsletters/Marketing -> Urgency 1-2.
    - Explicit action requests to Stefano -> Urgency 3+.
- **User Feedback:** The `feedback.json` file stores user corrections, which are then used to update `evaluation_rules.txt`.

## 7. Deployment & Infrastructure
- **Docker:** No longer used. Deployment is done via `uv` on the target machine.
- **Cron:** Used for periodic execution. See `README_CRON.md` and `setup_cron.sh`.
- **Logs:** Logs are written to `janus_cron.log` and rotated via `logrotate.conf`.

## 8. Development Workflow
1.  Verify configuration in `.env` and `credentials.json`.
2.  Run `uv sync` to set up the environment.
3.  Implement changes in the `src/` directory.
4.  Verify logic manually or by adding temporary scripts/tests.
5.  Check for typing errors using `mypy` or an LSP-enabled editor.
6.  If modifying LLM logic, ensure the `EmailAnalysis` Pydantic model is updated accordingly.
