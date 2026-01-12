#!/usr/bin/env python3
"""
Email Drafts Sync - AI-powered draft replies for starred Gmail emails.

This tool:
1. Gets all starred emails from Gmail (last 30 days)
2. Fetches full thread context for each email
3. Uses Claude to generate thoughtful draft replies
4. Creates Gmail drafts with quoted thread
5. Creates Apple Reminders with links to drafts
6. Cleans up old/duplicate drafts

Usage:
    python email_drafts_sync.py              # Full sync
    python email_drafts_sync.py --dry-run    # Preview changes without applying
    python email_drafts_sync.py --status     # Show current sync status
    python email_drafts_sync.py --cleanup    # Remove old drafts from Gmail

Designed to run daily via periodic/jobs.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from datetime import timedelta
from pathlib import Path

# Add tools directory to path for gmail import
TOOLS_DIR = Path(__file__).parent
sys.path.insert(0, str(TOOLS_DIR))

from gmail import create_draft  # noqa: E402
from gmail import extract_body  # noqa: E402
from gmail import format_message  # noqa: E402
from gmail import get_gmail_service  # noqa: E402
from gmail import get_starred  # noqa: E402

# Paths
STATE_FILE = Path.home() / ".amplifier" / "email_drafts_sync_state.json"
REMINDERS_LIST = "Email Follow-up"

# Anthropic API for draft generation
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def load_state() -> dict:
    """Load sync state from disk."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"drafted_emails": {}, "last_sync": None}


def save_state(state: dict):
    """Save sync state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def run_applescript(script: str) -> str:
    """Execute AppleScript and return result."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".scpt", delete=False) as f:
        f.write(script)
        temp_path = f.name

    try:
        result = subprocess.run(["osascript", temp_path], capture_output=True, text=True, timeout=60)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    finally:
        os.unlink(temp_path)


def escape_applescript(s: str) -> str:
    """Escape string for AppleScript."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def get_reminder_email_ids() -> set:
    """Get email IDs currently in the Email Follow-up reminders list."""
    script = f'''
    tell application "Reminders"
        if not (exists list "{REMINDERS_LIST}") then
            return ""
        end if

        set output to ""
        tell list "{REMINDERS_LIST}"
            repeat with r in (every reminder whose completed is false)
                set n to body of r
                if n contains "mail.google.com" then
                    set output to output & n & "|||"
                end if
            end repeat
        end tell
        return output
    end tell
    '''
    result = run_applescript(script)

    # Extract email IDs from Gmail links
    email_ids = set()
    for link in result.split("|||"):
        # Match Gmail inbox link format
        match = re.search(r"#inbox/([a-f0-9]+)", link)
        if match:
            email_ids.add(match.group(1))
        # Match Gmail drafts link format
        match = re.search(r"#drafts/([a-f0-9]+)", link)
        if match:
            email_ids.add(match.group(1))

    return email_ids


def delete_reminder_by_email_id(email_id: str) -> bool:
    """Delete a reminder that contains a specific email ID in its body."""
    script = f'''
    tell application "Reminders"
        tell list "{REMINDERS_LIST}"
            set toDelete to (every reminder whose body contains "{email_id}")
            repeat with r in toDelete
                delete r
            end repeat
        end tell
        return "done"
    end tell
    '''
    result = run_applescript(script)
    return result == "done"


def create_reminder(title: str, body: str) -> bool:
    """Create a reminder in the Email Follow-up list."""
    title_escaped = escape_applescript(title[:200])
    body_escaped = escape_applescript(body)

    script = f'''
    tell application "Reminders"
        if not (exists list "{REMINDERS_LIST}") then
            make new list with properties {{name:"{REMINDERS_LIST}"}}
        end if

        tell list "{REMINDERS_LIST}"
            make new reminder with properties {{name:"{title_escaped}", body:"{body_escaped}"}}
        end tell
        return "done"
    end tell
    '''
    result = run_applescript(script)
    return result == "done"


def get_thread_messages(thread_id: str) -> list[dict]:
    """Get all messages in a thread, ordered by date."""
    service = get_gmail_service()

    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()

    messages = []
    for msg in thread.get("messages", []):
        formatted = format_message(msg, include_body=True)
        formatted["body"] = extract_body(msg)
        messages.append(formatted)

    return messages


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
        lines.append(f"On {msg['date']}, {msg['from_name']} <{msg['from_email']}> wrote:")
        lines.append("")
        body = msg.get("body", "").strip()
        for line in body.split("\n"):
            lines.append(f"> {line}")

    return "\n".join(lines)


def generate_draft_with_ai(email: dict, thread_messages: list[dict]) -> str:
    """Generate a draft reply using Claude API."""
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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

    prompt = f"""You are drafting an email reply for Joi Ito. Write a thoughtful, helpful response based on the email thread below.

