#!/usr/bin/env python3
"""
Gmail to Apple Reminders Sync - Thread-aware email import.

Features:
- Fetches starred/flagged emails from Gmail API
- Groups emails by thread, imports only the latest per thread
- Tracks imported threads to prevent duplicates
- Creates reminders in Apple Reminders "Email Follow-up" list

Deduplication strategy:
1. Thread-based: Only the most recent email in each starred thread is imported
2. State tracking: Imported thread IDs are stored to prevent re-importing
3. Gmail message IDs in reminder notes enable duplicate detection
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

# Gmail API imports - will gracefully fail if not available
# Type stubs may not be available, so we use Any for dynamic imports
from typing import Any

Credentials: Any = None
Request: Any = None
InstalledAppFlow: Any = None
build: Any = None
GMAIL_AVAILABLE = False

try:
    from google.oauth2.credentials import Credentials  # type: ignore[no-redef]
    from google.auth.transport.requests import Request  # type: ignore[no-redef]
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[no-redef,import-untyped]
    from googleapiclient.discovery import build  # type: ignore[no-redef]

    GMAIL_AVAILABLE = True
except ImportError:
    pass  # Keep defaults (None/False)

# Gmail API scopes - include compose for drafts, modify for unstarring
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]

# Anthropic for AI draft generation (optional)
ANTHROPIC_AVAILABLE = False
ANTHROPIC_API_KEY: Optional[str] = None


def _load_anthropic_key() -> Optional[str]:
    """Load ANTHROPIC_API_KEY from environment or dotfiles-private."""
    # First check environment
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    # Try loading from dotfiles-private/jibot.env
    dotfiles_env = Path.home() / "dotfiles-private" / "jibot.env"
    if dotfiles_env.exists():
        try:
            with open(dotfiles_env) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        if key:
                            # Set in environment for anthropic client
                            os.environ["ANTHROPIC_API_KEY"] = key
                            return key
        except Exception:
            pass

    return None


try:
    import importlib.util

    if importlib.util.find_spec("anthropic") is not None:
        ANTHROPIC_API_KEY = _load_anthropic_key()
        ANTHROPIC_AVAILABLE = bool(ANTHROPIC_API_KEY)
except Exception:
    pass

# Default paths - use hydrated Google credentials from age-encrypted secrets
DEFAULT_CREDENTIALS_PATH = (
    Path.home() / ".cache" / "amplifier" / "google-hydrated" / "credentials.json"
)
DEFAULT_TOKEN_PATH = (
    Path.home() / ".cache" / "amplifier" / "google-hydrated" / "gmail_token.json"
)
DEFAULT_STATE_PATH = Path.home() / "switchboard" / "reminders" / "email_sync_state.json"
DEFAULT_LIST_NAME = "Email Replies"


class EmailSyncState:
    """Track which email threads have been imported to prevent duplicates."""

    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = Path(state_path or DEFAULT_STATE_PATH)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        """Load state from disk."""
        if self.state_path.exists():
            with open(self.state_path) as f:
                data = json.load(f)
                self.imported_threads = set(data.get("imported_threads", []))
                self.imported_messages = set(data.get("imported_messages", []))
                self.last_sync = data.get("last_sync")
        else:
            self.imported_threads = set()
            self.imported_messages = set()
            self.last_sync = None

    def _save(self):
        """Save state to disk."""
        with open(self.state_path, "w") as f:
            json.dump(
                {
                    "imported_threads": list(self.imported_threads),
                    "imported_messages": list(self.imported_messages),
                    "last_sync": self.last_sync,
                    "updated_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def is_thread_imported(self, thread_id: str) -> bool:
        """Check if a thread has already been imported."""
        return thread_id in self.imported_threads

    def is_message_imported(self, message_id: str) -> bool:
        """Check if a specific message has been imported."""
        return message_id in self.imported_messages

    def mark_imported(self, thread_id: str, message_id: str):
        """Mark a thread/message as imported."""
        self.imported_threads.add(thread_id)
        self.imported_messages.add(message_id)

    def update_last_sync(self):
        """Update last sync timestamp and save."""
        self.last_sync = datetime.now().isoformat()
        self._save()

    def get_stats(self) -> dict:
        """Get sync state statistics."""
        return {
            "imported_threads": len(self.imported_threads),
            "imported_messages": len(self.imported_messages),
            "last_sync": self.last_sync,
            "state_path": str(self.state_path),
        }


def get_gmail_service(
    credentials_path: Optional[Path] = None, token_path: Optional[Path] = None
):
    """Get authenticated Gmail API service."""
    if not GMAIL_AVAILABLE:
        raise RuntimeError(
            "Gmail API not available. Install with: "
            "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
        )

    credentials_path = Path(credentials_path or DEFAULT_CREDENTIALS_PATH)
    token_path = Path(token_path or DEFAULT_TOKEN_PATH)

    creds = None

    # Load existing token
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise RuntimeError(
                    f"Gmail credentials not found at {credentials_path}. "
                    "Download OAuth credentials from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def fetch_starred_emails(service, max_results: int = 100) -> list[dict]:
    """
    Fetch starred emails from Gmail.

    Returns list of emails with thread_id, message_id, date, sender, subject, preview.
    """
    # Search for starred emails
    results = (
        service.users()
        .messages()
        .list(userId="me", q="is:starred", maxResults=max_results)
        .execute()
    )

    messages = results.get("messages", [])
    emails = []

    for msg_ref in messages:
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=msg_ref["id"],
                format="metadata",
                metadataHeaders=["From", "To", "Cc", "Reply-To", "Subject", "Date"],
            )
            .execute()
        )

        headers = {
            h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])
        }

        # Parse sender
        from_header = headers.get("From", "")
        # Extract name from "Name <email>" format
        match = re.match(r"^([^<]+)\s*<", from_header)
        sender_name = (
            match.group(1).strip().strip('"') if match else from_header.split("@")[0]
        )
        sender_email = re.search(r"<([^>]+)>", from_header)
        sender_email = sender_email.group(1) if sender_email else from_header

        # Get snippet as preview
        snippet = msg.get("snippet", "")[:200]

        # Parse date for sorting
        date_str = headers.get("Date", "")
        internal_date = int(msg.get("internalDate", 0))

        emails.append(
            {
                "message_id": msg["id"],
                "thread_id": msg["threadId"],
                "sender_name": sender_name,
                "sender_email": sender_email,
                "to": headers.get("To", ""),
                "cc": headers.get("Cc", ""),
                "reply_to": headers.get("Reply-To", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "preview": snippet,
                "date": date_str,
                "internal_date": internal_date,  # For sorting (epoch ms)
            }
        )

    return emails


def group_by_thread(emails: list[dict]) -> dict[str, list[dict]]:
    """Group emails by thread ID."""
    threads = {}
    for email in emails:
        tid = email["thread_id"]
        if tid not in threads:
            threads[tid] = []
        threads[tid].append(email)
    return threads


def get_latest_per_thread(emails: list[dict]) -> list[dict]:
    """
    Get only the latest (most recent) email from each thread.

    This prevents duplicates when multiple emails in a thread are starred.
    """
    threads = group_by_thread(emails)
    latest = []

    for thread_id, thread_emails in threads.items():
        # Sort by internal_date descending, take the first (most recent)
        sorted_emails = sorted(
            thread_emails, key=lambda x: x["internal_date"], reverse=True
        )
        latest.append(sorted_emails[0])

    return latest


# ============================================================================
# Reply-All Helper
# ============================================================================

# User's email addresses to exclude from reply recipients
USER_EMAILS = {
    "joi@ito.com",
    "joi.ito@digital.go.jp",
    "joichi.ito@digital.go.jp",
    "joi@neoteny.com",
}


def parse_email_addresses(header: str) -> list[str]:
    """Extract email addresses from a header like 'Name <email>, Name2 <email2>'."""
    if not header:
        return []
    # Find all email addresses in angle brackets or bare emails
    emails = re.findall(r"<([^>]+)>", header)
    if not emails:
        # Try to find bare email addresses
        emails = re.findall(r"[\w\.-]+@[\w\.-]+", header)
    return [e.lower() for e in emails]


def get_thread_participants(
    thread_id: str,
    credentials_path: Optional[Path] = None,
    token_path: Optional[Path] = None,
    max_messages: int = 10,
) -> set[str]:
    """
    Get all participants from recent messages in a thread.

    Scans the last N messages to find all To/Cc/From addresses,
    which gives us the full participant list even if the most
    recent message dropped people from Cc.
    """
    service = get_gmail_service(credentials_path, token_path)

    thread = (
        service.users()
        .threads()
        .get(
            userId="me",
            id=thread_id,
            format="metadata",
            metadataHeaders=["From", "To", "Cc"],
        )
        .execute()
    )

    participants = set()
    messages = thread.get("messages", [])

    # Look at the last N messages
    for msg in messages[-max_messages:]:
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

        for header in ["From", "To", "Cc"]:
            for addr in parse_email_addresses(headers.get(header, "")):
                if addr.lower() not in USER_EMAILS:
                    participants.add(addr.lower())

    return participants


def build_reply_all_recipients(
    email: dict,
    thread_participants: Optional[set[str]] = None,
) -> tuple[str, str]:
    """
    Build reply-all recipients from an email.

    Returns (to, cc) where:
    - to: The sender (or Reply-To if present)
    - cc: All other recipients from the thread, minus user's own emails

    If thread_participants is provided, uses that for Cc instead of
    just the single email's headers (handles cases where someone
    dropped people from Cc in their reply).
    """
    # Determine the To recipient (use Reply-To if present, else sender)
    reply_to = email.get("reply_to", "")
    if reply_to:
        to_addr = parse_email_addresses(reply_to)
        to = to_addr[0] if to_addr else email["sender_email"]
    else:
        to = email["sender_email"]

    # Build Cc list from thread participants if available
    if thread_participants:
        cc_addresses = {
            addr
            for addr in thread_participants
            if addr.lower() != to.lower() and addr.lower() not in USER_EMAILS
        }
    else:
        # Fall back to single email headers
        cc_addresses = set()

        # Add original To recipients
        for addr in parse_email_addresses(email.get("to", "")):
            if addr.lower() not in USER_EMAILS and addr.lower() != to.lower():
                cc_addresses.add(addr)

        # Add original Cc recipients
        for addr in parse_email_addresses(email.get("cc", "")):
            if addr.lower() not in USER_EMAILS and addr.lower() != to.lower():
                cc_addresses.add(addr)

        # Also include the sender if Reply-To was different
        if reply_to and email["sender_email"].lower() not in USER_EMAILS:
            sender = email["sender_email"].lower()
            if sender != to.lower():
                cc_addresses.add(sender)

    cc = ", ".join(sorted(cc_addresses)) if cc_addresses else ""

    return to, cc


# ============================================================================
# Draft Generation Functions
# ============================================================================


def get_thread_messages(
    thread_id: str,
    credentials_path: Optional[Path] = None,
    token_path: Optional[Path] = None,
) -> list[dict]:
    """Get all messages in a thread, ordered by date (oldest first)."""
    service = get_gmail_service(credentials_path, token_path)

    thread = (
        service.users()
        .threads()
        .get(userId="me", id=thread_id, format="full")
        .execute()
    )

    messages = []
    for msg in thread.get("messages", []):
        headers = msg.get("payload", {}).get("headers", [])
        header_dict = {h["name"].lower(): h["value"] for h in headers}

        # Extract body
        body = extract_email_body(msg)

        # Parse date
        date_str = header_dict.get("date", "")

        # Parse from
        from_header = header_dict.get("from", "")
        from_match = re.match(r'"?([^"<]+)"?\s*<?([^>]*)>?', from_header)
        if from_match:
            from_name = from_match.group(1).strip()
            from_email = from_match.group(2).strip() or from_header
        else:
            from_name = from_header
            from_email = from_header

        messages.append(
            {
                "id": msg["id"],
                "thread_id": msg["threadId"],
                "from_name": from_name,
                "from_email": from_email,
                "subject": header_dict.get("subject", "(no subject)"),
                "date": date_str,
                "body": body,
            }
        )

    return messages


def extract_email_body(message: dict) -> str:
    """Extract plain text body from Gmail message."""
    import base64

    payload = message.get("payload", {})

    def get_body_from_part(part: dict) -> str:
        """Recursively extract text from message parts."""
        mime_type = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data", "")

        if mime_type == "text/plain" and data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        # Check nested parts
        for subpart in part.get("parts", []):
            result = get_body_from_part(subpart)
            if result:
                return result

        return ""

    # Try to get body from payload
    body = get_body_from_part(payload)

    # Fallback to snippet if no body found
    if not body:
        body = message.get("snippet", "")

    return body


def format_thread_for_context(messages: list[dict]) -> str:
    """Format thread messages for LLM context."""
    lines = []
    for i, msg in enumerate(messages):
        lines.append(f"--- Message {i + 1} ---")
        lines.append(f"From: {msg['from_name']} <{msg['from_email']}>")
        lines.append(f"Date: {msg['date']}")
        lines.append(f"Subject: {msg['subject']}")
        lines.append("")
        body = msg.get("body", "").strip()
        if len(body) > 3000:
            body = body[:3000] + "\n[... truncated ...]"
        lines.append(body)
        lines.append("")

    return "\n".join(lines)


def format_quoted_thread(messages: list[dict]) -> str:
    """Format thread as quoted text for inclusion in draft."""
    lines = []
    for msg in messages:
        lines.append("")
        lines.append(
            f"On {msg['date']}, {msg['from_name']} <{msg['from_email']}> wrote:"
        )
        lines.append("")
        body = msg.get("body", "").strip()
        for line in body.split("\n"):
            lines.append(f"> {line}")

    return "\n".join(lines)


def generate_draft_with_ai(
    email: dict,
    thread_messages: list[dict],
    owner_name: str = "Joi",
    timeout: float = 120.0,
) -> Optional[str]:
    """Generate a draft reply using Claude API.

    Args:
        email: The email to reply to
        thread_messages: All messages in the thread
        owner_name: Name to sign the email with
        timeout: API timeout in seconds (default 120s for long drafts)
    """
    if not ANTHROPIC_AVAILABLE:
        return None

    import anthropic  # type: ignore[import-not-found]
    import httpx

    # Create client with extended timeout for draft generation
    client = anthropic.Anthropic(
        timeout=httpx.Timeout(timeout, connect=30.0),
    )

    thread_context = format_thread_for_context(thread_messages)

    # Find the last message not from us to reply to
    latest_from_other = None
    for msg in reversed(thread_messages):
        if "joi" not in msg["from_email"].lower():
            latest_from_other = msg
            break

    if not latest_from_other:
        latest_from_other = email

    from_name = latest_from_other.get("from_name", "there")
    if from_name.startswith('"') and from_name.endswith('"'):
        from_name = from_name[1:-1]
    first_name = from_name.split()[0] if from_name else "there"

    prompt = f"""You are drafting an email reply for {owner_name}. Write a direct, efficient response based on the email thread below.

