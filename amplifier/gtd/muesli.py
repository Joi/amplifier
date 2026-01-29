#!/usr/bin/env python3
"""
Muesli Integration - Granola meeting transcripts for GTD daily notes.

Syncs meeting transcripts from Granola via muesli and injects
summaries into daily notes under the matching meeting time slots.

Features:
- Auto-detect Japanese transcripts
- Generate English translations
- Generate English summaries
- Link to both Japanese and English transcripts
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

# Default paths
MUESLI_DATA_DIR = Path.home() / ".local" / "share" / "muesli"
DAILYNOTE_DIR = Path.home() / "switchboard" / "dailynote"
ENGLISH_TRANSCRIPTS_DIR = MUESLI_DATA_DIR / "transcripts_en"


def is_japanese_text(text: str, threshold: float = 0.1) -> bool:
    """Detect if text is primarily Japanese.
    
    Returns True if more than threshold ratio of characters are Japanese.
    """
    if not text:
        return False
    
    # Count Japanese characters (hiragana, katakana, kanji)
    japanese_chars = 0
    total_chars = 0
    
    for char in text:
        if char.isspace():
            continue
        total_chars += 1
        # Hiragana: U+3040-U+309F, Katakana: U+30A0-U+30FF, Kanji: U+4E00-U+9FFF
        if '\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' or '\u4E00' <= char <= '\u9FFF':
            japanese_chars += 1
    
    if total_chars == 0:
        return False
    
    return (japanese_chars / total_chars) >= threshold


def get_anthropic_api_key() -> Optional[str]:
    """Get Anthropic API key from age-encrypted secrets or environment."""
    # First check environment
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        return api_key
    
    # Try to decrypt from age-encrypted secrets
    secrets_file = Path.home() / "dotfiles-private" / "amplifier-secrets.env.age"
    identity_file = Path.home() / ".config" / "age" / "secrets.key"
    
    if secrets_file.exists() and identity_file.exists():
        try:
            result = subprocess.run(
                ["age", "--decrypt", "-i", str(identity_file), str(secrets_file)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith("ANTHROPIC_API_KEY="):
                        return line.split("=", 1)[1]
        except Exception:
            pass
    
    return None


def call_llm(prompt: str, max_tokens: int = 8000, model: str = "claude-sonnet-4-20250514") -> Optional[str]:
    """Call LLM via Anthropic API directly for translation/summarization."""
    try:
        import anthropic
        
        api_key = get_anthropic_api_key()
        if not api_key:
            print("   No Anthropic API key found")
            return None
        
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
    except ImportError:
        print("   anthropic library not installed, trying amplifier CLI...")
        # Fallback to amplifier CLI
        try:
            result = subprocess.run(
                ["amplifier", "run", "--mode", "single", "--output-format", "text", prompt],
                capture_output=True,
                text=True,
                timeout=300,
                env={**os.environ, "NO_COLOR": "1"},
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
    except Exception as e:
        print(f"   LLM call failed: {e}")
        return None


def translate_to_english(japanese_text: str, title: str) -> Optional[str]:
    """Translate Japanese transcript to English."""
    prompt = f"""Translate this Japanese meeting transcript to English. 
Preserve the speaker timestamps and format. Keep it natural and readable.

Title: {title}

Transcript:
{japanese_text}

Provide only the English translation, maintaining the same format with **Speaker (HH:MM:SS):** markers."""

    return call_llm(prompt)


def generate_english_summary(text: str, title: str, is_english: bool = True) -> Optional[str]:
    """Generate an English summary of a meeting transcript."""
    lang_note = "" if is_english else " (translated from Japanese)"
    
    prompt = f"""Create a concise English summary of this meeting transcript{lang_note}.

Title: {title}

Transcript:
{text[:15000]}  # Limit to avoid token overflow

Provide a summary with:
1. **Key Points** - Main topics discussed (3-5 bullet points)
2. **Decisions** - Any decisions made
3. **Action Items** - Follow-ups or tasks mentioned
4. **Notable Quotes** - Any important statements (optional)

