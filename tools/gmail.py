#!/usr/bin/env python3
"""
Gmail Tool - Extract flagged emails, create actionable tasks, draft responses.

Uses Google Gmail API to interact with Gmail.

Usage:
    # Get starred/flagged emails
    python gmail.py starred
    python gmail.py starred --json
    
    # Get emails needing response (sent to me, no reply yet)
    python gmail.py needs-response
    python gmail.py needs-response --days 7
    
    # Search emails
    python gmail.py search "from:someone@example.com"
    python gmail.py search "is:starred label:action-required"
    
    # Get email details (for drafting response)
    python gmail.py get <message_id>
    
    # Create draft response
    python gmail.py draft <message_id> --body "Thanks for..."
    
    # Sync starred emails to Apple Reminders
    python gmail.py sync-to-reminders
    python gmail.py sync-to-reminders --list "Email Follow-up"

Environment:
    GMAIL_CREDS_PATH: Path to credentials.json
    GMAIL_TOKEN_PATH: Path to token.json (will be created on first auth)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("Error: Google API libraries not installed.")
    print("Install with: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)


# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
]

# Default paths
DEFAULT_CREDS_PATH = os.path.expanduser("~/.cache/amplifier/google-hydrated/credentials.json")
DEFAULT_TOKEN_PATH = os.path.expanduser("~/.cache/amplifier/google-hydrated/gmail_token.json")


def get_credentials() -> Credentials:
    """Get or refresh Gmail API credentials."""
    creds_path = os.environ.get("GMAIL_CREDS_PATH", DEFAULT_CREDS_PATH)
    token_path = os.environ.get("GMAIL_TOKEN_PATH", DEFAULT_TOKEN_PATH)
    
    creds = None
    
    # Load existing token
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(f"Credentials file not found: {creds_path}")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
    
    return creds


def get_gmail_service():
    """Build Gmail API service."""
    creds = get_credentials()
    return build('gmail', 'v1', credentials=creds)


def gmail_link(message_id: str) -> str:
    """Generate a clickable Gmail deep link for a message ID."""
    # Gmail web URL format
    return f"https://mail.google.com/mail/u/0/#inbox/{message_id}"


def parse_email_address(addr: str) -> tuple[str, str]:
    """Parse 'Name <email>' format, return (name, email)."""
    match = re.match(r'^(.+?)\s*<([^>]+)>$', addr)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return addr, addr


def extract_headers(headers: list, *names: str) -> dict:
    """Extract specific headers from message headers list."""
    result = {}
    names_lower = [n.lower() for n in names]
    for h in headers:
        if h['name'].lower() in names_lower:
            result[h['name'].lower()] = h['value']
    return result


def format_message(msg: dict, include_body: bool = False) -> dict:
    """Format a Gmail message for output."""
    headers = extract_headers(
        msg.get('payload', {}).get('headers', []),
        'From', 'To', 'Subject', 'Date'
    )
    
    from_name, from_email = parse_email_address(headers.get('from', ''))
    
    result = {
        'id': msg['id'],
        'thread_id': msg['threadId'],
        'link': gmail_link(msg['id']),
        'from_name': from_name,
        'from_email': from_email,
        'to': headers.get('to', ''),
        'subject': headers.get('subject', '(no subject)'),
        'date': headers.get('date', ''),
        'snippet': msg.get('snippet', ''),
        'labels': msg.get('labelIds', []),
    }
    
    if include_body:
        result['body'] = extract_body(msg)
    
    return result


def extract_body(msg: dict) -> str:
    """Extract plain text body from message."""
    payload = msg.get('payload', {})
    
    # Simple message
    if payload.get('body', {}).get('data'):
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
    
    # Multipart message - find text/plain
    parts = payload.get('parts', [])
    for part in parts:
        if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
    
    # Fallback to first part with data
    for part in parts:
        if part.get('body', {}).get('data'):
            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
    
    return ''


def get_starred(max_results: int = 50) -> list[dict]:
    """Get starred/flagged emails."""
    service = get_gmail_service()
    
    results = service.users().messages().list(
        userId='me',
        q='is:starred',
        maxResults=max_results
    ).execute()
    
    messages = []
    for msg_ref in results.get('messages', []):
        msg = service.users().messages().get(
            userId='me',
            id=msg_ref['id'],
            format='full'
        ).execute()
        messages.append(format_message(msg))
    
    return messages


def get_needs_response(days: int = 7, max_results: int = 50) -> list[dict]:
    """Get emails that may need a response (sent to me, I haven't replied)."""
    service = get_gmail_service()
    
    # Emails in inbox, not from me, older than 1 day
    after_date = (datetime.now() - timedelta(days=days)).strftime('%Y/%m/%d')
    query = f'in:inbox -from:me after:{after_date}'
    
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results
    ).execute()
    
    messages = []
    for msg_ref in results.get('messages', []):
        msg = service.users().messages().get(
            userId='me',
            id=msg_ref['id'],
            format='full'
        ).execute()
        
        # Check if I've replied to this thread
        thread = service.users().threads().get(
            userId='me',
            id=msg['threadId']
        ).execute()
        
        my_replies = [
            m for m in thread.get('messages', [])
            if 'SENT' in m.get('labelIds', [])
        ]
        
        # Only include if I haven't replied
        if not my_replies:
            messages.append(format_message(msg))
    
    return messages


