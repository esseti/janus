from __future__ import annotations

import os
from typing import Optional, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from .config import Config
from .llm_factory import create_llm


class EmailAnalysis(BaseModel):
    """Structured output for email thread analysis."""

    classification: str = Field(
        description="The category of the email thread "
        "(e.g., Urgent, Support, Information, Inquiry)"
    )
    urgency: int = Field(description="Urgency level from 1 (low) to 5 (high)")
    analysis: str = Field(
        description="Brief justification for the classification and importance. In italian, ALWAYS"
    )
    needs_reply: bool = Field(
        description="Whether a reply draft is suggested. IMPORTANT: Set to True "
        "ONLY if the email explicitly requires an action or response from Stefano "
        "personally (not from stefano@chino.io or the company). Check the last "
        "message content and context to determine if Stefano needs to take action."
    )
    draft_body: Optional[str] = Field(
        default=None,
        description="Suggested draft reply if needs_reply is True, else None. In the language of the thread, ALWAYS",
    )


class BatchEmailAnalysis(BaseModel):
    """Structured output for batch email analysis."""

    analyses: List[EmailAnalysis] = Field(
        description="List of email analyses, one for each email in the batch"
    )


class LLMProcessor:
    """Processor for analyzing email threads using configurable LLM provider."""

    def __init__(self) -> None:
        """Initialize the LLM processor with configured provider and model."""
        self.llm = create_llm()
        self.structured_llm = self.llm.with_structured_output(EmailAnalysis)
        self.batch_structured_llm = self.llm.with_structured_output(BatchEmailAnalysis)
        self.custom_rules = self._load_custom_rules()

    def _load_custom_rules(self) -> str:
        """Load custom evaluation rules from file.

        Returns:
            Custom rules as string, or empty string if file doesn't exist.
        """
        if os.path.exists(Config.RULES_FILE):
            try:
                with open(Config.RULES_FILE, "r") as f:
                    return f.read()
            except Exception:
                return ""
        return ""

    def analyze_threads_batch(
        self, thread_contents: List[tuple[str, str]]
    ) -> List[tuple[str, EmailAnalysis | None]]:
        """Analyze multiple email threads in a single LLM call.

        Args:
            thread_contents: List of (thread_id, content) tuples.

        Returns:
            List of (thread_id, EmailAnalysis) tuples.
        """
        if not thread_contents:
            return []

        # Build system prompt with custom rules if available
        system_prompt = (
            "You are an expert executive assistant for Stefano. "
            "Analyze each email thread to determine its classification, "
            "urgency, and if it requires a reply draft. "
            "\n\nIMPORTANT for needs_reply and draft_body:"
            "\n- Set needs_reply=True ONLY if the email explicitly requires "
            "an action or response from Stefano PERSONALLY."
            "\n- Check the last message content and context carefully."
            "\n- If the email is addressed to stefano@chino.io or the company, "
            "it likely does NOT need a personal reply from Stefano."
            "\n- If the email is informational, automated, or a newsletter, "
            "set needs_reply=False."
            "\n- Only create a draft if Stefano needs to take personal action."
            "\n\nBe concise and professional."
        )

        if self.custom_rules:
            system_prompt += (
                "\n\nIMPORTANT: Follow these custom evaluation rules "
                "based on user feedback:\n\n"
                f"{self.custom_rules}"
            )

        # Format batch content
        batch_content = "\n\n".join(
            [
                f"EMAIL {i + 1}:\n{content}"
                for i, (_, content) in enumerate(thread_contents)
            ]
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                (
                    "human",
                    "Analyze these {count} emails and provide analysis "
                    "for each one in order:\n\n{content}",
                ),
            ]
        )

        chain = prompt | self.batch_structured_llm
        try:
            result = chain.invoke(
                {"count": len(thread_contents), "content": batch_content}
            )
            # Pair thread_ids with analyses
            results = []
            for i, (thread_id, _) in enumerate(thread_contents):
                if i < len(result.analyses):
                    results.append((thread_id, result.analyses[i]))
                else:
                    results.append((thread_id, None))
            return results
        except Exception as e:
            print(f"❌ Errore batch LLM analysis: {e}")
            # Fallback to individual analysis
            print("   Fallback ad analisi individuale...")
            return [
                (tid, self.analyze_thread(content)) for tid, content in thread_contents
            ]

    def analyze_thread(self, thread_content: str) -> EmailAnalysis | None:
        """Analyze email thread and return structured classification.

        Args:
            thread_content: The email thread content to analyze.

        Returns:
            EmailAnalysis object with classification, urgency, and draft,
            or None if analysis fails.
        """
        # Build system prompt with custom rules if available
        system_prompt = (
            "You are an expert executive assistant for Stefano. "
            "Analyze the email thread to determine its classification, "
            "urgency, and if it requires a reply draft. "
            "\n\nIMPORTANT for needs_reply and draft_body:"
            "\n- Set needs_reply=True ONLY if the email explicitly requires "
            "an action or response from Stefano PERSONALLY."
            "\n- Check the last message content and context carefully."
            "\n- If the email is addressed to stefano@chino.io or the company, "
            "it likely does NOT need a personal reply from Stefano."
            "\n- If the email is informational, automated, or a newsletter, "
            "set needs_reply=False."
            "\n- Only create a draft if Stefano needs to take personal action."
            "\n\nBe concise and professional."
        )

        if self.custom_rules:
            system_prompt += (
                "\n\nIMPORTANT: Follow these custom evaluation rules "
                "based on user feedback:\n\n"
                f"{self.custom_rules}"
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{content}"),
            ]
        )

        chain = prompt | self.structured_llm
        try:
            result = chain.invoke({"content": thread_content})
            return result
        except Exception as e:
            print(f"Error during LLM analysis: {e}")
            return None
