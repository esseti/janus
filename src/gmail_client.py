from __future__ import annotations

import base64
import os.path
from datetime import datetime, timedelta
from fnmatch import fnmatch
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import Config

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class GmailClient:
    """Client for Gmail API operations."""

    def __init__(self) -> None:
        """Initialize Gmail client with authentication."""
        self.creds = self._authenticate()
        self.service = build("gmail", "v1", credentials=self.creds)
        profile = self.service.users().getProfile(userId="me").execute()
        self.authenticated_email = profile.get("emailAddress", "")
        print(f"📧 Account Gmail autenticato: {self.authenticated_email}")
        self.excluded_senders = self._load_excluded_senders()
        self.keep_senders = self._load_keep_senders()

    def _load_excluded_senders(self) -> list[str]:
        """Load excluded sender patterns from configuration file.

        Returns:
            List of email patterns to exclude (lowercase).
        """
        excluded_file = Config.EXCLUDED_SENDERS_FILE
        if not excluded_file.exists():
            return []

        excluded = []
        try:
            with open(excluded_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        excluded.append(line.lower())

            if excluded:
                print(f"📋 Caricati {len(excluded)} pattern di mittenti esclusi")
            return excluded
        except Exception as e:
            print(f"⚠️ Errore caricamento excluded_senders.txt: {e}")
            return []

    def _load_keep_senders(self) -> list[str]:
        """Load keep sender patterns from configuration file.

        These senders will always be processed, even if they match excluded_senders.

        Returns:
            List of email patterns to always keep (lowercase).
        """
        keep_file = Config.KEEP_SENDERS_FILE
        if not keep_file.exists():
            return []

        keep = []
        try:
            with open(keep_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        keep.append(line.lower())

            if keep:
                print(f"📋 Caricati {len(keep)} pattern di mittenti da mantenere")
            return keep
        except Exception as e:
            print(f"⚠️ Errore caricamento keep_senders.txt: {e}")
            return []

    def _is_excluded_sender(self, from_header: str) -> bool:
        """Check if sender matches any excluded pattern.

        First checks if sender is in keep_senders (priority override).
        Then checks if sender matches excluded_senders patterns.

        Supports glob-style patterns with * and ? wildcards:
        - * matches any sequence of characters
        - ? matches any single character
        - Exact substring match if no wildcards present

        Args:
            from_header: The From header value.

        Returns:
            True if sender should be excluded, False otherwise.
        """
        from_lower = from_header.lower()

        # Check keep_senders first (priority override)
        if self.keep_senders:
            for pattern in self.keep_senders:
                if "*" in pattern or "?" in pattern:
                    if fnmatch(from_lower, pattern):
                        return False  # Keep this sender
                else:
                    if pattern in from_lower:
                        return False  # Keep this sender

        # Check excluded_senders
        if not self.excluded_senders:
            return False

        for pattern in self.excluded_senders:
            # Check if pattern contains wildcards
            if "*" in pattern or "?" in pattern:
                # Use glob-style matching
                if fnmatch(from_lower, pattern):
                    return True
            else:
                # Use substring matching for backward compatibility
                if pattern in from_lower:
                    return True

        return False

    def add_to_excluded_senders(self, from_header: str) -> bool:
        """Add sender email to excluded_senders.txt if not already present.

        Extracts email address from From header and adds it to the exclusion list.

        Args:
            from_header: The From header value (e.g., "Name <email@domain.com>").

        Returns:
            True if sender was added, False if already present or error.
        """
        import re

        # Extract email address from header (e.g., "Name <email@domain.com>" -> "email@domain.com")
        email_match = re.search(r"<([^>]+)>", from_header)
        if email_match:
            email = email_match.group(1).strip().lower()
        else:
            # If no angle brackets, assume the whole string is the email
            email = from_header.strip().lower()

        # Check if already excluded
        if self._is_excluded_sender(email):
            return False

        # Add to file
        excluded_file = Config.EXCLUDED_SENDERS_FILE
        try:
            with open(excluded_file, "a", encoding="utf-8") as f:
                f.write(f"{email}\n")

            # Update in-memory list
            self.excluded_senders.append(email)
            print(f"  ➕ Aggiunto a excluded_senders.txt: {email}")
            return True
        except Exception as e:
            print(f"  ⚠️ Errore aggiunta a excluded_senders.txt: {e}")
            return False

    def _get_last_run_timestamp(self) -> str | None:
        """Get timestamp of last run from file.

        Returns:
            ISO format timestamp string or None if file doesn't exist.
        """
        if os.path.exists(Config.LAST_RUN_FILE):
            with open(Config.LAST_RUN_FILE, "r") as f:
                return f.read().strip()
        return None

    def _save_last_run_timestamp(self) -> None:
        """Save current timestamp to file."""
        timestamp = datetime.now().isoformat()
        with open(Config.LAST_RUN_FILE, "w") as f:
            f.write(timestamp)

    def _authenticate(self):
        creds = None
        if os.path.exists(Config.TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(Config.TOKEN_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    Config.CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(Config.TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        return creds

    def sync_labels_last_day(self, target_label: str) -> None:
        """Ensure all messages in janus threads from last day have correct label.

        Verifies that all messages in threads with the target label from the
        last 24 hours have the label applied. Adds the label to messages that
        are missing it.

        Args:
            target_label: The label to verify and apply (e.g., 'janus').
        """
        try:
            # Get label ID
            label_id = self._get_or_create_label(target_label)

            # Search for threads with target label from last day
            yesterday = datetime.now() - timedelta(days=1)
            date_str = yesterday.strftime("%Y/%m/%d")
            query = f"label:{target_label} after:{date_str}"

            print(
                f"🔄 Sincronizzazione label '{target_label}' "
                f"per messaggi dopo {date_str}..."
            )

            results = (
                self.service.users().threads().list(userId="me", q=query).execute()
            )
            threads = results.get("threads", [])

            if not threads:
                print("✅ Nessun thread da sincronizzare")
                return

            print(f"📦 Trovati {len(threads)} thread da verificare")
            messages_fixed = 0

            for thread_info in threads:
                thread_id = thread_info["id"]
                thread = (
                    self.service.users()
                    .threads()
                    .get(userId="me", id=thread_id)
                    .execute()
                )

                for msg in thread.get("messages", []):
                    msg_labels = msg.get("labelIds", [])

                    # Check if label is missing
                    if label_id not in msg_labels:
                        print(
                            f"  ⚠️ Label mancante su messaggio "
                            f"{msg['id'][:8]}... in thread {thread_id[:8]}..."
                        )

                        # Add the label
                        self.service.users().messages().modify(
                            userId="me", id=msg["id"], body={"addLabelIds": [label_id]}
                        ).execute()
                        messages_fixed += 1
                        print(f"  ✅ Label aggiunto")

            if messages_fixed > 0:
                print(
                    f"✅ Sync complete: "
                    f"{messages_fixed} messages fixed"
                )
            else:
                print("✅ All messages already have the correct label")

        except HttpError as error:
            print(f"❌ Error syncing labels: {error}")

    def get_unread_messages_since_last_run(self, target_label: str) -> list[dict]:
        """Get unread messages since last run or last 2 days.

        Args:
            target_label: The label to filter messages (not used in query).

        Returns:
            List of message objects with id and threadId, filtered by timestamp.
        """
        try:
            last_run = self._get_last_run_timestamp()
            last_run_dt = None

            if last_run:
                # Subtract 2 minutes safety margin to avoid missing emails arriving during execution
                last_run_dt = datetime.fromisoformat(last_run) - timedelta(minutes=2)
                # If last run was between yesterday and today, search from yesterday
                yesterday = datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=1)

                if last_run_dt >= yesterday:
                    search_from = yesterday
                    print(
                        f"🔍 Ultima esecuzione recente "
                        f"({last_run_dt.strftime('%Y-%m-%d %H:%M')})"
                    )
                    print(
                        f"🔍 Ricerca email non lette da ieri: "
                        f"{search_from.strftime('%Y/%m/%d')}"
                    )
                else:
                    search_from = last_run_dt
                    print(
                        f"🔍 Ricerca email non lette dall'ultima esecuzione: "
                        f"{search_from.strftime('%Y/%m/%d')}"
                    )
            else:
                # Fallback to last 2 days
                search_from = datetime.now() - timedelta(days=2)
                print(
                    f"🔍 Prima esecuzione: ricerca email non lette "
                    f"degli ultimi 2 giorni"
                )

            date_str = search_from.strftime("%Y/%m/%d")

            # Search for unread messages without janus label
            query = f"is:unread -label:{target_label} after:{date_str}"

            # Fetch all messages with pagination
            all_messages = []
            page_token = None

            while True:
                msg_results = (
                    self.service.users()
                    .messages()
                    .list(userId="me", q=query, pageToken=page_token)
                    .execute()
                )

                messages = msg_results.get("messages", [])
                all_messages.extend(messages)

                page_token = msg_results.get("nextPageToken")
                if not page_token:
                    break

            print(f"📨 Trovati {len(all_messages)} messaggi non letti totali")

            # Filter programmatically by timestamp if last_run_dt exists
            if last_run_dt:
                filtered_messages = []
                discarded_count = 0

                for msg in all_messages:
                    msg_detail = (
                        self.service.users()
                        .messages()
                        .get(
                            userId="me",
                            id=msg["id"],
                            format="metadata",
                            metadataHeaders=["Date"],
                        )
                        .execute()
                    )

                    # Get internal date (milliseconds since epoch)
                    internal_date_ms = int(msg_detail.get("internalDate", 0))
                    msg_dt = datetime.fromtimestamp(internal_date_ms / 1000)

                    # Only include if message is newer than last run
                    if msg_dt > last_run_dt:
                        filtered_messages.append(msg)
                    else:
                        discarded_count += 1

                print(
                    f"📨 {len(filtered_messages)} messages newer "
                    f"than last run"
                )
                if discarded_count > 0:
                    print(
                        f"⏭️  {discarded_count} messages skipped "
                        f"(older than last run)"
                    )
                return filtered_messages

            return all_messages

        except HttpError as error:
            print(f"❌ Errore durante ricerca: {error}")
            return []

    def _is_noreply_sender(self, from_header: str) -> bool:
        """Check if sender is a no-reply or mailing list address.

        Args:
            from_header: The From header value.

        Returns:
            True if sender is no-reply/mailing list, False otherwise.
        """
        from_lower = from_header.lower()

        # Common no-reply patterns
        noreply_patterns = [
            "no-reply",
            "noreply",
            "no_reply",
            "donotreply",
            "do-not-reply",
            "notifications",
            "notification",
            "mailer-daemon",
            "postmaster",
            "bounce",
            "automated",
            "auto-reply",
            "autoreply",
        ]

        return any(pattern in from_lower for pattern in noreply_patterns)

    def is_user_recipient(self, message_id: str, user_email: str) -> tuple[bool, dict]:
        """Check if user email is in To or CC of the message.

        Args:
            message_id: The message ID to check.
            user_email: The user's email address.

        Returns:
            Tuple of (is_recipient, message_info) where message_info contains
            from, to, subject headers.
        """

        try:
            msg = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=["From", "To", "Cc", "Subject"],
                )
                .execute()
            )

            headers = msg.get("payload", {}).get("headers", [])
            from_header = next(
                (h["value"] for h in headers if h["name"].lower() == "from"), "N/A"
            )
            to_header = next(
                (h["value"] for h in headers if h["name"].lower() == "to"), ""
            )
            cc_header = next(
                (h["value"] for h in headers if h["name"].lower() == "cc"), ""
            )
            subject = next(
                (h["value"] for h in headers if h["name"].lower() == "subject"), "N/A"
            )

            message_info = {
                "from": from_header,
                "to": to_header,
                "cc": cc_header,
                "subject": subject,
            }

            user_email_lower = user_email.lower()
            is_recipient = (
                user_email_lower in to_header.lower()
                or user_email_lower in cc_header.lower()
            )

            return True, message_info

        except HttpError as error:
            print(f"❌ Errore verifica destinatario: {error}")
            return False, {}

    def is_valid_sender(self, message_id: str) -> bool:
        """Check if sender is not a no-reply, mailing list, or excluded.

        Args:
            message_id: The message ID to check.

        Returns:
            True if sender is valid (not no-reply or excluded), False otherwise.
        """
        try:
            msg = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=["From"],
                )
                .execute()
            )

            headers = msg.get("payload", {}).get("headers", [])
            from_header = next(
                (h["value"] for h in headers if h["name"].lower() == "from"), ""
            )

            if self._is_noreply_sender(from_header):
                return False

            if self._is_excluded_sender(from_header):
                return False

            return True

        except HttpError as error:
            print(f"❌ Errore verifica mittente: {error}")
            return True  # In case of error, don't filter out

    def send_email(self, to: str, subject: str, body_text: str) -> bool:
        """Sends an email using the Gmail API.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body_text: Email body content (plain text).

        Returns:
            True if sent successfully, False otherwise.
        """
        from email.message import EmailMessage

        message = EmailMessage()
        message.set_content(body_text)
        message["To"] = self.authenticated_email
        message["From"] = self.authenticated_email
        message["Subject"] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"raw": encoded_message}

        try:
            self.service.users().messages().send(
                userId="me", body=create_message
            ).execute()
            print(f"✅ Email inviata a {to}")
            return True
        except HttpError as error:
            print(f"❌ Errore invio email: {error}")
            return False

    def get_thread_details(self, thread_id):
        """Fetches full thread content and formats it for the LLM."""
        try:
            thread = (
                self.service.users().threads().get(userId="me", id=thread_id).execute()
            )
            messages = []
            subject = ""
            from_addr = ""
            all_recipients = set()

            for msg in thread.get("messages", []):
                headers = msg.get("payload", {}).get("headers", [])
                msg_from = next(
                    (h["value"] for h in headers if h["name"] == "From"), "Unknown"
                )
                msg_to = next((h["value"] for h in headers if h["name"] == "To"), "")
                msg_cc = next((h["value"] for h in headers if h["name"] == "Cc"), "")
                msg_bcc = next((h["value"] for h in headers if h["name"] == "Bcc"), "")
                msg_date = next(
                    (h["value"] for h in headers if h["name"] == "Date"), "Unknown"
                )
                if not subject:
                    subject = next(
                        (h["value"] for h in headers if h["name"] == "Subject"),
                        "No Subject",
                    )
                if not from_addr:
                    from_addr = msg_from

                if msg_to:
                    all_recipients.update(addr.strip() for addr in msg_to.split(","))
                if msg_cc:
                    all_recipients.update(addr.strip() for addr in msg_cc.split(","))
                if msg_bcc:
                    all_recipients.update(addr.strip() for addr in msg_bcc.split(","))

                body = self._get_message_body(msg)
                messages.append(
                    f"From: {msg_from}\nDate: {msg_date}\nContent: {body}\n"
                )

            full_content = "\n---\n".join(messages)
            last_message_id = thread["messages"][-1]["id"]
            to_addr = ", ".join(sorted(all_recipients)) if all_recipients else "Unknown"
            return {
                "subject": subject,
                "content": full_content,
                "last_message_id": last_message_id,
                "from": from_addr,
                "to": to_addr,
            }
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def _get_message_body(self, msg):
        """Extracts the plain text body from a message."""
        payload = msg.get("payload", {})
        parts = payload.get("parts", [])

        def extract_text(parts):
            for part in parts:
                if part["mimeType"] == "text/plain":
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
                if "parts" in part:
                    res = extract_text(part["parts"])
                    if res:
                        return res
            return ""

        body = extract_text(parts) if parts else ""
        if not body and "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        return body if body else msg.get("snippet", "")

    def create_draft(self, thread_id, last_message_id, body):
        """Creates a draft reply to the specified thread."""
        try:
            # Get original message to extract headers for proper threading
            original_msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=last_message_id)
                .execute()
            )
            headers = original_msg.get("payload", {}).get("headers", [])

            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            msg_to = next((h["value"] for h in headers if h["name"] == "From"), "")
            msg_id = next(
                (h["value"] for h in headers if h["name"] == "Message-ID"), ""
            )

            # Format the draft message
            # Note: Threading requires In-Reply-To and References headers
            draft_content = (
                f"To: {msg_to}\n"
                f"Subject: Re: {subject}\n"
                f"In-Reply-To: {msg_id}\n"
                f"References: {msg_id}\n\n"
                f"{body}"
            )

            raw_message = base64.urlsafe_b64encode(
                draft_content.encode("utf-8")
            ).decode("utf-8")
            draft_body = {"message": {"threadId": thread_id, "raw": raw_message}}

            self.service.users().drafts().create(userId="me", body=draft_body).execute()
            return True
        except HttpError as error:
            print(f"An error occurred creating draft: {error}")
            return False

    def get_feedback_labeled_threads(self) -> list[dict]:
        """Return threads the user has labeled with janus/urgent or janus/not-urgent.

        Returns:
            List of dicts with keys: thread_id, feedback_type ('urgent'|'not-urgent'),
            subject, from_addr.
        """
        results = []
        for label_name, feedback_type in [
            ("janus/urgent", "urgent"),
            ("janus/not-urgent", "not-urgent"),
        ]:
            try:
                label_id = self._get_or_create_label(label_name)
                response = (
                    self.service.users()
                    .threads()
                    .list(userId="me", labelIds=[label_id])
                    .execute()
                )
                for thread in response.get("threads", []):
                    thread_id = thread["id"]
                    try:
                        details = (
                            self.service.users()
                            .threads()
                            .get(
                                userId="me",
                                id=thread_id,
                                format="metadata",
                                metadataHeaders=["Subject", "From"],
                            )
                            .execute()
                        )
                        first_msg = details["messages"][0]
                        headers = first_msg.get("payload", {}).get("headers", [])
                        subject = next(
                            (h["value"] for h in headers if h["name"].lower() == "subject"),
                            "N/A",
                        )
                        from_addr = next(
                            (h["value"] for h in headers if h["name"].lower() == "from"),
                            "N/A",
                        )
                        results.append(
                            {
                                "thread_id": thread_id,
                                "feedback_type": feedback_type,
                                "label_id": label_id,
                                "subject": subject,
                                "from_addr": from_addr,
                            }
                        )
                    except HttpError:
                        pass
            except HttpError as e:
                print(f"⚠️ Errore lettura label {label_name}: {e}")
        return results

    def remove_label_from_thread(self, thread_id: str, label_id: str) -> None:
        """Remove a label from all messages in a thread.

        Args:
            thread_id: The thread ID.
            label_id: The label ID to remove.
        """
        try:
            self.service.users().threads().modify(
                userId="me",
                id=thread_id,
                body={"removeLabelIds": [label_id]},
            ).execute()
        except HttpError as e:
            print(f"⚠️ Errore rimozione label da thread {thread_id[:8]}...: {e}")

    def mark_as_read(self, thread_id: str, target_label: str) -> bool:
        """Mark thread as read and add target label.

        Args:
            thread_id: The thread ID to mark as read.
            target_label: The label to add (e.g., 'janus').

        Returns:
            True if successful, False otherwise.
        """
        try:
            label_id = self._get_or_create_label(target_label)
            body = {
                "addLabelIds": [label_id],
                "removeLabelIds": ["UNREAD"],
            }

            self.service.users().threads().modify(
                userId="me",
                id=thread_id,
                body=body,
            ).execute()
            return True
        except HttpError as error:
            print(f"❌ Errore marcatura come letto: {error}")
            return False

    def archive_thread(self, thread_id: str) -> bool:
        """Archive a thread by removing it from INBOX.

        Args:
            thread_id: The thread ID to archive.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.service.users().threads().modify(
                userId="me",
                id=thread_id,
                body={"removeLabelIds": ["INBOX"]},
            ).execute()
            return True
        except HttpError as error:
            print(f"❌ Errore archiviazione: {error}")
            return False

    def _get_or_create_label(self, label_name):
        labels = (
            self.service.users().labels().list(userId="me").execute().get("labels", [])
        )
        for label in labels:
            if label["name"].lower() == label_name.lower():
                return label["id"]

        # Create label if not found
        new_label = {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        created = (
            self.service.users().labels().create(userId="me", body=new_label).execute()
        )
        return created["id"]
