#!/usr/bin/env python3
"""
Morning Routine - Unified GTD startup for the day.

Runs all GTD tools in sequence:
1. Sync reminders from Apple Reminders
2. Sync Notes.app ↔ Obsidian
3. Sync starred emails to Email Replies reminders
4. Generate GTD Dashboard
5. Generate Daily Note
6. Open Obsidian to GTD Dashboard
"""

import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Use relative imports (preferred within a package)
from .daily_note import DailyNoteGenerator
from .dashboard import GTDDashboard
from .email_sync import sync_emails_to_reminders
from .muesli import sync_and_inject as muesli_sync_and_inject
from .notes_sync import NotesSync


def run_command(cmd: list[str], description: str, cwd: Optional[str] = None) -> bool:
    """Run a command with nice output."""
    print(f"\n📦 {description}...")
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            # Show first few lines of output
            output = result.stdout.strip()
            if output:
                for line in output.split("\n")[:3]:
                    print(f"   {line}")
            print("   ✓ Done")
            return True
        else:
            print(f"   ✗ Failed: {result.stderr[:100]}")
            return False
    except subprocess.TimeoutExpired:
        print("   ✗ Timeout")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def sync_reminders() -> bool:
    """Sync reminders from Apple Reminders using existing JS tool."""
    obs_dailynotes = Path.home() / "obs-dailynotes"
    if not obs_dailynotes.exists():
        print("   ⚠ obs-dailynotes not found, skipping reminders sync")
        return False

    return run_command(
        ["npm", "run", "reminders:update-cache"],
        "Updating reminders cache from Apple Reminders",
        cwd=str(obs_dailynotes),
    )


def sync_notes() -> bool:
    """Sync Notes.app ↔ Obsidian using Python implementation."""
    print("\n📝 Syncing Notes.app with Obsidian...")
    try:
        syncer = NotesSync()
        results = syncer.sync()
        summary = results["summary"]
        print(
            f"   Created: {summary['total_created']}, Updated: {summary['total_updated']}"
        )
        if summary["total_errors"] > 0:
            print(f"   Errors: {summary['total_errors']}")
        print("   ✓ Done")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def sync_emails() -> bool:
    """Sync starred Gmail emails to Email Replies reminder list."""
    print("\n📧 Syncing starred emails to reminders...")
    try:
        result = sync_emails_to_reminders(dry_run=False)
        if result.get("success"):
            created = result.get("reminders_created", 0)
            skipped = result.get("skipped_existing", 0) + result.get("skipped_imported", 0)
            print(f"   Created: {created}, Skipped: {skipped}")
            print("   ✓ Done")
            return True
        else:
            error = result.get("error", "unknown error")
            print(f"   ✗ Failed: {error}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def generate_dashboard() -> bool:
    """Generate GTD Dashboard."""
    print("\n📊 Generating GTD Dashboard...")
    try:
        dashboard = GTDDashboard()
        path = dashboard.save()
        print(f"   ✓ Done: {path}")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def generate_daily_note() -> bool:
    """Generate today's daily note."""
    print("\n📅 Generating today's daily note...")
    try:
        generator = DailyNoteGenerator()
        path = generator.save()
        print(f"   ✓ Done: {path}")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def open_obsidian() -> bool:
    """Open Obsidian to GTD Dashboard."""
    print("\n🚀 Opening GTD Dashboard in Obsidian...")
    try:
        subprocess.run(
            ["open", "obsidian://open?vault=switchboard&file=GTD%20Dashboard"],
            check=True,
        )
        print("   ✓ Opened")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def sync_muesli_meetings() -> bool:
    """Sync Granola meetings via muesli and inject into daily notes."""
    print("\n🎙️ Syncing Granola meetings (muesli)...")
    try:
        # Sync and inject for yesterday (completed meetings)
        yesterday = datetime.now() - timedelta(days=1)
        result = muesli_sync_and_inject(date=yesterday, generate_summaries=False)

        inject_result = result.get("inject", {})
        if inject_result.get("success"):
            count = inject_result.get("meetings_processed", 0)
            if count > 0:
                print(f"   Injected {count} meeting(s) into yesterday's note")
            else:
                print("   No meetings to inject for yesterday")
            print("   ✓ Done")
            return True
        else:
            error = inject_result.get("error", "unknown")
            # "No daily note" for yesterday is not an error
            if "not found" in str(error).lower():
                print("   No daily note for yesterday (OK)")
                return True
            print(f"   ⚠ {error}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def morning_routine(skip_sync: bool = False, skip_open: bool = False):
    """Run the complete morning routine."""
    print("=" * 50)
    print("🌅 GTD Morning Routine")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    results = {}

    # Step 1: Sync reminders (optional)
    if not skip_sync:
        results["reminders"] = sync_reminders()
    else:
        print("\n⏭ Skipping reminders sync")

    # Step 2: Sync notes (optional)
    if not skip_sync:
        results["notes"] = sync_notes()
    else:
        print("\n⏭ Skipping notes sync")

    # Step 3: Sync emails to reminders (optional)
    if not skip_sync:
        results["emails"] = sync_emails()
    else:
        print("\n⏭ Skipping email sync")

    # Step 4: Sync Granola meetings (muesli) - injects into yesterday's note
    if not skip_sync:
        results["muesli"] = sync_muesli_meetings()
    else:
        print("\n⏭ Skipping muesli sync")

    # Step 5: Generate GTD Dashboard
    results["dashboard"] = generate_dashboard()

    # Step 6: Generate Daily Note
    results["daily_note"] = generate_daily_note()

    # Step 7: Open Obsidian (optional)
    if not skip_open:
        results["obsidian"] = open_obsidian()
    else:
        print("\n⏭ Skipping Obsidian open")

    # Summary
    print("\n" + "=" * 50)
    print("✅ Morning routine complete!")
    print("=" * 50)

    successes = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n   {successes}/{total} steps succeeded")

    if results.get("dashboard"):
        print("\n   📋 GTD Dashboard: ~/switchboard/GTD Dashboard.md")
    if results.get("daily_note"):
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"   📅 Daily Note: ~/switchboard/dailynote/{today}.md")

    return results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="GTD Morning Routine")
    parser.add_argument(
        "--skip-sync", action="store_true", help="Skip reminders and notes sync"
    )
    parser.add_argument(
        "--skip-open", action="store_true", help="Skip opening Obsidian"
    )
    parser.add_argument(
        "--dashboard-only", action="store_true", help="Only generate dashboard"
    )
    parser.add_argument(
        "--daily-only", action="store_true", help="Only generate daily note"
    )

    args = parser.parse_args()

    if args.dashboard_only:
        generate_dashboard()
    elif args.daily_only:
        generate_daily_note()
    else:
        morning_routine(skip_sync=args.skip_sync, skip_open=args.skip_open)


if __name__ == "__main__":
    main()
