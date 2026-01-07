# Fix for Notes Sync Special Character Issue

## Problem
The notes sync fails on content with special characters like `{`, `}`, `&` because of shell/AppleScript escaping issues.

## Solution
Use temp file approach instead of inline `-e` flag for complex content.

## How to Apply

Edit `~/obs-dailynotes/lib/notes-sync/applescript.js`:

### Replace the imports and runAppleScript function (lines 1-26):

```javascript
/**
 * AppleScript bridge for Mac Notes.app
 *
 * Provides CRUD operations for notes via AppleScript/osascript
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const SYNC_FOLDER_NAME = 'Obsidian Sync';

/**
 * Execute an AppleScript and return the result
 * Uses temp file approach for complex scripts to avoid shell escaping issues
 * @param {string} script - AppleScript code to execute
 * @param {boolean} useTempFile - Force temp file approach (default: false)
 * @returns {string} - Output from the script
 */
function runAppleScript(script, useTempFile = false) {
  try {
    // For complex content (with special chars), use temp file to avoid escaping issues
    if (useTempFile || script.includes('{') || script.includes('&') || script.length > 5000) {
      const tempFile = path.join(os.tmpdir(), `notes-sync-${Date.now()}.scpt`);
      try {
        fs.writeFileSync(tempFile, script, 'utf-8');
        const result = execSync(`osascript "${tempFile}"`, {
          encoding: 'utf-8',
          maxBuffer: 10 * 1024 * 1024
        });
        return result.trim();
      } finally {
        // Clean up temp file
        try { fs.unlinkSync(tempFile); } catch (e) { /* ignore */ }
      }
    }
    
    // Simple scripts can use the inline approach
    const result = execSync(`osascript -e '${script.replace(/'/g, "'\\"'\\"'")}'`, {
      encoding: 'utf-8',
      maxBuffer: 10 * 1024 * 1024
    });
    return result.trim();
  } catch (error) {
    throw new Error(`AppleScript error: ${error.message}`);
  }
}
```

## Quick Apply Command

```bash
cd ~/obs-dailynotes
# Open in editor
code lib/notes-sync/applescript.js
```

Or ask Claude to fix it when you're in that directory.