Guidelines:
- Be direct and to the point - no unnecessary pleasantries or filler
- Skip cheerful phrases like "I hope this finds you well", "Thank you for reaching out", "I'd be happy to"
- Get straight to the substance
- Short sentences, clear answers
- If something needs follow-up, say so plainly
- If declining, be polite but direct
- Sign off with just "{owner_name}" (no "Best," or "Thanks,")

Tone: Professional, efficient, respectful - but not warm or effusive. Think busy executive who values everyone's time.

Email thread (oldest to newest):
{thread_context}

Write ONLY the reply body text. Start with "Hi {first_name}," (or just "{first_name}," for familiar contacts) and end with just "{owner_name}". Keep it brief."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def create_gmail_draft(
    to: str,
    subject: str,
    body: str,
    thread_id: str,
    reply_to_id: str,
    cc: Optional[str] = None,
    credentials_path: Optional[Path] = None,
    token_path: Optional[Path] = None,
) -> dict:
    """Create a Gmail draft reply (reply-all style with Cc recipients)."""
    import base64
    from email.mime.text import MIMEText

    service = get_gmail_service(credentials_path, token_path)

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    if cc:
        message["cc"] = cc

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    draft_body = {
        "message": {
            "raw": raw,
            "threadId": thread_id,
        }
    }

    draft = service.users().drafts().create(userId="me", body=draft_body).execute()

    return {
        "draft_id": draft["id"],
        "message_id": draft["message"]["id"],
        "link": f"https://mail.google.com/mail/u/0/#drafts/{draft['message']['id']}",
    }


