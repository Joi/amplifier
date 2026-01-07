"""Gmail skill - Read, search, send, and manage emails.

Native Amplifier skill for Gmail. Works everywhere:
main session, subagents, SDK, scripts, cron jobs.

Usage:
    from amplifier.skills.gmail import (
        list_messages, get_message, search_messages, send_email,
        reply_to_message, get_threads, get_labels
    )

    # List recent emails
    messages = await list_messages(max_results=10)

    # Search emails
    messages = await search_messages("from:alice@example.com subject:meeting")

    # Get full message
    msg = await get_message(message_id)
    print(msg.subject, msg.sender, msg.body_text)

    # Send email
    await send_email(
        to="bob@example.com",
        subject="Hello",
        body="Hi Bob!"
    )

    # Reply to a message
    await reply_to_message(message_id, "Thanks for the update!")
"""

from __future__ import annotations

import asyncio
import base64
import email.utils
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal

import httpx

from amplifier.utils.google_auth import (
    GoogleCredentials,
    GoogleScopes,
    get_google_credentials,
)

# Gmail API base URL
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"


@dataclass
class EmailAddress:
    """Email address with optional name."""

    email: str
    name: str = ""

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email

    @classmethod
    def parse(cls, header: str) -> "EmailAddress":
        """Parse email header into EmailAddress."""
        name, email_addr = email.utils.parseaddr(header)
        return cls(email=email_addr, name=name)


@dataclass
class EmailMessage:
    """Represents a Gmail message."""

    id: str
    thread_id: str
    subject: str = ""
    sender: EmailAddress | None = None
    to: list[EmailAddress] = field(default_factory=list)
    cc: list[EmailAddress] = field(default_factory=list)
    date: datetime | None = None
    snippet: str = ""
    body_text: str = ""
    body_html: str = ""
    labels: list[str] = field(default_factory=list)
    is_unread: bool = False
    is_starred: bool = False
    has_attachments: bool = False


@dataclass
class EmailThread:
    """Represents a Gmail thread (conversation)."""

    id: str
    snippet: str = ""
    messages: list[EmailMessage] = field(default_factory=list)


@dataclass
class Label:
    """Represents a Gmail label."""

    id: str
    name: str
    type: str = "user"  # "system" or "user"
    messages_total: int = 0
    messages_unread: int = 0


def _get_credentials(
    scopes: list[str] | None = None,
) -> GoogleCredentials:
    """Get Gmail credentials."""
    scopes = scopes or [GoogleScopes.GMAIL_MODIFY, GoogleScopes.GMAIL_SEND]
    return get_google_credentials(
        app_name="amplifier",
        scopes=scopes,
        service="google",  # Shared token with Calendar
    )


def _get_headers(creds: GoogleCredentials) -> dict:
    """Get HTTP headers with auth."""
    return {
        "Authorization": f"Bearer {creds.access_token}",
        "Content-Type": "application/json",
    }


def _parse_message(data: dict, include_body: bool = False) -> EmailMessage:
    """Parse Gmail API message response into EmailMessage."""
    headers = {}
    if "payload" in data:
        for header in data["payload"].get("headers", []):
            headers[header["name"].lower()] = header["value"]

    # Parse sender
    sender = None
    if "from" in headers:
        sender = EmailAddress.parse(headers["from"])

    # Parse recipients
    to = []
    if "to" in headers:
        for addr in headers["to"].split(","):
            to.append(EmailAddress.parse(addr.strip()))

    cc = []
    if "cc" in headers:
        for addr in headers["cc"].split(","):
            cc.append(EmailAddress.parse(addr.strip()))

    # Parse date
    date = None
    if "date" in headers:
        try:
            parsed = email.utils.parsedate_to_datetime(headers["date"])
            date = parsed
        except (ValueError, TypeError):
            pass

    # Parse body
    body_text = ""
    body_html = ""
    has_attachments = False

    if include_body and "payload" in data:
        payload = data["payload"]

        def extract_body(part: dict) -> tuple[str, str, bool]:
            text, html, attach = "", "", False
            mime_type = part.get("mimeType", "")

            if part.get("filename"):
                attach = True

            if "body" in part and "data" in part["body"]:
                decoded = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                    "utf-8", errors="replace"
                )
                if mime_type == "text/plain":
                    text = decoded
                elif mime_type == "text/html":
                    html = decoded

            for subpart in part.get("parts", []):
                t, h, a = extract_body(subpart)
                text = text or t
                html = html or h
                attach = attach or a

            return text, html, attach

        body_text, body_html, has_attachments = extract_body(payload)

    # Parse labels
    labels = data.get("labelIds", [])
    is_unread = "UNREAD" in labels
    is_starred = "STARRED" in labels

    return EmailMessage(
        id=data["id"],
        thread_id=data.get("threadId", ""),
        subject=headers.get("subject", "(no subject)"),
        sender=sender,
        to=to,
        cc=cc,
        date=date,
        snippet=data.get("snippet", ""),
        body_text=body_text,
        body_html=body_html,
        labels=labels,
        is_unread=is_unread,
        is_starred=is_starred,
        has_attachments=has_attachments,
    )


