#!/usr/bin/env python3
"""
Kimono Sync - Sync calendar events to kimono preparation spreadsheet.

Scans Google Calendar for kimono-related events and syncs them to the
kimono tracking spreadsheet.

Usage:
    # Preview what would be synced (dry run)
    python kimono_sync.py preview
    
    # Sync calendar events to spreadsheet
    python kimono_sync.py sync
    
    # Show current spreadsheet contents
    python kimono_sync.py list

Environment:
    GCAL_CREDS_PATH: Path to credentials.json
    GCAL_TOKEN_PATH: Path to calendar token.json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("Error: Google API libraries not installed.")
    print("Install with: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)


# Scopes needed
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Kimono spreadsheet
SPREADSHEET_ID = "1hOwDgfhrLkeJzUmEWoUlH63l7q54cH9vCvQRSt5b--Q"
SHEET_RANGE = "Sheet1!A:D"  # Date, Event, Location, Style

# Default paths
DEFAULT_CREDS_PATH = os.path.expanduser("~/.cache/amplifier/google-hydrated/credentials.json")
DEFAULT_CAL_TOKEN_PATH = os.path.expanduser("~/.cache/amplifier/google-hydrated/calendar_token.json")
DEFAULT_SHEETS_TOKEN_PATH = os.path.expanduser("~/.cache/amplifier/google-hydrated/sheets_token.json")

# Only explicit #kimono tag - no inference from event titles
# The hand-curated spreadsheet is ground truth
KIMONO_TAG = r'#kimono'


def get_calendar_credentials() -> Credentials:
    """Get Google Calendar credentials."""
    creds_path = os.environ.get("GCAL_CREDS_PATH", DEFAULT_CREDS_PATH)
    token_path = os.environ.get("GCAL_TOKEN_PATH", DEFAULT_CAL_TOKEN_PATH)
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, CALENDAR_SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, CALENDAR_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
    
    return creds


def get_sheets_credentials() -> Credentials:
    """Get Google Sheets credentials."""
    creds_path = os.environ.get("GCAL_CREDS_PATH", DEFAULT_CREDS_PATH)
    token_path = DEFAULT_SHEETS_TOKEN_PATH
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SHEETS_SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SHEETS_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
    
    return creds


def is_kimono_event(event: dict) -> bool:
    """Check if event has explicit #kimono tag."""
    text = event.get('summary', '') + ' ' + event.get('description', '')
    return bool(re.search(KIMONO_TAG, text, re.IGNORECASE))


def extract_location(event: dict) -> str:
    """Extract location, defaulting to 東京."""
    location = event.get('location', '')
    
    # Try to extract city
    if '京都' in location:
        return '京都'
    elif '大阪' in location:
        return '大阪'
    elif '千葉' in location:
        return '千葉'
    elif '東京' in location or not location:
        return '東京'
    
    # Return first part of location if comma-separated
    return location.split(',')[0].strip() or '東京'


def parse_event_date(event: dict) -> str:
    """Parse event date to YYYY/M/D format."""
    start = event.get('start', {})
    date_str = start.get('date') or start.get('dateTime', '')[:10]
    
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return f"{dt.year}/{dt.month}/{dt.day}"
    except ValueError:
        return date_str


def get_calendar_events(days_ahead: int = 365) -> list:
    """Get calendar events for the next N days."""
    creds = get_calendar_credentials()
    service = build('calendar', 'v3', credentials=creds)
    
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
    
    events = []
    page_token = None
    
    while True:
        result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=500,
            singleEvents=True,
            orderBy='startTime',
            pageToken=page_token
        ).execute()
        
        events.extend(result.get('items', []))
        page_token = result.get('nextPageToken')
        
        if not page_token:
            break
    
    return events


def get_kimono_events(days_ahead: int = 365) -> list:
    """Get kimono-related events from calendar."""
    all_events = get_calendar_events(days_ahead)
    
    kimono_events = []
    for event in all_events:
        if is_kimono_event(event):
            kimono_events.append({
                'date': parse_event_date(event),
                'event': event.get('summary', '').replace('#kimono', '').strip(),
                'location': extract_location(event),
                'style': '',  # User fills in manually
            })
    
    return kimono_events