def search_emails(query: str, max_results: int = 50) -> list[dict]:
    """Search emails with Gmail query syntax."""
    service = get_gmail_service()
    
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results
    ).execute()
    
    messages = []
    for msg_ref in results.get('messages', []):
        msg = service.users().messages().get(
            userId='me',
            id=msg_ref['id'],
            format='full'
        ).execute()
        messages.append(format_message(msg))
    
    return messages


def get_message(message_id: str, include_body: bool = True) -> dict:
    """Get a single message by ID."""
    service = get_gmail_service()
    
    msg = service.users().messages().get(
        userId='me',
        id=message_id,
        format='full'
    ).execute()
    
    return format_message(msg, include_body=include_body)


def create_draft(to: str, subject: str, body: str, reply_to_id: Optional[str] = None) -> dict:
    """Create a draft email."""
    service = get_gmail_service()
    
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    draft_body = {'message': {'raw': raw}}
    
    if reply_to_id:
        # Get original message for threading
        original = service.users().messages().get(
            userId='me',
            id=reply_to_id,
            format='metadata',
            metadataHeaders=['Message-ID', 'References']
        ).execute()
        
        headers = extract_headers(original.get('payload', {}).get('headers', []), 'message-id', 'references')
        
        draft_body['message']['threadId'] = original['threadId']
        # Add In-Reply-To and References headers for proper threading
    
    draft = service.users().drafts().create(
        userId='me',
        body=draft_body
    ).execute()
    
    return {
        'id': draft['id'],
        'message_id': draft['message']['id'],
        'link': f"https://mail.google.com/mail/u/0/#drafts/{draft['message']['id']}"
    }


def sync_starred_to_reminders(list_name: str = "Email Follow-up") -> dict:
    """Sync starred emails to Apple Reminders."""
    starred = get_starred()
    
    # Path to apple_reminders.py
    reminders_tool = Path(__file__).parent / "apple_reminders.py"
    
    created = []
    skipped = []
    
    for email in starred:
        # Create reminder title with sender and subject
        title = f"📧 {email['from_name']}: {email['subject'][:50]}"
        if len(email['subject']) > 50:
            title += "..."
        
        # Notes include the clickable link and snippet
        notes = f"From: {email['from_email']}\n\nLink: {email['link']}\n\n{email['snippet']}"
        
        # Check if reminder already exists (by searching for the link)
        try:
            search_result = subprocess.run(
                [sys.executable, str(reminders_tool), "search", email['link']],
                capture_output=True, text=True
            )
            if email['link'] in search_result.stdout:
                skipped.append({'id': email['id'], 'reason': 'already exists'})
                continue
        except Exception:
            pass  # If search fails, try to create anyway
        
        # Create the reminder
        try:
            result = subprocess.run(
                [
                    sys.executable, str(reminders_tool), "add",
                    title,
                    "--list", list_name,
                    "--notes", notes
                ],
                capture_output=True, text=True, check=True
            )
            created.append({
                'email_id': email['id'],
                'subject': email['subject'],
                'from': email['from_email']
            })
        except subprocess.CalledProcessError as e:
            skipped.append({'id': email['id'], 'reason': str(e)})
    
    return {
        'created': len(created),
        'skipped': len(skipped),
        'details': {
            'created': created,
            'skipped': skipped
        }
    }