async def list_messages(
    max_results: int = 20,
    label_ids: list[str] | None = None,
    include_spam_trash: bool = False,
) -> list[EmailMessage]:
    """List recent messages.

    Args:
        max_results: Maximum messages to return (default: 20)
        label_ids: Filter by label IDs (e.g., ["INBOX", "UNREAD"])
        include_spam_trash: Include spam and trash

    Returns:
        List of EmailMessage objects (without full body)
    """
    creds = _get_credentials([GoogleScopes.GMAIL_READONLY])

    params = {
        "maxResults": max_results,
        "includeSpamTrash": include_spam_trash,
    }
    if label_ids:
        params["labelIds"] = ",".join(label_ids)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GMAIL_API_BASE}/users/me/messages",
            headers=_get_headers(creds),
            params=params,
        )
        response.raise_for_status()
        data = response.json()

        messages = []
        for msg_ref in data.get("messages", []):
            # Fetch each message's metadata
            msg_response = await client.get(
                f"{GMAIL_API_BASE}/users/me/messages/{msg_ref['id']}",
                headers=_get_headers(creds),
                params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]},
            )
            msg_response.raise_for_status()
            messages.append(_parse_message(msg_response.json()))

        return messages


async def get_message(message_id: str) -> EmailMessage:
    """Get a full message by ID.

    Args:
        message_id: Gmail message ID

    Returns:
        EmailMessage with full body content
    """
    creds = _get_credentials([GoogleScopes.GMAIL_READONLY])

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GMAIL_API_BASE}/users/me/messages/{message_id}",
            headers=_get_headers(creds),
            params={"format": "full"},
        )
        response.raise_for_status()
        return _parse_message(response.json(), include_body=True)


async def search_messages(
    query: str,
    max_results: int = 20,
    include_spam_trash: bool = False,
) -> list[EmailMessage]:
    """Search messages using Gmail search syntax.

    Args:
        query: Gmail search query (e.g., "from:alice subject:meeting is:unread")
        max_results: Maximum messages to return
        include_spam_trash: Include spam and trash

    Returns:
        List of matching EmailMessage objects

    Query examples:
        - "from:alice@example.com"
        - "subject:meeting"
        - "is:unread"
        - "after:2024/01/01 before:2024/02/01"
        - "has:attachment"
        - "label:work"
    """
    creds = _get_credentials([GoogleScopes.GMAIL_READONLY])

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GMAIL_API_BASE}/users/me/messages",
            headers=_get_headers(creds),
            params={
                "q": query,
                "maxResults": max_results,
                "includeSpamTrash": include_spam_trash,
            },
        )
        response.raise_for_status()
        data = response.json()

        messages = []
        for msg_ref in data.get("messages", []):
            msg_response = await client.get(
                f"{GMAIL_API_BASE}/users/me/messages/{msg_ref['id']}",
                headers=_get_headers(creds),
                params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]},
            )
            msg_response.raise_for_status()
            messages.append(_parse_message(msg_response.json()))

        return messages


async def send_email(
    to: str | list[str],
    subject: str,
    body: str,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    html: bool = False,
) -> EmailMessage:
    """Send an email.

    Args:
        to: Recipient email(s)
        subject: Email subject
        body: Email body (plain text or HTML)
        cc: CC recipient(s)
        bcc: BCC recipient(s)
        html: Whether body is HTML

    Returns:
        The sent EmailMessage
    """
    creds = _get_credentials([GoogleScopes.GMAIL_SEND])

    # Build message
    if html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "html"))
    else:
        msg = MIMEText(body, "plain")

    # Handle recipient lists
    to_list = [to] if isinstance(to, str) else to
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject

    if cc:
        cc_list = [cc] if isinstance(cc, str) else cc
        msg["Cc"] = ", ".join(cc_list)

    # Encode message
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GMAIL_API_BASE}/users/me/messages/send",
            headers=_get_headers(creds),
            json={"raw": raw},
        )
        response.raise_for_status()
        data = response.json()

        # Fetch the sent message
        return await get_message(data["id"])