Guidelines:
- Be warm but professional
- Be concise and direct
- Address the specific points raised in the email
- If action items are mentioned, acknowledge them
- If questions are asked, answer them or indicate you'll follow up
- Match the tone of the conversation
- Sign off as "Joi" (not "Best, Joi" - just "Joi")

Email thread (oldest to newest):
{thread_context}

Write ONLY the reply body text. Start with a greeting like "Hi {first_name}," and end with just "Joi". Do not include subject line or email headers."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def get_existing_drafts() -> dict[str, dict]:
    """Get all existing drafts from Gmail, keyed by thread ID."""
    service = get_gmail_service()

    drafts_response = service.users().drafts().list(userId="me").execute()
    drafts = {}

    for draft in drafts_response.get("drafts", []):
        draft_detail = service.users().drafts().get(userId="me", id=draft["id"]).execute()
        thread_id = draft_detail.get("message", {}).get("threadId")
        if thread_id:
            drafts[thread_id] = {
                "draft_id": draft["id"],
                "message_id": draft_detail.get("message", {}).get("id"),
            }

    return drafts


def delete_gmail_draft(draft_id: str) -> bool:
    """Delete a draft from Gmail."""
    service = get_gmail_service()
    try:
        service.users().drafts().delete(userId="me", id=draft_id).execute()
        return True
    except Exception:
        return False


def cleanup_old_drafts(days: int = 30, dry_run: bool = False) -> dict:
    """Remove drafts older than N days from Gmail."""
    state = load_state()
    drafted = state.get("drafted_emails", {})

    removed = []
    kept = 0
    cutoff = datetime.now() - timedelta(days=days)

    for email_id, info in list(drafted.items()):
        created_str = info.get("created")
        if not created_str:
            continue

        try:
            created = datetime.fromisoformat(created_str)
        except ValueError:
            continue

        if created < cutoff:
            draft_id = info.get("draft_id")
            if draft_id and not dry_run:
                if delete_gmail_draft(draft_id):
                    del drafted[email_id]
                    removed.append(email_id)
            elif dry_run:
                removed.append(email_id)
        else:
            kept += 1

    if not dry_run:
        state["drafted_emails"] = drafted
        save_state(state)

    return {"removed": removed, "kept": kept}


