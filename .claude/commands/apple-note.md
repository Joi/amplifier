---
description: Read from or save to Apple Notes
category: productivity
allowed-tools: Bash
---

# Claude Command: Apple Note

Read from or save content to Apple Notes.

## Usage

### Reading Notes (search)
```
/apple-note find <search phrase>
/apple-note search <search phrase>
/apple-note read <search phrase>
```

Examples:
```
/apple-note find NAAN
/apple-note search meeting notes
/apple-note read tea foundation
```

### Writing Notes (save)
```
/apple-note save <description of what to save>
/apple-note create <title>
/apple-note add <description>
```

Examples:
```
/apple-note save the NAAN report
/apple-note create a note with the meeting summary
/apple-note add this recipe to my notes
```

## What This Command Does

### For Reading:
1. Searches Apple Notes by title/content matching the search phrase
2. Lists matching notes if multiple found
3. Returns the plaintext content of matching note(s)

### For Writing:
1. Identifies the content to save based on the user's description
2. Formats the content as HTML for proper rendering in Apple Notes
3. Creates a new note in Apple Notes (iCloud account) with proper formatting

## Technical Implementation

Use AppleScript via osascript to interact with Notes.

### Reading Notes - AppleScript Template

**Search by title:**
```bash
osascript -e '
tell application "Notes"
    tell account "iCloud"
        set matchingNotes to notes whose name contains "SEARCH_PHRASE"
        set noteList to {}
        repeat with n in matchingNotes
            set end of noteList to name of n
        end repeat
        return noteList
    end tell
end tell'
```

**Get content of matching note:**
```bash
osascript -e '
tell application "Notes"
    tell account "iCloud"
        set matchingNotes to notes whose name contains "SEARCH_PHRASE"
        if (count of matchingNotes) > 0 then
            set n to item 1 of matchingNotes
            return plaintext of n
        end if
    end tell
end tell'
```

**Search in note body (slower but searches content):**
```bash
osascript -e '
tell application "Notes"
    tell account "iCloud"
        set matchingNotes to notes whose plaintext contains "SEARCH_PHRASE"
        repeat with n in matchingNotes
            log name of n
        end repeat
    end tell
end tell'
```

### Writing Notes - AppleScript Template

```bash
osascript -e '
tell application "Notes"
    tell account "iCloud"
        make new note at folder "Notes" with properties {name:"NOTE_TITLE", body:"HTML_CONTENT"}
    end tell
end tell'
```

### HTML Formatting Guidelines

- Use `<h1>`, `<h2>`, `<h3>` for headings
- Use `<p>` for paragraphs
- Use `<ul>` and `<li>` for bullet lists
- Use `<ol>` and `<li>` for numbered lists
- Use `<b>` for bold text
- Use `<pre>` for code blocks
- Use `<a href="URL">text</a>` for links
- Escape single quotes with `'\''` in the shell command

### Example

```bash
osascript -e '
tell application "Notes"
    tell account "iCloud"
        make new note at folder "Notes" with properties {name:"Meeting Notes", body:"<h1>Meeting Notes</h1>
<p>Date: January 5, 2026</p>
<h2>Action Items</h2>
<ul>
<li>Review proposal</li>
<li>Send follow-up email</li>
</ul>"}
    end tell
end tell'
```

### Handling Special Characters

- Single quotes: Replace `'` with `'\''`
- Double quotes inside the body: Use `\"` or HTML entities
- Newlines: Can be literal in the AppleScript string

## Folder Options

By default, notes are created in the "Notes" folder. To specify a different folder:

```bash
tell account "iCloud"
    make new note at folder "FOLDER_NAME" with properties {...}
end tell
```

Common folders: "Notes", "Work", "Personal", etc.

## Additional Guidance

$ARGUMENTS