async def reply_to_message(
    message_id: str,
    body: str,
    reply_all: bool = False,
    html: bool = False,
) -> EmailMessage:
    """Reply to a message.

    Args:
        message_id: ID of message to reply to
        body: Reply body
        reply_all: Reply to all recipients
        html: Whether body is HTML

    Returns:
        The sent reply EmailMessage
    """
    creds = _get_credentials([GoogleScopes.GMAIL_SEND, GoogleScopes.GMAIL_READONLY])

    # Get original message
    original = await get_message(message_id)

    # Build reply
    if html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "html"))
    else:
        msg = MIMEText(body, "plain")

    # Set reply headers
    msg["In-Reply-To"] = message_id
    msg["References"] = message_id

    # Reply to sender
    if original.sender:
        msg["To"] = str(original.sender)

    # Reply all includes original recipients
    if reply_all and original.to:
        all_recipients = [str(original.sender)] if original.sender else []
        all_recipients.extend(str(r) for r in original.to)
        msg["To"] = ", ".join(all_recipients)
        if original.cc:
            msg["Cc"] = ", ".join(str(r) for r in original.cc)

    # Add Re: prefix if not present
    subject = original.subject
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    msg["Subject"] = subject

    # Encode and send
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GMAIL_API_BASE}/users/me/messages/send",
            headers=_get_headers(creds),
            json={"raw": raw, "threadId": original.thread_id},
        )
        response.raise_for_status()
        data = response.json()

        return await get_message(data["id"])


async def get_labels() -> list[Label]:
    """Get all Gmail labels.

    Returns:
        List of Label objects
    """
    creds = _get_credentials([GoogleScopes.GMAIL_READONLY])

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GMAIL_API_BASE}/users/me/labels",
            headers=_get_headers(creds),
        )
        response.raise_for_status()
        data = response.json()

        labels = []
        for label_data in data.get("labels", []):
            # Get full label info
            label_response = await client.get(
                f"{GMAIL_API_BASE}/users/me/labels/{label_data['id']}",
                headers=_get_headers(creds),
            )
            if label_response.status_code == 200:
                full_data = label_response.json()
                labels.append(
                    Label(
                        id=full_data["id"],
                        name=full_data["name"],
                        type=full_data.get("type", "user"),
                        messages_total=full_data.get("messagesTotal", 0),
                        messages_unread=full_data.get("messagesUnread", 0),
                    )
                )

        return labels


async def modify_labels(
    message_id: str,
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
) -> EmailMessage:
    """Modify labels on a message.

    Args:
        message_id: Message ID
        add_labels: Labels to add (e.g., ["STARRED", "IMPORTANT"])
        remove_labels: Labels to remove (e.g., ["UNREAD"])

    Returns:
        Updated EmailMessage
    """
    creds = _get_credentials([GoogleScopes.GMAIL_MODIFY])

    body = {}
    if add_labels:
        body["addLabelIds"] = add_labels
    if remove_labels:
        body["removeLabelIds"] = remove_labels

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GMAIL_API_BASE}/users/me/messages/{message_id}/modify",
            headers=_get_headers(creds),
            json=body,
        )
        response.raise_for_status()

        return await get_message(message_id)


async def mark_as_read(message_id: str) -> EmailMessage:
    """Mark a message as read."""
    return await modify_labels(message_id, remove_labels=["UNREAD"])


async def mark_as_unread(message_id: str) -> EmailMessage:
    """Mark a message as unread."""
    return await modify_labels(message_id, add_labels=["UNREAD"])


async def star_message(message_id: str) -> EmailMessage:
    """Star a message."""
    return await modify_labels(message_id, add_labels=["STARRED"])


async def unstar_message(message_id: str) -> EmailMessage:
    """Remove star from a message."""
    return await modify_labels(message_id, remove_labels=["STARRED"])