# ============================================================================
# Reminder Creation (via EventKit)
# ============================================================================


def create_email_reminder(
    sender_name: str,
    subject: str,
    sender_email: str,
    message_id: str,
    preview: str,
    list_name: str = DEFAULT_LIST_NAME,
    draft_link: Optional[str] = None,
) -> bool:
    """
    Create a reminder for an email in Apple Reminders using EventKit.

    Format matches existing Email Follow-up reminders:
    - Title: 📧 Sender: Subject
    - Notes: From: email\n\nDraft: draft_link\n\nGmail: gmail_url\n\nPreview: ...
    """
    # Import EventKit create_reminder
    try:
        from .eventkit_sync import create_reminder
    except ImportError:
        # Running as standalone script - add module dir to path
        import sys

        module_dir = Path(__file__).parent
        if str(module_dir) not in sys.path:
            sys.path.insert(0, str(module_dir))
        from eventkit_sync import create_reminder

    # Truncate subject if too long
    if len(subject) > 80:
        subject = subject[:77] + "..."

    title = f"📧 {sender_name}: {subject}"
    gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{message_id}"

    # Build notes with draft link if available
    notes_parts = [f"From: {sender_email}"]
    if draft_link:
        notes_parts.append(f"Draft: {draft_link}")
    notes_parts.append(f"Gmail: {gmail_link}")
    notes_parts.append(f"Preview: {preview[:200]}...")
    notes = "\n\n".join(notes_parts)

    try:
        result = create_reminder(title=title, list_name=list_name, notes=notes)
        if result.get("success"):
            return True
        else:
            print(f"   ❌ Failed to create reminder: {result.get('error', 'unknown')}")
            return False
    except Exception as e:
        print(f"   ❌ Failed to create reminder: {e}")
        return False