def get_spreadsheet_events() -> list:
    """Get current events from the spreadsheet."""
    creds = get_sheets_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=SHEET_RANGE
    ).execute()
    
    rows = result.get('values', [])
    
    if not rows:
        return []
    
    # Skip header
    events = []
    for row in rows[1:]:
        if len(row) >= 2:
            events.append({
                'date': row[0] if len(row) > 0 else '',
                'event': row[1] if len(row) > 1 else '',
                'location': row[2] if len(row) > 2 else '',
                'style': row[3] if len(row) > 3 else '',
            })
    
    return events


def sync_to_spreadsheet(new_events: list, existing_events: list) -> dict:
    """Sync new events to spreadsheet, preserving existing style info."""
    creds = get_sheets_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
    # Create lookup of existing events by date+event
    existing_lookup = {}
    for e in existing_events:
        key = f"{e['date']}|{e['event']}"
        existing_lookup[key] = e
    
    # Merge: keep existing style, add new events
    merged = []
    seen_keys = set()
    
    # First add all existing events (preserving style)
    for e in existing_events:
        key = f"{e['date']}|{e['event']}"
        merged.append(e)
        seen_keys.add(key)
    
    # Add new events not already in spreadsheet
    added = []
    for e in new_events:
        key = f"{e['date']}|{e['event']}"
        if key not in seen_keys:
            merged.append(e)
            added.append(e)
            seen_keys.add(key)
    
    # Sort by date
    def parse_date(d):
        try:
            parts = d['date'].split('/')
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except:
            return (9999, 12, 31)
    
    merged.sort(key=parse_date)
    
    # Convert to rows
    rows = [['Date', 'Event', 'Location', 'Style']]  # Header
    for e in merged:
        rows.append([e['date'], e['event'], e['location'], e['style']])
    
    # Update spreadsheet
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1!A1",
        valueInputOption='RAW',
        body={'values': rows}
    ).execute()
    
    return {
        'total': len(merged),
        'added': len(added),
        'added_events': added
    }


def main():
    parser = argparse.ArgumentParser(description="Sync kimono events to spreadsheet")
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # preview
    preview_parser = subparsers.add_parser('preview', help='Preview calendar kimono events')
    preview_parser.add_argument('--days', type=int, default=365, help='Days ahead to scan')
    
    # sync
    sync_parser = subparsers.add_parser('sync', help='Sync to spreadsheet')
    sync_parser.add_argument('--days', type=int, default=365, help='Days ahead to scan')
    
    # list
    list_parser = subparsers.add_parser('list', help='Show current spreadsheet')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'preview':
            events = get_kimono_events(args.days)
            print(f"Found {len(events)} kimono events in calendar:\n")
            for e in events:
                print(f"  {e['date']:12} {e['event'][:30]:32} {e['location']}")
        
        elif args.command == 'sync':
            print("Fetching calendar events...")
            cal_events = get_kimono_events(args.days)
            
            print("Fetching spreadsheet...")
            sheet_events = get_spreadsheet_events()
            
            print("Syncing...")
            result = sync_to_spreadsheet(cal_events, sheet_events)
            
            print(f"\nSync complete:")
            print(f"  Total events: {result['total']}")
            print(f"  Added: {result['added']}")
            
            if result['added_events']:
                print("\nNewly added:")
                for e in result['added_events']:
                    print(f"  {e['date']:12} {e['event']}")
        
        elif args.command == 'list':
            events = get_spreadsheet_events()
            print(f"Kimono spreadsheet ({len(events)} events):\n")
            print(f"{'Date':12} {'Event':32} {'Location':10} Style")
            print("-" * 70)
            for e in events:
                print(f"{e['date']:12} {e['event'][:30]:32} {e['location']:10} {e['style']}")
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
