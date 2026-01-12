#!/usr/bin/env python3
"""
Meeting Prep Tool - Generate meeting briefing memos from documents using Gemini AI.

Uses Google's Gemini API (1M+ token context) for processing large documents,
then saves the briefing to Apple Notes.

Usage:
    # From document files
    python meeting_prep.py "Meeting with Client X" doc1.pdf doc2.md
    
    # With meeting context
    python meeting_prep.py "Board Meeting" report.pdf --context "Quarterly review with board members"
    
    # From stdin (pipe document content)
    cat large_doc.md | python meeting_prep.py "Project Review" --stdin
    
    # Specify Apple Notes folder
    python meeting_prep.py "Sales Call" proposal.pdf --folder "Work/Meetings"
    
    # Just generate briefing (don't save to Notes)
    python meeting_prep.py "Demo Prep" spec.md --no-save
    
    # Custom Gemini model
    python meeting_prep.py "Review" doc.pdf --model gemini-2.5-pro

Environment:
    GEMINI_API_KEY: Required. Your Google AI API key.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai package not installed.", file=sys.stderr)
    print("Install with: pip install google-generativeai", file=sys.stderr)
    sys.exit(1)


# Default paths
APPLE_NOTES_TOOL = Path(__file__).parent / "apple_notes.py"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_FOLDER = "Meeting Prep"

BRIEFING_PROMPT = """You are preparing a meeting briefing memo for an executive. 

Meeting: {meeting_title}
{context_section}

Based on the following documents, create a concise, actionable briefing memo.

DOCUMENTS:
{documents}

---

Generate a briefing memo with the following structure:

# Meeting Briefing: {meeting_title}

## Executive Summary
(2-3 sentences capturing the most critical points)

## Key Points
(Bullet points of the most important information from the documents)

## Discussion Topics
(What should be discussed in this meeting based on the documents)

## Questions to Consider
(Strategic questions to ask or think about)

## Potential Action Items
(Actions that may arise from this meeting)

## Background Context
(Brief relevant background if needed)

---

Keep the briefing focused and scannable. Use bullet points liberally.
Prioritize actionable information over comprehensive summaries.
"""


def read_document(path: Path) -> str:
    """Read document content. Supports text files and basic PDF extraction."""
    suffix = path.suffix.lower()
    
    if suffix == '.pdf':
        # Try to extract text from PDF
        try:
            import subprocess
            # Try pdftotext first (poppler)
            result = subprocess.run(
                ['pdftotext', '-layout', str(path), '-'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout
        except FileNotFoundError:
            pass
        
        # Fallback: try pypdf if available
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            text = []
            for page in reader.pages:
                text.append(page.extract_text() or "")
            return "\n".join(text)
        except ImportError:
            print(f"Warning: Cannot extract PDF text. Install poppler (pdftotext) or pypdf.", file=sys.stderr)
            return f"[PDF file: {path.name} - text extraction not available]"
    
    # Text-based files
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return path.read_text(encoding='latin-1')


def generate_briefing(
    meeting_title: str,
    documents: dict[str, str],
    meeting_context: str = "",
    model_name: str = DEFAULT_MODEL,
    api_key: str = None
) -> str:
    """Generate meeting briefing using Gemini API."""
    
    # Configure Gemini
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    # Format documents
    doc_sections = []
    for name, content in documents.items():
        doc_sections.append(f"### Document: {name}\n\n{content}\n")
    documents_text = "\n---\n".join(doc_sections)
    
    # Format context section
    context_section = ""
    if meeting_context:
        context_section = f"Context: {meeting_context}\n"
    
    # Build prompt
    prompt = BRIEFING_PROMPT.format(
        meeting_title=meeting_title,
        context_section=context_section,
        documents=documents_text
    )
    
    # Generate
    response = model.generate_content(prompt)
    return response.text


def save_to_apple_notes(title: str, content: str, folder: str = DEFAULT_FOLDER) -> str:
    """Save briefing to Apple Notes using the apple_notes.py tool."""
    
    if not APPLE_NOTES_TOOL.exists():
        raise FileNotFoundError(f"Apple Notes tool not found: {APPLE_NOTES_TOOL}")
    
    result = subprocess.run(
        [sys.executable, str(APPLE_NOTES_TOOL), "create", title, content, "--folder", folder],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to create note: {result.stderr}")
    
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(
        description='Generate meeting prep briefings from documents using Gemini AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('title', help='Meeting title for the briefing')
    parser.add_argument('documents', nargs='*', help='Document files to process')
    parser.add_argument('--context', '-c', help='Additional meeting context (who, what, purpose)')
    parser.add_argument('--stdin', action='store_true', help='Read document content from stdin')
    parser.add_argument('--folder', '-f', default=DEFAULT_FOLDER, help=f'Apple Notes folder (default: {DEFAULT_FOLDER})')
    parser.add_argument('--no-save', action='store_true', help='Print briefing only, do not save to Apple Notes')
    parser.add_argument('--model', '-m', default=DEFAULT_MODEL, help=f'Gemini model to use (default: {DEFAULT_MODEL})')
    parser.add_argument('--api-key', help='Gemini API key (or set GEMINI_API_KEY env var)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress progress messages')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.documents and not args.stdin:
        parser.error("Must provide document files or --stdin")
    
    def log(msg):
        if not args.quiet:
            print(msg, file=sys.stderr)
    
    try:
        # Load documents
        documents = {}
        
        if args.stdin:
            log("Reading from stdin...")
            documents["stdin"] = sys.stdin.read()
        
        for doc_path in args.documents or []:
            path = Path(doc_path)
            if not path.exists():
                print(f"Error: File not found: {doc_path}", file=sys.stderr)
                sys.exit(1)
            log(f"Reading: {path.name}")
            documents[path.name] = read_document(path)
        
        # Calculate total size for info
        total_chars = sum(len(c) for c in documents.values())
        log(f"Total content: {total_chars:,} characters (~{total_chars // 4:,} tokens)")
        
        # Generate briefing
        log(f"Generating briefing with {args.model}...")
        briefing = generate_briefing(
            meeting_title=args.title,
            documents=documents,
            meeting_context=args.context or "",
            model_name=args.model,
            api_key=args.api_key
        )
        
        # Output or save
        if args.no_save:
            print(briefing)
        else:
            # Generate note title with date
            date_str = datetime.now().strftime("%Y-%m-%d")
            note_title = f"Briefing: {args.title} ({date_str})"
            
            log(f"Saving to Apple Notes: {note_title}")
            result = save_to_apple_notes(note_title, briefing, args.folder)
            print(result)
            
            # Also print the briefing to stdout
            print("\n" + "="*60)
            print(briefing)
        
        log("Done!")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
