#!/usr/bin/env python3
"""
Standalone GTD Morning Routine - works without Amplifier framework.

Runs all GTD tools in sequence:
1. Sync reminders from Apple Reminders via EventKit
2. Sync Notes.app ↔ Obsidian
3. Sync starred emails to Email Replies reminders
4. Sync meeting transcripts from Granola (muesli)
5. Generate GTD Dashboard
6. Generate Daily Note
7. Open Obsidian to GTD Dashboard
"""

import sys
from pathlib import Path

# Add amplifier to path so we can import the gtd modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Now import from the gtd modules (without going through __init__.py which needs amplifier_core)
from amplifier.gtd.morning import morning_routine

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GTD Morning Routine")
    parser.add_argument(
        "--skip-sync", action="store_true", help="Skip reminders and notes sync"
    )
    parser.add_argument(
        "--skip-open", action="store_true", help="Skip opening Obsidian"
    )

    args = parser.parse_args()

    results = morning_routine(skip_sync=args.skip_sync, skip_open=args.skip_open)
    
    # Exit with success if at least the core steps succeeded
    if results.get("dashboard") and results.get("daily_note"):
        sys.exit(0)
    else:
        sys.exit(1)
