#!/usr/bin/env python3
"""
Email Drafts Sync - Sync starred Gmail emails to Apple Reminders with draft replies.

This tool:
1. Gets all starred emails from Gmail (last 30 days)
2. Creates draft replies for each (if not already drafted)
3. Syncs to "Email Follow-up" Apple Reminders list with draft links
4. Removes reminders for emails that are no longer starred (Gmail is ground truth)

Usage:
    python email_drafts_sync.py              # Full sync
    python email_drafts_sync.py --dry-run    # Preview changes without applying
    python email_drafts_sync.py --status     # Show current sync status

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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add tools directory to path for gmail import
TOOLS_DIR = Path(__file__).parent
sys.path.insert(0, str(TOOLS_DIR))

from gmail import get_starred, get_message, create_draft, gmail_link

# State file to track drafted emails
STATE_FILE = Path.home() / ".amplifier" / "email_drafts_sync_state.json"
REMINDERS_LIST = "Email Follow-up"


def load_state() -> dict:
    """Load sync state from disk."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"drafted_emails": {}, "last_sync": None}


def save_state(state: dict):
    """Save sync state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def run_applescript(script: str) -> str:
    """Execute AppleScript and return result."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.scpt', delete=False) as f:
        f.write(script)
        temp_path = f.name
    
    try:
        result = subprocess.run(
            ['osascript', temp_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    finally:
        os.unlink(temp_path)


def escape_applescript(s: str) -> str:
    """Escape string for AppleScript."""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


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
        match = re.search(r'#inbox/([a-f0-9]+)', link)
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
    title_escaped = escape_applescript(title[:200])  # Limit title length
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


def generate_draft_body(email: dict) -> str:
    """Generate a draft reply body based on the email content."""
    from_name = email.get('from_name', 'there')
    # Clean up quoted names
    if from_name.startswith('"') and from_name.endswith('"'):
        from_name = from_name[1:-1]
    
    # Use first name if available
    first_name = from_name.split()[0] if from_name else "there"
    
    # Simple draft template
    return f"""Hi {first_name},

Thank you for your email. 

[Your response here]

Best,
Joi"""


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
        "errors": []
    }
    
    # Get all starred emails
    if verbose:
        print("Fetching starred emails from Gmail...")
    
    try:
        starred_emails = get_starred(max_results=100)
    except Exception as e:
        results["errors"].append(f"Failed to fetch Gmail: {e}")
        return results
    
    results["starred_count"] = len(starred_emails)
    starred_ids = {email['id'] for email in starred_emails}
    
    if verbose:
        print(f"Found {len(starred_emails)} starred emails")
    
    # Get current reminders
    if verbose:
        print("Checking current reminders...")
    
    reminder_email_ids = get_reminder_email_ids()
    
    if verbose:
        print(f"Found {len(reminder_email_ids)} email reminders")
    
    # Remove reminders for emails that are no longer starred
    for email_id in reminder_email_ids:
        if email_id not in starred_ids:
            if verbose:
                print(f"  Removing reminder for unstarred email: {email_id[:16]}...")
            
            if not dry_run:
                if delete_reminder_by_email_id(email_id):
                    results["removed_reminders"].append(email_id)
                    # Also remove from drafted state
                    if email_id in drafted:
                        del drafted[email_id]
                else:
                    results["errors"].append(f"Failed to delete reminder: {email_id}")
            else:
                results["removed_reminders"].append(email_id)
    
    # Process each starred email
    for email in starred_emails:
        email_id = email['id']
        subject = email.get('subject', '(no subject)')
        from_name = email.get('from_name', 'Unknown')
        
        # Skip if already has reminder
        if email_id in reminder_email_ids and email_id in drafted:
            results["skipped"].append(email_id)
            continue
        
        if verbose:
            print(f"  Processing: {from_name[:20]}: {subject[:40]}...")
        
        # Create draft if needed
        draft_link = drafted.get(email_id, {}).get("draft_link")
        
        if not draft_link:
            if verbose:
                print(f"    Creating draft reply...")
            
            if not dry_run:
                try:
                    draft_body = generate_draft_body(email)
                    draft_result = create_draft(
                        to=email['from_email'],
                        subject=f"Re: {subject}",
                        body=draft_body,
                        reply_to_id=email_id
                    )
                    draft_link = draft_result['link']
                    
                    # Save to state
                    drafted[email_id] = {
                        "draft_link": draft_link,
                        "draft_id": draft_result['id'],
                        "created": datetime.now().isoformat(),
                        "subject": subject,
                        "from": email['from_email']
                    }
                    results["new_drafts"].append(email_id)
                    
                except Exception as e:
                    results["errors"].append(f"Failed to create draft for {email_id}: {e}")
                    continue
            else:
                draft_link = "[DRY RUN - would create draft]"
                results["new_drafts"].append(email_id)
        
        # Create reminder if needed
        if email_id not in reminder_email_ids:
            if verbose:
                print(f"    Creating reminder...")
            
            # Clean up from_name
            clean_from = from_name
            if clean_from.startswith('"') and clean_from.endswith('"'):
                clean_from = clean_from[1:-1]
            
            title = f"📧 {clean_from}: {subject[:50]}"
            if len(subject) > 50:
                title += "..."
            
            body = f"""From: {email['from_email']}

Draft: {draft_link}

Gmail: {email['link']}

Preview: {email.get('snippet', '')[:200]}"""
            
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
        for email_id, info in list(drafted.items())[-10:]:
            print(f"  - {info.get('from', 'Unknown')[:30]}: {info.get('subject', 'No subject')[:40]}")


def main():
    parser = argparse.ArgumentParser(description="Sync starred emails to reminders with draft replies")
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--status', action='store_true', help='Show sync status')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    
    args = parser.parse_args()
    
    if args.status:
        print_status()
        return
    
    verbose = not args.quiet
    
    if verbose:
        print("=" * 50)
        print("Email Drafts Sync")
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
        if results['errors']:
            print(f"Errors: {len(results['errors'])}")
            for err in results['errors']:
                print(f"  - {err}")
    
    # Exit with error code if there were errors
    if results['errors']:
        sys.exit(1)


if __name__ == "__main__":
    main()