def check_existing_reminders(list_name: str = DEFAULT_LIST_NAME) -> set[str]:
    """
    Get message IDs of emails already in the reminder list.

    Parses the Link: field from reminder notes to extract Gmail message IDs.
    """
    # Handle both module and standalone script contexts
    try:
        from .reminders_sync import load_reminders_cache
    except ImportError:
        # Running as standalone script - load from cache file directly
        cache_path = Path.home() / "switchboard" / "reminders" / "reminders_cache.json"
        if cache_path.exists():
            with open(cache_path) as f:
                data = json.load(f)
                reminders = []
                for ln, items in data.get("byList", {}).items():
                    for r in items:
                        r["list"] = ln
                        reminders.append(r)
        else:
            reminders = []
        existing_ids = set()
        for r in reminders:
            if r.get("list") != list_name:
                continue
            notes = r.get("notes") or ""
            match = re.search(r"mail\.google\.com/mail/u/\d+/#inbox/([a-f0-9]+)", notes)
            if match:
                existing_ids.add(match.group(1))
        return existing_ids

    reminders = load_reminders_cache()
    existing_ids = set()

    for r in reminders:
        if r.get("list") != list_name:
            continue

        notes = r.get("notes") or ""
        # Extract message ID from Gmail link
        match = re.search(r"mail\.google\.com/mail/u/\d+/#inbox/([a-f0-9]+)", notes)
        if match:
            existing_ids.add(match.group(1))

    return existing_ids