def sync_emails(dry_run: bool = False, verbose: bool = True) -> dict:
    """Main sync function."""
    state = load_state()
    drafted = state.get("drafted_emails", {})

    results = {
        "starred_count": 0,
        "new_drafts": [],
        "new_reminders": [],
        "removed_reminders": [],
        "skipped": [],
        "errors": [],
    }

    if verbose:
        print("Fetching starred emails from Gmail...")

    try:
        starred_emails = get_starred(max_results=100)
    except Exception as e:
        results["errors"].append(f"Failed to fetch Gmail: {e}")
        return results

    results["starred_count"] = len(starred_emails)
    starred_ids = {email["id"] for email in starred_emails}

    if verbose:
        print(f"Found {len(starred_emails)} starred emails")

    if verbose:
        print("Checking current reminders...")

    reminder_email_ids = get_reminder_email_ids()

    if verbose:
        print(f"Found {len(reminder_email_ids)} email reminders")

    # Get existing Gmail drafts to avoid duplicates
    if verbose:
        print("Checking existing Gmail drafts...")

    existing_drafts = get_existing_drafts()

    if verbose:
        print(f"Found {len(existing_drafts)} existing drafts")

    # Remove reminders for emails that are no longer starred
    for email_id in reminder_email_ids:
        if email_id not in starred_ids:
            if verbose:
                print(f"  Removing reminder for unstarred email: {email_id[:16]}...")

            if not dry_run:
                if delete_reminder_by_email_id(email_id):
                    results["removed_reminders"].append(email_id)
                    if email_id in drafted:
                        # Also delete the Gmail draft
                        draft_id = drafted[email_id].get("draft_id")
                        if draft_id:
                            delete_gmail_draft(draft_id)
                        del drafted[email_id]
                else:
                    results["errors"].append(f"Failed to delete reminder: {email_id}")
            else:
                results["removed_reminders"].append(email_id)

    # Process each starred email
    for email in starred_emails:
        email_id = email["id"]
        thread_id = email["thread_id"]
        subject = email.get("subject", "(no subject)")
        from_name = email.get("from_name", "Unknown")

        # Skip if already has a draft for this thread
        if thread_id in existing_drafts and email_id in drafted:
            results["skipped"].append(email_id)
            continue

        # Skip if already processed and has reminder
        if email_id in reminder_email_ids and email_id in drafted:
            results["skipped"].append(email_id)
            continue

        if verbose:
            print(f"  Processing: {from_name[:20]}: {subject[:40]}...")

        # Get full thread
        try:
            thread_messages = get_thread_messages(thread_id)
        except Exception as e:
            results["errors"].append(f"Failed to get thread for {email_id}: {e}")
            continue

        # Generate AI draft
        if verbose:
            print("    Generating AI draft...")

        draft_link = None

        if not dry_run:
            try:
                draft_body = generate_draft_with_ai(email, thread_messages)
            except Exception as e:
                results["errors"].append(f"Failed to generate draft for {email_id}: {e}")
                first_name = from_name.split()[0] if from_name else "there"
                draft_body = f"""Hi {first_name},

Thank you for your email.

[Your response here]

Joi"""

            # Add quoted thread below the reply
            quoted_thread = format_quoted_thread(thread_messages)
            full_body = f"{draft_body}\n\n---\n{quoted_thread}"

            # Create Gmail draft
            try:
                draft_result = create_draft(
                    to=email["from_email"],
                    subject=f"Re: {subject}" if not subject.startswith("Re:") else subject,
                    body=full_body,
                    reply_to_id=email_id,
                )
                draft_link = draft_result["link"]

                if verbose:
                    print(f"    Created Gmail draft: {draft_result['id']}")

                # Save to state
                drafted[email_id] = {
                    "draft_id": draft_result["id"],
                    "draft_link": draft_link,
                    "created": datetime.now().isoformat(),
                    "subject": subject,
                    "from": email["from_email"],
                }
                results["new_drafts"].append(email_id)

            except Exception as e:
                results["errors"].append(f"Failed to create Gmail draft for {email_id}: {e}")
                continue
        else:
            draft_link = "[DRY RUN - would create draft]"
            results["new_drafts"].append(email_id)

        # Create reminder if needed
        if email_id not in reminder_email_ids:
            if verbose:
                print("    Creating reminder...")

            clean_from = from_name
            if clean_from.startswith('"') and clean_from.endswith('"'):
                clean_from = clean_from[1:-1]

            title = f"📧 {clean_from}: {subject[:50]}"
            if len(subject) > 50:
                title += "..."

            body = f"""From: {email["from_email"]}

Draft: {draft_link}

Gmail: {email["link"]}

Preview: {email.get("snippet", "")[:200]}"""

            if not dry_run:
                if create_reminder(title, body):
                    results["new_reminders"].append(email_id)
                else:
                    results["errors"].append(f"Failed to create reminder: {email_id}")
            else:
                results["new_reminders"].append(email_id)

    # Save state
    if not dry_run:
        state["drafted_emails"] = drafted
        state["last_sync"] = datetime.now().isoformat()
        save_state(state)

    return results


def print_status():
    """Print current sync status."""
    state = load_state()
    drafted = state.get("drafted_emails", {})
    last_sync = state.get("last_sync")

    print("Email Drafts Sync Status")
    print("=" * 40)
    print(f"Last sync: {last_sync or 'Never'}")
    print(f"Drafted emails tracked: {len(drafted)}")
    print(f"State file: {STATE_FILE}")
    print()

    if drafted:
        print("Recent drafts:")
        for _email_id, info in list(drafted.items())[-10:]:
            subject = info.get("subject", "Unknown")[:40]
            draft_link = info.get("draft_link", "")
            print(f"  - {subject}")
            print(f"    {draft_link}")


def main():
    parser = argparse.ArgumentParser(description="Sync starred emails to reminders with AI draft replies")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup old drafts from Gmail")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")

    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.cleanup:
        result = cleanup_old_drafts(days=30, dry_run=args.dry_run)
        print(f"Removed {len(result['removed'])} drafts, kept {result['kept']}")
        return

    verbose = not args.quiet

    if verbose:
        print("=" * 50)
        print("Email Drafts Sync (AI-Powered)")
        print("=" * 50)
        if args.dry_run:
            print("DRY RUN - no changes will be made")
        print()

    results = sync_emails(dry_run=args.dry_run, verbose=verbose)

    if verbose:
        print()
        print("=" * 50)
        print("Summary")
        print("=" * 50)
        print(f"Starred emails: {results['starred_count']}")
        print(f"New drafts created: {len(results['new_drafts'])}")
        print(f"New reminders created: {len(results['new_reminders'])}")
        print(f"Reminders removed (unstarred): {len(results['removed_reminders'])}")
        print(f"Skipped (already synced): {len(results['skipped'])}")
        if results["errors"]:
            print(f"Errors: {len(results['errors'])}")
            for err in results["errors"]:
                print(f"  - {err}")

    if results["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
