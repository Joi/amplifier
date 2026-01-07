---
name: gmail
description: Read, search, send, and manage Gmail messages. Use when user wants to check email, send messages, or manage their inbox.
version: 1.0.0
---

# Gmail Skill

Native integration with Gmail API via OAuth2. Works in subagents, scripts, cron jobs.

## When to Use

- User asks about their email or inbox
- User wants to send an email
- User asks to search for specific emails
- User wants to reply to a message
- Part of morning routine (check unread count)

## Setup (One-Time)

```bash
# Authorize Gmail access (opens browser)
python -m amplifier.skills.gmail auth
```

Requires OAuth credentials at `~/.googleauth/credentials.json`

## Python API (Preferred)

```python
from amplifier.skills import (
    list_messages, get_message, search_messages, send_email,
    reply_to_message, get_unread_count, mark_as_read,
    EmailMessage, EmailAddress
)

# List recent emails
messages = await list_messages(max_results=10)
for msg in messages:
    print(f"{msg.sender.email}: {msg.subject}")

# List only unread
unread = await list_messages(label_ids=["UNREAD"])

# Search emails (Gmail search syntax)
results = await search_messages("from:alice@example.com subject:meeting")
results = await search_messages("is:unread after:2024/01/01")
results = await search_messages("has:attachment filename:pdf")

# Get full message with body
msg = await get_message(message_id)
print(msg.body_text)  # Plain text body
print(msg.body_html)  # HTML body

# Send email
sent = await send_email(
    to="bob@example.com",
    subject="Hello",
    body="Hi Bob, how are you?"
)

# Send to multiple recipients
sent = await send_email(
    to=["alice@example.com", "bob@example.com"],
    cc="manager@example.com",
    subject="Team Update",
    body="<h1>Update</h1><p>All good!</p>",
    html=True
)

# Reply to a message
reply = await reply_to_message(message_id, "Thanks for the update!")
reply = await reply_to_message(message_id, "Got it!", reply_all=True)

# Get unread count
count = await get_unread_count()
print(f"You have {count} unread emails")

# Mark as read/unread
await mark_as_read(message_id)
await mark_as_unread(message_id)

# Star/trash
await star_message(message_id)
await trash_message(message_id)
```

## Sync Wrappers

```python
from amplifier.skills import (
    list_messages_sync, get_message_sync, search_messages_sync, send_email_sync
)

# For use outside async context
messages = list_messages_sync(max_results=5)
msg = get_message_sync(message_id)
```

## Data Classes

```python
@dataclass
class EmailMessage:
    id: str
    thread_id: str
    subject: str
    sender: EmailAddress | None
    to: list[EmailAddress]
    cc: list[EmailAddress]
    date: datetime | None
    snippet: str
    body_text: str
    body_html: str
    labels: list[str]
    is_unread: bool
    is_starred: bool
    has_attachments: bool

@dataclass
class EmailAddress:
    email: str
    name: str = ""
```

## Gmail Search Syntax

| Query | Description |
|-------|-------------|
| `from:alice@example.com` | From specific sender |
| `to:bob@example.com` | To specific recipient |
| `subject:meeting` | Subject contains word |
| `is:unread` | Unread messages |
| `is:starred` | Starred messages |
| `has:attachment` | Has attachments |
| `filename:pdf` | Attachment filename |
| `after:2024/01/01` | After date |
| `before:2024/02/01` | Before date |
| `label:work` | Has label |
| `larger:5M` | Larger than 5MB |

## CLI Interface

```bash
# List recent emails
python -m amplifier.skills.gmail list
python -m amplifier.skills.gmail list --unread --limit 5

# Search
python -m amplifier.skills.gmail search "from:alice subject:project"

# Read a message
python -m amplifier.skills.gmail read MESSAGE_ID

# Send
python -m amplifier.skills.gmail send --to bob@example.com --subject "Hi" --body "Hello!"

# Check unread count
python -m amplifier.skills.gmail unread

# List labels
python -m amplifier.skills.gmail labels
```

## Advantages Over MCP

- ✅ Works in subagents (MCP tools don't inherit)
- ✅ Async-first with sync wrappers
- ✅ Works in scripts, cron jobs, SDK calls
- ✅ Returns proper Python dataclasses
- ✅ Uses existing OAuth infrastructure