def sync_emails_to_reminders(
    credentials_path: Optional[Path] = None,
    token_path: Optional[Path] = None,
    state_path: Optional[Path] = None,
    list_name: str = DEFAULT_LIST_NAME,
    max_emails: int = 100,
    dry_run: bool = False,
    create_drafts: bool = False,
) -> dict:
    """
    Sync starred Gmail emails to Apple Reminders.

    Args:
        credentials_path: Path to OAuth credentials.json
        token_path: Path to token.json (will be created)
        state_path: Path to sync state file
        list_name: Apple Reminders list to add to
        max_emails: Maximum emails to fetch from Gmail
        dry_run: If True, don't actually create reminders
        create_drafts: If True, generate AI draft replies and include links

    Returns:
        dict with sync results
    """
    result = {
        "success": False,
        "emails_fetched": 0,
        "threads_found": 0,
        "new_threads": 0,
        "reminders_created": 0,
        "drafts_created": 0,
        "skipped_existing": 0,
        "skipped_imported": 0,
        "errors": [],
    }

    # Check Gmail API availability
    if not GMAIL_AVAILABLE:
        result["error"] = "Gmail API not available"
        return result

    try:
        # Initialize state tracking
        state = EmailSyncState(state_path)

        # Get existing reminders to check for duplicates
        print("📧 Checking existing email reminders...")
        existing_in_reminders = check_existing_reminders(list_name)
        print(f"   Found {len(existing_in_reminders)} existing email reminders")

        # Connect to Gmail
        print("🔗 Connecting to Gmail...")
        service = get_gmail_service(credentials_path, token_path)

        # Fetch starred emails
        print(f"⭐ Fetching starred emails (max {max_emails})...")
        emails = fetch_starred_emails(service, max_emails)
        result["emails_fetched"] = len(emails)
        print(f"   Found {len(emails)} starred emails")

        if not emails:
            result["success"] = True
            result["message"] = "No starred emails to sync"
            state.update_last_sync()
            return result

        # Get only the latest email per thread
        print("🔄 Deduplicating by thread (keeping latest only)...")
        latest_emails = get_latest_per_thread(emails)
        result["threads_found"] = len(latest_emails)
        print(f"   {len(latest_emails)} unique threads")

        # Filter out already imported
        new_emails = []
        for email in latest_emails:
            msg_id = email["message_id"]
            thread_id = email["thread_id"]

            # Check if already in reminders (by message ID in notes)
            if msg_id in existing_in_reminders:
                result["skipped_existing"] += 1
                continue

            # Check if thread was previously imported (even if reminder was deleted)
            if state.is_thread_imported(thread_id):
                result["skipped_imported"] += 1
                continue

            new_emails.append(email)

        result["new_threads"] = len(new_emails)
        print(f"   {len(new_emails)} new threads to import")
        print(
            f"   Skipped: {result['skipped_existing']} existing, {result['skipped_imported']} previously imported"
        )

        if not new_emails:
            result["success"] = True
            result["message"] = "No new emails to import"
            state.update_last_sync()
            return result

        # Create reminders (and optionally drafts) for new emails
        if create_drafts:
            print(f"\n📝 Creating drafts and reminders in '{list_name}'...")
            if not ANTHROPIC_AVAILABLE:
                print("   ⚠️  Anthropic API not available - skipping draft generation")
                create_drafts = False
        else:
            print(f"\n📝 Creating reminders in '{list_name}'...")

        for email in new_emails:
            draft_link = None

            # Generate draft if requested
            if create_drafts and not dry_run:
                try:
                    print(f"   📄 Generating draft for: {email['sender_name'][:20]}...")
                    thread_messages = get_thread_messages(
                        email["thread_id"], credentials_path, token_path
                    )
                    draft_body = generate_draft_with_ai(email, thread_messages)

                    if draft_body:
                        # Add quoted thread
                        quoted = format_quoted_thread(thread_messages)
                        full_body = f"{draft_body}\n\n---\n{quoted}"

                        # Create Gmail draft
                        subject = email["subject"]
                        if not subject.startswith("Re:"):
                            subject = f"Re: {subject}"

                        # Build reply-all recipients from thread participants
                        thread_participants = get_thread_participants(
                            email["thread_id"], credentials_path, token_path
                        )
                        to_addr, cc_addr = build_reply_all_recipients(
                            email, thread_participants
                        )

                        draft_result = create_gmail_draft(
                            to=to_addr,
                            subject=subject,
                            body=full_body,
                            thread_id=email["thread_id"],
                            reply_to_id=email["message_id"],
                            cc=cc_addr if cc_addr else None,
                            credentials_path=credentials_path,
                            token_path=token_path,
                        )
                        draft_link = draft_result["link"]
                        result["drafts_created"] += 1
                        print("      ✓ Draft created")
                except Exception as e:
                    result["errors"].append(
                        f"Draft failed for {email['subject'][:30]}: {e}"
                    )
                    print(f"      ⚠️  Draft failed: {e}")

            # Create reminder
            if dry_run:
                draft_info = " + draft" if create_drafts else ""
                print(
                    f"   [DRY RUN] Would create{draft_info}: {email['sender_name']}: {email['subject'][:50]}"
                )
                result["reminders_created"] += 1
                if create_drafts:
                    result["drafts_created"] += 1
            else:
                success = create_email_reminder(
                    sender_name=email["sender_name"],
                    subject=email["subject"],
                    sender_email=email["sender_email"],
                    message_id=email["message_id"],
                    preview=email["preview"],
                    list_name=list_name,
                    draft_link=draft_link,
                )
                if success:
                    result["reminders_created"] += 1
                    state.mark_imported(email["thread_id"], email["message_id"])
                    draft_info = " (with draft)" if draft_link else ""
                    print(
                        f"   ✓ {email['sender_name']}: {email['subject'][:50]}{draft_info}"
                    )
                else:
                    result["errors"].append(f"Failed: {email['subject']}")

        # Save state
        state.update_last_sync()

        result["success"] = True
        result["state"] = state.get_stats()

        print(f"\n✅ Sync complete: {result['reminders_created']} reminders created")

    except Exception as e:
        result["error"] = str(e)
        print(f"\n❌ Sync failed: {e}")

    return result


