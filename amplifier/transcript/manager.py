"""
Transcript manager for Claude Code conversation transcripts.

This module provides the TranscriptManager class for managing conversation
transcripts including listing, loading, searching, restoring, and exporting.
"""

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


class TranscriptManager:
    """Manages Claude Code conversation transcripts."""

    def __init__(self):
        self.data_dir = Path(".data")
        self.transcripts_dir = self.data_dir / "transcripts"
        self.sessions_file = self.data_dir / "sessions.json"
        self.current_session = self._get_current_session()

    def _get_current_session(self) -> str | None:
        """Get current session ID from environment or recent activity"""
        # Check if there's a current_session file
        current_session_file = Path(".claude/current_session")
        if current_session_file.exists():
            with open(current_session_file) as f:
                return f.read().strip()

        # Otherwise, find the most recent session from transcripts
        transcripts = self.list_transcripts(last_n=1)
        if transcripts:
            # Extract session ID from filename
            match = re.search(r"compact_\d+_\d+_([a-f0-9-]+)\.txt", transcripts[0].name)
            if match:
                return match.group(1)

        return None

    def list_transcripts(self, last_n: int | None = None) -> list[Path]:
        """List available transcripts, optionally limited to last N"""
        if not self.transcripts_dir.exists():
            return []

        transcripts = sorted(self.transcripts_dir.glob("compact_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)

        if last_n:
            return transcripts[:last_n]
        return transcripts

    def load_transcript_content(self, identifier: str) -> str | None:
        """Load a transcript by session ID or filename and return its content"""
        # Try as direct filename first
        if identifier.endswith(".txt"):
            transcript_path = self.transcripts_dir / identifier
            if transcript_path.exists():
                with open(transcript_path, encoding="utf-8") as f:
                    return f.read()

        # Try to find by session ID
        for transcript_file in self.list_transcripts():
            if identifier in transcript_file.name:
                with open(transcript_file, encoding="utf-8") as f:
                    return f.read()

        return None

    def restore_conversation_lineage(self, session_id: str | None = None) -> str | None:
        """Restore entire conversation lineage by outputting all transcript content"""
        # NOTE: session_id parameter is reserved for future use (e.g., filtering by session)
        # Get all available transcripts
        transcripts = self.list_transcripts()
        if not transcripts:
            return None

        # Sort transcripts by modification time (oldest first) to maintain chronological order
        transcripts_to_process = sorted(transcripts, key=lambda p: p.stat().st_mtime)

        combined_content = []
        sessions_restored = 0

        # Process each transcript file
        for transcript_file in transcripts_to_process:
            if transcript_file.exists():
                with open(transcript_file, encoding="utf-8") as f:
                    content = f.read()

                    # Extract session info from the transcript content if available
                    session_id_match = re.search(r"Session ID:\s*([a-f0-9-]+)", content)
                    session_id_from_content = session_id_match.group(1) if session_id_match else "unknown"

                    # Add separator and content
                    combined_content.append(f"\n{'=' * 80}\n")
                    combined_content.append(f"CONVERSATION SEGMENT {sessions_restored + 1}\n")
                    combined_content.append(f"File: {transcript_file.name}\n")
                    if session_id_from_content != "unknown":
                        combined_content.append(f"Session ID: {session_id_from_content}\n")
                    combined_content.append(f"{'=' * 80}\n\n")
                    combined_content.append(content)
                    sessions_restored += 1

        if not combined_content:
            return None

        return "".join(combined_content)

    def search_transcripts(self, term: str, max_results: int = 10) -> str | None:
        """Search transcripts and output matching content with context"""
        results = []
        for transcript_file in self.list_transcripts():
            try:
                with open(transcript_file, encoding="utf-8") as f:
                    content = f.read()
                    if term.lower() in content.lower():
                        # Extract session ID from filename
                        match = re.search(r"compact_\d+_\d+_([a-f0-9-]+)\.txt", transcript_file.name)
                        session_id = match.group(1) if match else "unknown"

                        # Find all occurrences with context
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if term.lower() in line.lower() and len(results) < max_results:
                                # Get context (5 lines before and after)
                                context_start = max(0, i - 5)
                                context_end = min(len(lines), i + 6)
                                context = "\n".join(lines[context_start:context_end])

                                results.append(
                                    f"\n{'=' * 60}\n"
                                    f"Match in {transcript_file.name} (line {i + 1})\n"
                                    f"Session ID: {session_id}\n"
                                    f"{'=' * 60}\n"
                                    f"{context}\n"
                                )

                                if len(results) >= max_results:
                                    break
            except Exception as e:
                print(f"Error searching {transcript_file.name}: {e}", file=sys.stderr)

        if results:
            return "".join(results)
        return None

    def list_transcripts_json(self, last_n: int | None = None) -> str:
        """List transcripts metadata in JSON format"""
        transcripts = self.list_transcripts(last_n=last_n)
        results = []

        for t in transcripts:
            # Extract session ID
            match = re.search(r"compact_\d+_\d+_([a-f0-9-]+)\.txt", t.name)
            session_id = match.group(1) if match else "unknown"

            # Get metadata
            mtime = datetime.fromtimestamp(t.stat().st_mtime)  # noqa: DTZ006
            size_kb = t.stat().st_size / 1024

            # Try to get first user message as summary
            summary = ""
            try:
                with open(t, encoding="utf-8") as f:
                    content = f.read(5000)  # Read first 5KB
                    # Look for first user message
                    user_msg = re.search(r"Human: (.+?)\n", content)
                    if user_msg:
                        summary = user_msg.group(1)[:200]
            except Exception:
                pass

            results.append(
                {
                    "session_id": session_id,
                    "filename": t.name,
                    "timestamp": mtime.isoformat(),
                    "size_kb": round(size_kb, 1),
                    "summary": summary,
                }
            )

        return json.dumps(results, indent=2)

    def export_transcript(self, session_id: str | None = None, output_format: str = "text") -> Path | None:
        """Export a transcript to a file"""
        if not session_id:
            session_id = self.current_session

        if not session_id:
            return None

        # Find the transcript file
        transcript_file = None
        for t in self.list_transcripts():
            if session_id in t.name:
                transcript_file = t
                break

        if not transcript_file:
            return None

        # Create export directory
        export_dir = Path("exported_transcripts")
        export_dir.mkdir(exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_format == "markdown":
            output_file = export_dir / f"conversation_{timestamp}.md"
        else:
            output_file = export_dir / f"conversation_{timestamp}.txt"

        # Copy the transcript
        shutil.copy2(transcript_file, output_file)

        return output_file