def format_for_display(messages: list[dict]) -> str:
    """Format messages for human-readable display."""
    if not messages:
        return "No messages found."
    
    lines = []
    for i, msg in enumerate(messages, 1):
        lines.append(f"\n{i}. {msg['subject']}")
        lines.append(f"   From: {msg['from_name']} <{msg['from_email']}>")
        lines.append(f"   Date: {msg['date']}")
        lines.append(f"   Link: {msg['link']}")
        if msg.get('snippet'):
            snippet = msg['snippet'][:100] + "..." if len(msg['snippet']) > 100 else msg['snippet']
            lines.append(f"   Preview: {snippet}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Gmail Tool - Manage emails for GTD")
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # starred
    starred_parser = subparsers.add_parser('starred', help='Get starred emails')
    starred_parser.add_argument('--max', type=int, default=50, help='Max results')
    starred_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # needs-response
    needs_parser = subparsers.add_parser('needs-response', help='Get emails needing response')
    needs_parser.add_argument('--days', type=int, default=7, help='Look back N days')
    needs_parser.add_argument('--max', type=int, default=50, help='Max results')
    needs_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # search
    search_parser = subparsers.add_parser('search', help='Search emails')
    search_parser.add_argument('query', help='Gmail search query')
    search_parser.add_argument('--max', type=int, default=50, help='Max results')
    search_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # get
    get_parser = subparsers.add_parser('get', help='Get a single message')
    get_parser.add_argument('message_id', help='Message ID')
    get_parser.add_argument('--body', action='store_true', help='Include body')
    get_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # draft
    draft_parser = subparsers.add_parser('draft', help='Create a draft reply')
    draft_parser.add_argument('message_id', help='Message ID to reply to')
    draft_parser.add_argument('--body', required=True, help='Draft body text')
    draft_parser.add_argument('--subject', help='Override subject (default: Re: original)')
    draft_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # sync-to-reminders
    sync_parser = subparsers.add_parser('sync-to-reminders', help='Sync starred to Reminders')
    sync_parser.add_argument('--list', default='Email Follow-up', help='Reminders list name')
    sync_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'starred':
            result = get_starred(args.max)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(format_for_display(result))
        
        elif args.command == 'needs-response':
            result = get_needs_response(args.days, args.max)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(format_for_display(result))
        
        elif args.command == 'search':
            result = search_emails(args.query, args.max)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(format_for_display(result))
        
        elif args.command == 'get':
            result = get_message(args.message_id, include_body=args.body)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Subject: {result['subject']}")
                print(f"From: {result['from_name']} <{result['from_email']}>")
                print(f"Date: {result['date']}")
                print(f"Link: {result['link']}")
                if result.get('body'):
                    print(f"\n--- Body ---\n{result['body']}")
        
        elif args.command == 'draft':
            # Get original message for reply
            original = get_message(args.message_id)
            subject = args.subject or f"Re: {original['subject']}"
            to = original['from_email']
            
            result = create_draft(to, subject, args.body, args.message_id)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Draft created: {result['link']}")
        
        elif args.command == 'sync-to-reminders':
            result = sync_starred_to_reminders(args.list)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Created {result['created']} reminders, skipped {result['skipped']}")
                for item in result['details']['created']:
                    print(f"  + {item['subject'][:50]}")
        
        else:
            parser.print_help()
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