async def trash_message(message_id: str) -> None:
    """Move a message to trash.

    Args:
        message_id: Message ID
    """
    creds = _get_credentials([GoogleScopes.GMAIL_MODIFY])

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GMAIL_API_BASE}/users/me/messages/{message_id}/trash",
            headers=_get_headers(creds),
        )
        response.raise_for_status()


async def get_unread_count() -> int:
    """Get count of unread messages in inbox.

    Returns:
        Number of unread messages
    """
    labels = await get_labels()
    for label in labels:
        if label.id == "INBOX":
            return label.messages_unread
    return 0


# =============================================================================
# Synchronous Wrappers
# =============================================================================


def list_messages_sync(
    max_results: int = 20,
    label_ids: list[str] | None = None,
) -> list[EmailMessage]:
    """Sync wrapper for list_messages."""
    return asyncio.run(list_messages(max_results, label_ids))


def get_message_sync(message_id: str) -> EmailMessage:
    """Sync wrapper for get_message."""
    return asyncio.run(get_message(message_id))


def search_messages_sync(query: str, max_results: int = 20) -> list[EmailMessage]:
    """Sync wrapper for search_messages."""
    return asyncio.run(search_messages(query, max_results))


def send_email_sync(
    to: str | list[str],
    subject: str,
    body: str,
    cc: str | list[str] | None = None,
    html: bool = False,
) -> EmailMessage:
    """Sync wrapper for send_email."""
    return asyncio.run(send_email(to, subject, body, cc=cc, html=html))


# =============================================================================
# CLI Interface
# =============================================================================


def _cli_main() -> None:
    """CLI entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Gmail CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_p = subparsers.add_parser("list", help="List recent messages")
    list_p.add_argument("--limit", "-n", type=int, default=10, help="Max messages")
    list_p.add_argument("--unread", action="store_true", help="Only unread")

    # Search command
    search_p = subparsers.add_parser("search", help="Search messages")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--limit", "-n", type=int, default=10, help="Max results")

    # Read command
    read_p = subparsers.add_parser("read", help="Read a message")
    read_p.add_argument("message_id", help="Message ID")

    # Send command
    send_p = subparsers.add_parser("send", help="Send an email")
    send_p.add_argument("--to", "-t", required=True, help="Recipient")
    send_p.add_argument("--subject", "-s", required=True, help="Subject")
    send_p.add_argument("--body", "-b", required=True, help="Body")

    # Unread count
    subparsers.add_parser("unread", help="Get unread count")

    # Labels
    subparsers.add_parser("labels", help="List labels")

    # Auth
    auth_p = subparsers.add_parser("auth", help="Authorize Gmail access")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "auth":
            from amplifier.utils.google_auth import authorize_google
            authorize_google(
                app_name="amplifier",
                scopes=[GoogleScopes.GMAIL_MODIFY, GoogleScopes.GMAIL_SEND],
                service="gmail",
            )

        elif args.command == "list":
            label_ids = ["UNREAD"] if args.unread else None
            messages = list_messages_sync(args.limit, label_ids)
            for msg in messages:
                status = "●" if msg.is_unread else "○"
                sender = msg.sender.email if msg.sender else "Unknown"
                print(f"{status} {msg.id[:8]} | {sender[:25]:<25} | {msg.subject[:50]}")

        elif args.command == "search":
            messages = search_messages_sync(args.query, args.limit)
            for msg in messages:
                sender = msg.sender.email if msg.sender else "Unknown"
                print(f"{msg.id[:8]} | {sender[:25]:<25} | {msg.subject[:50]}")

        elif args.command == "read":
            msg = get_message_sync(args.message_id)
            print(f"From: {msg.sender}")
            print(f"To: {', '.join(str(r) for r in msg.to)}")
            print(f"Date: {msg.date}")
            print(f"Subject: {msg.subject}")
            print("-" * 60)
            print(msg.body_text or msg.snippet)

        elif args.command == "send":
            msg = send_email_sync(args.to, args.subject, args.body)
            print(f"✓ Sent! Message ID: {msg.id}")

        elif args.command == "unread":
            count = asyncio.run(get_unread_count())
            print(f"Unread messages: {count}")

        elif args.command == "labels":
            labels = asyncio.run(get_labels())
            for label in sorted(labels, key=lambda l: l.name):
                unread = f" ({label.messages_unread} unread)" if label.messages_unread else ""
                print(f"  {label.name}{unread}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