def get_sync_status(state_path: Optional[Path] = None) -> dict:
    """Get current sync status."""
    state = EmailSyncState(state_path)
    return {"gmail_available": GMAIL_AVAILABLE, "state": state.get_stats()}


def clear_sync_state(state_path: Optional[Path] = None) -> dict:
    """Clear the sync state (allows re-importing all emails)."""
    state = EmailSyncState(state_path)
    old_stats = state.get_stats()

    state.imported_threads = set()
    state.imported_messages = set()
    state._save()

    return {"cleared": True, "previous": old_stats, "current": state.get_stats()}


def unstar_email(
    message_id: str,
    credentials_path: Optional[Path] = None,
    token_path: Optional[Path] = None,
) -> dict:
    """Remove the star from a Gmail message.

    Args:
        message_id: The Gmail message ID to unstar
        credentials_path: Path to OAuth credentials.json
        token_path: Path to token.json

    Returns:
        dict with success status
    """
    if not GMAIL_AVAILABLE:
        return {"success": False, "error": "Gmail API not available"}

    try:
        service = get_gmail_service(credentials_path, token_path)

        # Remove the STARRED label
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["STARRED"]},
        ).execute()

        return {"success": True, "message_id": message_id, "unstarred": True}

    except Exception as e:
        return {"success": False, "error": str(e), "message_id": message_id}