Keep it concise but informative. Use markdown formatting."""

    return call_llm(prompt)


@dataclass
class Meeting:
    """Represents a Granola meeting."""

    doc_id: str
    title: str
    created_at: datetime
    start_time: Optional[datetime]  # First speaker timestamp
    transcript_path: Path
    summary: Optional[str] = None
    english_transcript_path: Optional[Path] = None
    is_japanese: bool = False

    @property
    def local_time(self) -> datetime:
        """Get meeting time in local timezone."""
        # Use start_time if available, otherwise created_at
        dt = self.start_time or self.created_at
        return dt.astimezone()

    @property
    def time_str(self) -> str:
        """Get HH:MM format for matching daily note slots."""
        return self.local_time.strftime("%H:%M")


def sync_muesli() -> dict:
    """Sync muesli data from Granola API."""
    try:
        result = subprocess.run(
            ["muesli", "sync"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Sync timed out"}
    except FileNotFoundError:
        return {"success": False, "error": "muesli not found - install from github.com/harperreed/muesli"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_transcript_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from transcript file."""
    content = path.read_text()
    
    # Extract frontmatter between --- markers
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    
    frontmatter = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip()
            # Handle quoted strings
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            # Handle arrays (simple case)
            if value == "[]":
                value = []
            frontmatter[key.strip()] = value
    
    return frontmatter


def extract_first_speaker_time(path: Path) -> Optional[datetime]:
    """Extract timestamp from first speaker line in transcript.
    
    Speaker timestamps are in LOCAL time, not UTC. We use the date from
    the filename (which muesli sets based on local time) and combine it
    with the speaker time to get a proper local datetime.
    """
    content = path.read_text()
    
    # Find first **Speaker (HH:MM:SS):** pattern after frontmatter
    match = re.search(r"\*\*Speaker \((\d{2}):(\d{2}):(\d{2})\):\*\*", content)
    if not match:
        return None
    
    # Get the date from the filename (YYYY-MM-DD_title.md)
    # The filename date is based on local time, matching the speaker timestamps
    filename = path.stem  # e.g., "2026-01-25_joshua-joi"
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})_", filename)
    if not date_match:
        return None
    
    date_str = date_match.group(1)
    
    # Combine date with speaker time in LOCAL timezone
    h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        local_tz = ZoneInfo("Asia/Tokyo")  # Assuming JST for now
        speaker_dt = datetime(
            int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10]),
            h, m, s, tzinfo=local_tz
        )
        return speaker_dt
    except Exception:
        return None


def get_meetings(
    date: Optional[datetime] = None,
    data_dir: Path = MUESLI_DATA_DIR,
) -> list[Meeting]:
    """Get all meetings for a specific date.

    Note: Granola saves created_at in UTC, so meetings after midnight UTC
    but before midnight local time will have the previous day's date in
    the filename. We check both today and yesterday's files, then filter
    by actual local meeting time.
    """
    if date is None:
        date = datetime.now()

    target_date = date.date() if hasattr(date, 'date') else date
    date_str = target_date.strftime("%Y-%m-%d")

    # Also check previous day's files (UTC vs local timezone issue)
    prev_date = target_date - timedelta(days=1)
    prev_date_str = prev_date.strftime("%Y-%m-%d")

    transcripts_dir = data_dir / "transcripts"

    if not transcripts_dir.exists():
        return []

    meetings = []

    # Check both today and yesterday's dated files
    for date_prefix in [date_str, prev_date_str]:
        for path in transcripts_dir.glob(f"{date_prefix}_*.md"):
            fm = parse_transcript_frontmatter(path)

            # Parse created_at
            created_at_str = fm.get("created_at", "")
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except Exception:
                continue

            # Get first speaker time for more accurate meeting start
            start_time = extract_first_speaker_time(path)

            meeting = Meeting(
                doc_id=fm.get("doc_id", ""),
                title=fm.get("title", path.stem),
                created_at=created_at,
                start_time=start_time,
                transcript_path=path,
            )

            # Filter by actual local date (not filename date)
            meeting_local_date = meeting.local_time.date()
            if meeting_local_date == target_date:
                meetings.append(meeting)

    # Sort by time
    meetings.sort(key=lambda m: m.local_time)
    return meetings


