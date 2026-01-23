#!/usr/bin/env python3
"""
Notes.app ↔ Obsidian Sync Orchestrator

Bidirectional sync between Mac Notes.app and Obsidian vault.
Only syncs notes in the "Obsidian Sync" folder.

Features:
- Cache freshness tracking
- Timeout handling with partial results
- Progress tracking
"""

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class TimeoutError(Exception):
    """Operation timed out."""

    pass


def normalize_datetime(dt: datetime) -> datetime:
    """Normalize datetime to naive UTC for comparison."""
    if dt.tzinfo is not None:
        # Convert to UTC and remove timezone
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string, handling timezone suffixes."""
    # Handle 'Z' suffix (UTC)
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(dt_str)
        return normalize_datetime(dt)
    except ValueError:
        return datetime.now()


try:
    from .notes_applescript import (
        SYNC_FOLDER_NAME,
        ensure_sync_folder,
        list_notes_in_sync_folder,
        get_note,
        create_note,
        update_note,
        delete_note,
    )
    from .notes_converter import (
        html_to_markdown,
        markdown_to_html,
        title_to_filename,
        filename_to_title,
        add_frontmatter,
        parse_frontmatter,
    )
    from .notes_state import SyncState
except ImportError:
    from notes_applescript import (
        SYNC_FOLDER_NAME,
        ensure_sync_folder,
        list_notes_in_sync_folder,
        get_note,
        create_note,
        update_note,
        delete_note,
    )
    from notes_converter import (
        html_to_markdown,
        markdown_to_html,
        title_to_filename,
        filename_to_title,
        add_frontmatter,
        parse_frontmatter,
    )
    from notes_state import SyncState


DEFAULT_OBSIDIAN_SYNC_DIR = Path.home() / "switchboard" / "notes-sync"


def get_notes_cache_info(obsidian_sync_dir: Optional[Path] = None) -> dict:
    """Get notes sync cache metadata including freshness."""
    if obsidian_sync_dir is None:
        obsidian_sync_dir = DEFAULT_OBSIDIAN_SYNC_DIR

    obsidian_sync_dir = Path(os.path.expanduser(str(obsidian_sync_dir)))
    state_file = obsidian_sync_dir / ".sync-state.json"

    if not state_file.exists():
        return {
            "exists": False,
            "cache_age_seconds": None,
            "cache_age_human": "never synced",
            "is_stale": True,
            "last_sync_at": None,
        }

    try:
        with open(state_file) as f:
            state = json.load(f)

        last_sync = state.get("lastSyncAt")
        if last_sync:
            last_sync_time = datetime.fromisoformat(last_sync)
            age_seconds = int((datetime.now() - last_sync_time).total_seconds())
        else:
            age_seconds = None

        # Consider cache stale after 1 hour
        is_stale = age_seconds is None or age_seconds > 3600

        # Human-readable age
        if age_seconds is None:
            age_human = "unknown"
        elif age_seconds < 60:
            age_human = f"{age_seconds}s ago"
        elif age_seconds < 3600:
            age_human = f"{age_seconds // 60}m ago"
        elif age_seconds < 86400:
            age_human = f"{age_seconds // 3600}h ago"
        else:
            age_human = f"{age_seconds // 86400}d ago"

        return {
            "exists": True,
            "cache_age_seconds": age_seconds,
            "cache_age_human": age_human,
            "is_stale": is_stale,
            "last_sync_at": last_sync,
            "tracked_count": state.get("totalTracked", len(state.get("notes", {}))),
        }
    except Exception as e:
        return {
            "exists": True,
            "error": str(e),
            "cache_age_seconds": None,
            "cache_age_human": "error reading state",
            "is_stale": True,
            "last_sync_at": None,
        }


class NotesSync:
    """Notes Sync Manager with timeout handling."""

    def __init__(self, obsidian_sync_dir: Optional[Path] = None):
        self.obsidian_sync_dir = Path(
            os.path.expanduser(str(obsidian_sync_dir or DEFAULT_OBSIDIAN_SYNC_DIR))
        )
        self.state = SyncState(self.obsidian_sync_dir)

    def initialize(self) -> dict:
        """Initialize sync (first-time setup)."""
        # Ensure Obsidian sync directory exists
        if not self.obsidian_sync_dir.exists():
            self.obsidian_sync_dir.mkdir(parents=True)
            print(f"Created Obsidian sync folder: {self.obsidian_sync_dir}")

        # Ensure Notes.app sync folder exists
        ensure_sync_folder()
        print(f'Ensured Notes.app folder: "{SYNC_FOLDER_NAME}"')

        # Initialize state if not already done
        if not self.state.state_file.exists():
            self.state.initialize()
            print("Initialized sync state")

        return {
            "obsidian_dir": str(self.obsidian_sync_dir),
            "notes_folder": SYNC_FOLDER_NAME,
            "enabled_since": self.state.get_enabled_since().isoformat(),
        }

    def pull_from_notes(self, max_timeout: int = 120, progress_callback=None) -> dict:
        """Pull changes from Notes.app to Obsidian with timeout handling."""
        start_time = time.time()

        results = {
            "created": [],
            "updated": [],
            "deleted": [],
            "unchanged": [],
            "errors": [],
            "timed_out": False,
        }

        # Get all notes in sync folder
        try:
            notes_in_folder = list_notes_in_sync_folder()
        except Exception as e:
            results["errors"].append({"operation": "list_notes", "error": str(e)})
            return results

        tracked_notes = self.state.get_all_tracked()
        seen_note_ids = set()
        processed = 0

        for note_meta in notes_in_folder:
            # Check timeout
            if time.time() - start_time > max_timeout:
                results["timed_out"] = True
                results["errors"].append(
                    {
                        "operation": "pull",
                        "error": f"Timed out after {max_timeout}s, processed {processed}/{len(notes_in_folder)} notes",
                    }
                )
                break

            note_id = note_meta["id"]
            seen_note_ids.add(note_id)

            try:
                tracked = self.state.get_note_state(note_id)

                if not tracked:
                    # New note - create in Obsidian
                    full_note = get_note(note_id)
                    markdown = html_to_markdown(full_note["body"])
                    filename = f"{title_to_filename(full_note['name'])}.md"
                    obsidian_path = self.obsidian_sync_dir / filename

                    # Add frontmatter with metadata
                    content = add_frontmatter(
                        markdown,
                        {
                            "title": full_note["name"],
                            "created": full_note["created_at"].isoformat(),
                            "modified": full_note["modified_at"].isoformat(),
                            "notes_id": full_note["id"],
                        },
                    )

                    with open(obsidian_path, "w") as f:
                        f.write(content)

                    mtime = datetime.fromtimestamp(obsidian_path.stat().st_mtime)

                    self.state.track_note(
                        note_id, filename, full_note["modified_at"], mtime
                    )

                    results["created"].append(filename)
                else:
                    # Existing note - check for updates
                    last_notes_modified = parse_iso_datetime(tracked["notesModifiedAt"])
                    current_modified = normalize_datetime(note_meta["modified_at"])

                    if current_modified > last_notes_modified:
                        # Note was updated in Notes.app
                        full_note = get_note(note_id)
                        markdown = html_to_markdown(full_note["body"])
                        obsidian_path = self.obsidian_sync_dir / tracked["obsidianPath"]

                        # Preserve frontmatter, update content
                        content = add_frontmatter(
                            markdown,
                            {
                                "title": full_note["name"],
                                "created": full_note["created_at"].isoformat(),
                                "modified": full_note["modified_at"].isoformat(),
                                "notes_id": full_note["id"],
                            },
                        )

                        with open(obsidian_path, "w") as f:
                            f.write(content)

                        mtime = datetime.fromtimestamp(obsidian_path.stat().st_mtime)

                        self.state.update_sync_time(
                            note_id, full_note["modified_at"], mtime
                        )

                        results["updated"].append(tracked["obsidianPath"])
                    else:
                        results["unchanged"].append(tracked["obsidianPath"])

            except Exception as e:
                results["errors"].append(
                    {
                        "note_id": note_id,
                        "name": note_meta.get("name", "Unknown"),
                        "error": str(e),
                    }
                )

            processed += 1
            if progress_callback:
                progress_callback("pull", processed, len(notes_in_folder))

        # Check for deleted notes (in state but not in Notes.app) - only if we didn't timeout
        if not results["timed_out"]:
            for note_id, info in tracked_notes.items():
                if note_id not in seen_note_ids:
                    # Note was deleted from Notes.app - remove from Obsidian
                    obsidian_path = self.obsidian_sync_dir / info["obsidianPath"]
                    if obsidian_path.exists():
                        # Move to trash folder instead of deleting
                        trash_dir = self.obsidian_sync_dir / ".trash"
                        trash_dir.mkdir(exist_ok=True)
                        trash_path = trash_dir / info["obsidianPath"]
                        shutil.move(str(obsidian_path), str(trash_path))
                        results["deleted"].append(info["obsidianPath"])
                    self.state.untrack_note(note_id)

        return results

    def push_to_notes(self, max_timeout: int = 120, progress_callback=None) -> dict:
        """Push changes from Obsidian to Notes.app with timeout handling."""
        start_time = time.time()

        results = {
            "created": [],
            "updated": [],
            "deleted": [],
            "unchanged": [],
            "errors": [],
            "timed_out": False,
        }

        # Get all markdown files in sync folder
        try:
            obsidian_files = [
                f.name
                for f in self.obsidian_sync_dir.iterdir()
                if f.suffix == ".md" and not f.name.startswith(".")
            ]
        except Exception as e:
            results["errors"].append({"operation": "list_files", "error": str(e)})
            return results

        tracked_notes = self.state.get_all_tracked()
        seen_paths = set()
        processed = 0

        for filename in obsidian_files:
            # Check timeout
            if time.time() - start_time > max_timeout:
                results["timed_out"] = True
                results["errors"].append(
                    {
                        "operation": "push",
                        "error": f"Timed out after {max_timeout}s, processed {processed}/{len(obsidian_files)} files",
                    }
                )
                break

            seen_paths.add(filename)
            obsidian_path = self.obsidian_sync_dir / filename

            try:
                stat = obsidian_path.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                note_id = self.state.find_note_id_by_path(filename)

                if not note_id:
                    # New file in Obsidian - create in Notes.app
                    with open(obsidian_path) as f:
                        content = f.read()

                    frontmatter, body = parse_frontmatter(content)
                    title = frontmatter.get("title") or filename_to_title(filename)
                    html = markdown_to_html(body)

                    new_note_id = create_note(title, html)

                    # Get the created note to get accurate timestamps
                    created_note = get_note(new_note_id)

                    self.state.track_note(
                        new_note_id, filename, created_note["modified_at"], mtime
                    )

                    results["created"].append(filename)
                else:
                    # Existing file - check for updates
                    tracked = self.state.get_note_state(note_id)
                    if not tracked:
                        continue
                    last_obsidian_mtime = parse_iso_datetime(tracked["obsidianMtime"])
                    current_mtime = normalize_datetime(mtime)

                    if current_mtime > last_obsidian_mtime:
                        # File was updated in Obsidian
                        with open(obsidian_path) as f:
                            content = f.read()

                        frontmatter, body = parse_frontmatter(content)
                        title = frontmatter.get("title") or filename_to_title(filename)
                        html = markdown_to_html(body)

                        update_note(note_id, title, html)

                        # Get updated note for accurate timestamp
                        updated_note = get_note(note_id)

                        self.state.update_sync_time(
                            note_id, updated_note["modified_at"], mtime
                        )

                        results["updated"].append(filename)
                    else:
                        results["unchanged"].append(filename)

            except Exception as e:
                results["errors"].append({"file": filename, "error": str(e)})

            processed += 1
            if progress_callback:
                progress_callback("push", processed, len(obsidian_files))

        # Check for deleted files (in state but not in Obsidian) - only if we didn't timeout
        if not results["timed_out"]:
            for note_id, info in tracked_notes.items():
                if info["obsidianPath"] not in seen_paths:
                    # File was deleted from Obsidian - delete from Notes.app
                    try:
                        delete_note(note_id)
                        results["deleted"].append(info["obsidianPath"])
                    except Exception as e:
                        results["errors"].append(
                            {
                                "note_id": note_id,
                                "file": info["obsidianPath"],
                                "error": str(e),
                            }
                        )
                    self.state.untrack_note(note_id)

        return results

    def sync(self, max_timeout: int = 240, progress_callback=None) -> dict:
        """Full bidirectional sync. Pull first (Notes.app wins for conflicts), then push."""
        start_time = time.time()
        print("Starting Notes.app ↔ Obsidian sync...")

        # Ensure folders exist
        self.initialize()

        # Calculate time budget for each phase
        pull_timeout = max_timeout // 2

        # Pull from Notes.app first
        print("Pulling from Notes.app...")
        pull_results = self.pull_from_notes(
            max_timeout=pull_timeout, progress_callback=progress_callback
        )

        # Calculate remaining time for push
        elapsed = time.time() - start_time
        push_timeout = max(30, max_timeout - int(elapsed))

        # Push to Notes.app
        print("Pushing to Notes.app...")
        push_results = self.push_to_notes(
            max_timeout=push_timeout, progress_callback=progress_callback
        )

        # Update last sync time in state
        self.state.update_last_sync()

        total_elapsed = time.time() - start_time

        return {
            "pull": pull_results,
            "push": push_results,
            "summary": {
                "total_created": len(pull_results["created"])
                + len(push_results["created"]),
                "total_updated": len(pull_results["updated"])
                + len(push_results["updated"]),
                "total_deleted": len(pull_results["deleted"])
                + len(push_results["deleted"]),
                "total_errors": len(pull_results["errors"])
                + len(push_results["errors"]),
                "partial": pull_results.get("timed_out", False)
                or push_results.get("timed_out", False),
                "elapsed_seconds": total_elapsed,
            },
            "synced_at": datetime.now().isoformat(),
        }

    def get_status(self) -> dict:
        """Get sync status with cache freshness info."""
        stats = self.state.get_stats()

        try:
            notes_in_folder = list_notes_in_sync_folder()
            notes_count = len(notes_in_folder)
        except Exception:
            notes_count = "error"

        cache_info = get_notes_cache_info(self.obsidian_sync_dir)

        return {
            "enabled_since": stats["enabledSince"],
            "tracked_notes": stats["totalTracked"],
            "notes_in_sync_folder": notes_count,
            "obsidian_sync_dir": str(self.obsidian_sync_dir),
            "notes_folder_name": SYNC_FOLDER_NAME,
            "cache_age_seconds": cache_info.get("cache_age_seconds"),
            "cache_age_human": cache_info.get("cache_age_human"),
            "is_stale": cache_info.get("is_stale", True),
            "last_sync_at": cache_info.get("last_sync_at"),
        }


def main():
    """CLI entry point."""
    import sys

    syncer = NotesSync()

    if len(sys.argv) < 2:
        print("Usage: python notes_sync.py [sync|pull|push|status|init]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "sync":
        results = syncer.sync()
        print("\n✅ Sync complete!")
        print(f"   Created: {results['summary']['total_created']}")
        print(f"   Updated: {results['summary']['total_updated']}")
        print(f"   Deleted: {results['summary']['total_deleted']}")
        if results["summary"]["total_errors"] > 0:
            print(f"   Errors: {results['summary']['total_errors']}")
        if results["summary"].get("partial"):
            print("   ⚠️  Partial sync (timed out)")

    elif cmd == "pull":
        syncer.initialize()
        results = syncer.pull_from_notes()
        print("\n✅ Pull complete!")
        print(f"   Created: {len(results['created'])}")
        print(f"   Updated: {len(results['updated'])}")

    elif cmd == "push":
        syncer.initialize()
        results = syncer.push_to_notes()
        print("\n✅ Push complete!")
        print(f"   Created: {len(results['created'])}")
        print(f"   Updated: {len(results['updated'])}")

    elif cmd == "status":
        status = syncer.get_status()
        print("\n📊 Notes Sync Status")
        print(f"   Enabled since: {status['enabled_since']}")
        print(f"   Tracked notes: {status['tracked_notes']}")
        print(f"   Notes in folder: {status['notes_in_sync_folder']}")
        print(f"   Last sync: {status['cache_age_human']}")
        if status["is_stale"]:
            print("   ⚠️  Cache is stale")
        print(f"   Obsidian dir: {status['obsidian_sync_dir']}")

    elif cmd == "init":
        info = syncer.initialize()
        print("\n✅ Initialized!")
        print(f"   Obsidian: {info['obsidian_dir']}")
        print(f"   Notes.app: {info['notes_folder']}")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