def extract_gmail_id_from_notes(notes: str) -> Optional[str]:
    """Extract Gmail message ID from reminder notes.

    The notes contain a link like:
    Gmail: https://mail.google.com/mail/u/0/#inbox/{message_id}

    Returns the message ID or None if not found.
    """
    if not notes:
        return None

    match = re.search(r"mail\.google\.com/mail/u/\d+/#inbox/([a-f0-9]+)", notes)
    if match:
        return match.group(1)
    return None


def email_done(
    reminder_id: Optional[str] = None,
    title_match: Optional[str] = None,
    list_name: str = DEFAULT_LIST_NAME,
    credentials_path: Optional[Path] = None,
    token_path: Optional[Path] = None,
    state_path: Optional[Path] = None,
) -> dict:
    """Complete an email reminder AND unstar the corresponding Gmail message.

    This is the streamlined workflow for processing email reminders:
    1. Find the reminder by ID or title
    2. Extract the Gmail message ID from the reminder notes
    3. Remove the star from the Gmail message
    4. Complete/delete the reminder in Apple Reminders
    5. Optionally remove from sync state to prevent re-import

    Args:
        reminder_id: The reminder's calendarItemIdentifier (preferred)
        title_match: Find reminder by exact title match (fallback)
        list_name: List to search in (default: Email Replies)
        credentials_path: Path to OAuth credentials.json
        token_path: Path to token.json
        state_path: Path to sync state file

    Returns:
        dict with success status and details of what was done
    """
    result = {
        "success": False,
        "reminder_completed": False,
        "email_unstarred": False,
        "gmail_message_id": None,
        "reminder_title": None,
    }

    # Import EventKit functions
    try:
        from .eventkit_sync import complete_reminder
        from .reminders_sync import load_reminders_cache
    except ImportError:
        # Running as standalone script
        import sys
        from pathlib import Path as P

        module_dir = P(__file__).parent
        if str(module_dir) not in sys.path:
            sys.path.insert(0, str(module_dir))
        from eventkit_sync import complete_reminder
        from reminders_sync import load_reminders_cache

    # Find the reminder to get the notes (which contain the Gmail link)
    reminders = load_reminders_cache()
    target_reminder = None

    for r in reminders:
        if reminder_id and r.get("id") == reminder_id:
            target_reminder = r
            break
        if title_match and r.get("title") == title_match:
            # Optionally filter by list
            if list_name and r.get("list") != list_name:
                continue
            target_reminder = r
            break

    if not target_reminder:
        result["error"] = f"Reminder not found: {reminder_id or title_match}"
        return result

    result["reminder_title"] = target_reminder.get("title")

    # Extract Gmail message ID from notes
    notes = target_reminder.get("notes", "")
    gmail_id = extract_gmail_id_from_notes(notes)
    result["gmail_message_id"] = gmail_id

    if not gmail_id:
        result["error"] = "Could not find Gmail message ID in reminder notes"
        return result

    # Step 1: Unstar the email in Gmail
    unstar_result = unstar_email(gmail_id, credentials_path, token_path)
    if unstar_result.get("success"):
        result["email_unstarred"] = True
    else:
        # Log but continue - we still want to complete the reminder
        result["unstar_error"] = unstar_result.get("error")

    # Step 2: Complete the reminder in Apple Reminders
    complete_result = complete_reminder(
        reminder_id=reminder_id,
        title_match=title_match,
        list_name=list_name,
    )

    if complete_result.get("success"):
        result["reminder_completed"] = True
        result["success"] = True
    else:
        result["complete_error"] = complete_result.get("error")

    # Step 3: Optionally remove from sync state (so it won't warn about re-import)
    # This is optional - the email is unstarred so it won't be picked up anyway
    if gmail_id:
        try:
            state = EmailSyncState(state_path)
            # Find and remove the thread/message from imported sets
            if gmail_id in state.imported_messages:
                state.imported_messages.discard(gmail_id)
                state._save()
        except Exception:
            pass  # Non-critical

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "sync":
            dry_run = "--dry-run" in sys.argv
            with_drafts = "--drafts" in sys.argv
            result = sync_emails_to_reminders(
                dry_run=dry_run, create_drafts=with_drafts
            )
            print(json.dumps(result, indent=2))

        elif cmd == "status":
            result = get_sync_status()
            print(json.dumps(result, indent=2))

        elif cmd == "clear":
            result = clear_sync_state()
            print(json.dumps(result, indent=2))

        else:
            print(f"Unknown command: {cmd}")
            print("Commands: sync [--dry-run] [--drafts], status, clear")
    else:
        print("Gmail to Reminders Sync")
        print()
        print("Commands:")
        print("  sync [--dry-run] [--drafts]  Sync starred emails to reminders")
        print("                               --drafts: Generate AI draft replies")
        print("  status                       Show sync state")
        print("  clear                        Clear sync state (allow re-import)")