def generate_summary(meeting: Meeting, use_muesli: bool = True) -> Optional[str]:
    """Generate or fetch summary for a meeting.
    
    If use_muesli=True, tries muesli summarize command first.
    Otherwise returns None (caller can use their own summarization).
    """
    if not use_muesli:
        return None
    
    # Check if summary already exists
    summary_path = MUESLI_DATA_DIR / "summaries" / f"{meeting.transcript_path.stem}.md"
    if summary_path.exists():
        return summary_path.read_text()
    
    # Try muesli summarize (requires OpenAI API key)
    try:
        result = subprocess.run(
            ["muesli", "summarize", meeting.doc_id, "--save"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and summary_path.exists():
            return summary_path.read_text()
    except Exception:
        pass
    
    return None


def get_transcript_content(path: Path) -> str:
    """Get transcript content without frontmatter."""
    content = path.read_text()
    
    # Skip frontmatter
    match = re.match(r"^---\n.*?\n---\n", content, re.DOTALL)
    if match:
        content = content[match.end():]
    
    return content.strip()


def get_transcript_excerpt(meeting: Meeting, max_lines: int = 20) -> str:
    """Get first N lines of transcript (after frontmatter) as excerpt."""
    content = get_transcript_content(meeting.transcript_path)
    
    # Get first N non-empty lines
    lines = [l for l in content.split("\n") if l.strip()][:max_lines]
    return "\n".join(lines)


def process_transcript(meeting: Meeting, force: bool = False) -> dict:
    """Process a transcript: detect language, translate if Japanese, generate summary.
    
    Returns dict with processing results.
    """
    results = {
        "is_japanese": False,
        "translated": False,
        "summarized": False,
        "english_path": None,
        "summary": None,
    }
    
    # Ensure English transcripts directory exists
    ENGLISH_TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get transcript content
    content = get_transcript_content(meeting.transcript_path)
    
    # Detect if Japanese
    meeting.is_japanese = is_japanese_text(content)
    results["is_japanese"] = meeting.is_japanese
    
    # English transcript path
    en_path = ENGLISH_TRANSCRIPTS_DIR / f"{meeting.transcript_path.stem}_en.md"
    
    if meeting.is_japanese:
        # Check if English translation already exists
        if en_path.exists() and not force:
            print(f"   English translation already exists: {en_path.name}")
            meeting.english_transcript_path = en_path
            results["english_path"] = str(en_path)
        else:
            # Translate to English
            print(f"   Translating Japanese transcript to English...")
            english_content = translate_to_english(content, meeting.title)
            
            if english_content:
                # Create English transcript with frontmatter
                fm = parse_transcript_frontmatter(meeting.transcript_path)
                en_frontmatter = f"""---
doc_id: {fm.get('doc_id', '')}
source: granola (translated)
original: {meeting.transcript_path.name}
created_at: {fm.get('created_at', '')}
title: {meeting.title} (English)
generator: muesli-gtd translation
---

# {meeting.title} (English Translation)

_Translated from Japanese_

"""
                en_path.write_text(en_frontmatter + english_content)
                meeting.english_transcript_path = en_path
                results["translated"] = True
                results["english_path"] = str(en_path)
                print(f"   ✓ Saved English translation: {en_path.name}")
            else:
                print(f"   ⚠ Translation failed")
        
        # Generate summary from English translation
        summary_content = get_transcript_content(en_path) if en_path.exists() else content
    else:
        # Not Japanese - use original for summary
        summary_content = content
    
    # Generate English summary
    summary_path = MUESLI_DATA_DIR / "summaries" / f"{meeting.transcript_path.stem}_summary.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    
    if summary_path.exists() and not force:
        meeting.summary = summary_path.read_text()
        results["summary"] = meeting.summary
        print(f"   Summary already exists")
    else:
        print(f"   Generating English summary...")
        summary = generate_english_summary(
            summary_content[:15000],  # Limit size
            meeting.title,
            is_english=not meeting.is_japanese
        )
        
        if summary:
            summary_path.write_text(summary)
            meeting.summary = summary
            results["summarized"] = True
            results["summary"] = summary
            print(f"   ✓ Saved summary")
        else:
            print(f"   ⚠ Summary generation failed")
    
    return results


def format_meeting_notes(meeting: Meeting, include_summary: bool = True) -> str:
    """Format meeting notes for injection into daily note."""
    lines = []

    # Summary if available
    if include_summary and meeting.summary:
        lines.append("#### Summary")
        lines.append("")
        # Convert any ## or # headings in summary to ##### to avoid breaking Notes section parsing
        summary = meeting.summary
        # Convert ## headings to ##### (skip # title if present)
        summary = re.sub(r'^## ', '##### ', summary, flags=re.MULTILINE)
        summary = re.sub(r'^# ([^#])', r'##### \1', summary, flags=re.MULTILINE)
        lines.append(summary)
        lines.append("")
    
    # Links to transcripts
    transcript_name = meeting.transcript_path.stem
    
    if meeting.is_japanese and meeting.english_transcript_path:
        # Dual links for Japanese meetings
        en_name = meeting.english_transcript_path.stem
        lines.append(f"**Transcripts**: [[muesli_en/{en_name}|English]] | [[muesli/{transcript_name}|日本語 (Original)]]")
    else:
        # Single link for English meetings
        lines.append(f"**Transcript**: [[muesli/{transcript_name}|View full transcript]]")
    
    lines.append(f"**Granola ID**: `{meeting.doc_id}`")
    lines.append("")
    
    return "\n".join(lines)


def find_meeting_slot(daily_note: str, meeting: Meeting, tolerance_minutes: int = 30) -> Optional[tuple[int, str]]:
    """Find the matching meeting slot in daily note for this meeting.
    
    Returns (line_index, header_line) or None if no match.
    Matches by time within tolerance_minutes.
    """
    meeting_time = meeting.local_time
    lines = daily_note.split("\n")
    
    # Look for ### HH:MM patterns in Notes section
    in_notes_section = False
    
    for i, line in enumerate(lines):
        if line.startswith("## ") and "Notes" in line:
            in_notes_section = True
            continue
        
        if not in_notes_section:
            continue
        
        # Stop at next major section
        if line.startswith("## "):
            break
        
        # Check for meeting header
        match = re.match(r"^### (\d{2}):(\d{2})\s+(.+)$", line)
        if match:
            slot_h, slot_m = int(match.group(1)), int(match.group(2))
            slot_title = match.group(3)
            
            # Create datetime for comparison
            slot_time = meeting_time.replace(hour=slot_h, minute=slot_m, second=0)
            
            # Check if within tolerance
            diff = abs((meeting_time - slot_time).total_seconds() / 60)
            if diff <= tolerance_minutes:
                return (i, line)
    
    return None


def inject_meeting_notes(
    date: Optional[datetime] = None,
    dailynote_dir: Path = DAILYNOTE_DIR,
    generate_summaries: bool = False,
    translate: bool = False,
    dry_run: bool = False,
) -> dict:
    """Inject meeting notes into daily note for a specific date.
    
    Args:
        date: Date to process (default: today)
        dailynote_dir: Path to daily notes directory
        generate_summaries: Generate English summaries
        translate: Translate Japanese transcripts to English
        dry_run: Don't write changes
    
    Returns dict with results.
    """
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    daily_note_path = dailynote_dir / f"{date_str}.md"
    
    if not daily_note_path.exists():
        return {
            "success": False,
            "error": f"Daily note not found: {daily_note_path}",
            "date": date_str,
        }
    
    # Get meetings for this date
    meetings = get_meetings(date)
    if not meetings:
        return {
            "success": True,
            "message": "No meetings found for this date",
            "date": date_str,
            "meetings_processed": 0,
        }
    
    # Read daily note
    content = daily_note_path.read_text()
    original_content = content
    
    # Process transcripts (translate + summarize) if requested
    if translate or generate_summaries:
        for meeting in meetings:
            print(f"\n📄 Processing: {meeting.title}")
            process_transcript(meeting)
    
    # Process each meeting
    injected = []
    skipped = []
    
    for meeting in meetings:
        slot = find_meeting_slot(content, meeting)
        
        if not slot:
            skipped.append({
                "title": meeting.title,
                "time": meeting.time_str,
                "reason": "No matching slot found",
            })
            continue
        
        line_idx, header_line = slot
        
        # Check if already injected (look for Granola ID)
        next_section_idx = len(content.split("\n"))
        lines = content.split("\n")
        for j in range(line_idx + 1, len(lines)):
            if lines[j].startswith("### ") or lines[j].startswith("## "):
                next_section_idx = j
                break
        
        section_content = "\n".join(lines[line_idx:next_section_idx])
        if meeting.doc_id in section_content:
            skipped.append({
                "title": meeting.title,
                "time": meeting.time_str,
                "reason": "Already injected",
            })
            continue
        
        # Inject meeting notes after the header
        notes = format_meeting_notes(meeting, include_summary=(translate or generate_summaries))
        
        lines = content.split("\n")
        # Insert after header line (and any blank line)
        insert_idx = line_idx + 1
        while insert_idx < len(lines) and lines[insert_idx].strip() == "":
            insert_idx += 1
        
        lines.insert(insert_idx, notes)
        content = "\n".join(lines)
        
        injected.append({
            "title": meeting.title,
            "time": meeting.time_str,
            "doc_id": meeting.doc_id,
        })
    
    # Save if changed and not dry run
    if content != original_content and not dry_run:
        daily_note_path.write_text(content)
    
    return {
        "success": True,
        "date": date_str,
        "daily_note": str(daily_note_path),
        "meetings_processed": len(injected),
        "injected": injected,
        "skipped": skipped,
        "dry_run": dry_run,
    }


def sync_and_inject(
    date: Optional[datetime] = None,
    generate_summaries: bool = False,
    translate: bool = True,
) -> dict:
    """Sync muesli and inject meeting notes in one operation.
    
    Args:
        date: Date to process (default: today)
        generate_summaries: Generate English summaries (default: True when translate=True)
        translate: Translate Japanese transcripts to English (default: True)
    """
    results = {"sync": None, "inject": None}
    
    # Sync first
    print("📥 Syncing Granola meetings via muesli...")
    sync_result = sync_muesli()
    results["sync"] = sync_result
    
    if not sync_result.get("success"):
        print(f"   ⚠ Sync warning: {sync_result.get('error')}")
        # Continue anyway - might have cached data
    else:
        print("   ✓ Sync complete")
    
    # Inject with translation and summaries
    print("\n📝 Processing meeting transcripts...")
    inject_result = inject_meeting_notes(
        date=date,
        generate_summaries=generate_summaries or translate,  # Summary comes with translation
        translate=translate,
    )
    results["inject"] = inject_result
    
    if inject_result.get("success"):
        count = inject_result.get("meetings_processed", 0)
        print(f"\n   ✓ Injected {count} meeting(s) into daily note")
        for m in inject_result.get("injected", []):
            print(f"      + {m['time']} {m['title']}")
        for m in inject_result.get("skipped", []):
            print(f"      - {m['time']} {m['title']} ({m['reason']})")
    else:
        print(f"   ✗ Error: {inject_result.get('error')}")
    
    return results


def list_meetings(date: Optional[datetime] = None) -> list[dict]:
    """List meetings for a date (for tool use)."""
    meetings = get_meetings(date)
    return [
        {
            "doc_id": m.doc_id,
            "title": m.title,
            "time": m.time_str,
            "created_at": m.created_at.isoformat(),
            "transcript": str(m.transcript_path),
        }
        for m in meetings
    ]


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Muesli integration for GTD")
    parser.add_argument("command", choices=["sync", "list", "inject", "sync-inject", "process"])
    parser.add_argument("--date", help="Date (YYYY-MM-DD), default today")
    parser.add_argument("--translate", action="store_true", help="Translate Japanese to English")
    parser.add_argument("--summarize", action="store_true", help="Generate English summaries")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if exists")

    args = parser.parse_args()

    # Parse date
    date = None
    if args.date:
        date = datetime.strptime(args.date, "%Y-%m-%d")

    if args.command == "sync":
        result = sync_muesli()
        print(result)
    elif args.command == "list":
        meetings = list_meetings(date)
        for m in meetings:
            # Check if Japanese
            content = get_transcript_content(Path(m["transcript"]))
            is_jp = "🇯🇵" if is_japanese_text(content) else "🇺🇸"
            print(f"{m['time']} | {is_jp} {m['title']} | {m['doc_id']}")
    elif args.command == "process":
        # Process transcripts only (translate + summarize) without injecting
        meetings = get_meetings(date)
        for meeting in meetings:
            print(f"\n📄 Processing: {meeting.title}")
            result = process_transcript(meeting, force=args.force)
            print(f"   Japanese: {result['is_japanese']}, Translated: {result['translated']}, Summarized: {result['summarized']}")
    elif args.command == "inject":
        result = inject_meeting_notes(
            date=date,
            generate_summaries=args.summarize,
            translate=args.translate,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2))
    elif args.command == "sync-inject":
        result = sync_and_inject(
            date=date,
            generate_summaries=args.summarize,
            translate=args.translate or True,  # Default to translate
        )


if __name__ == "__main__":
    main()
