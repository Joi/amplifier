---
description: Add knowledge to the chanoyu (tea ceremony) vault with proper formatting
argument-hint: <description of what to add>
---

# Add Knowledge to Chanoyu Vault

You are adding content to the chanoyu (tea ceremony) knowledge vault at `~/switchboard/chanoyu/`.

## Step 1: Read the Structure Guide

FIRST, read the structure guide to understand the format and conventions:

```
Read file: ~/switchboard/chanoyu/_STRUCTURE.md
```

This is REQUIRED before creating any content.

## Step 2: Understand the Request

The user wants to add: {{PROMPT}}

## Step 3: Execute

Based on the structure guide and the user's request:

1. Determine the appropriate file type (concept, source, person, etc.)
2. Follow the template from _STRUCTURE.md exactly
3. Create the file(s) with proper YAML frontmatter
4. Update INDEX.md if adding a new concept
5. Add cross-links to related existing content
6. Verify the integration

## Important Conventions

- Japanese terms: Always include kanji, romaji, and English
- Cross-links use Obsidian format: `[[chanoyu/concepts/name|Display Name]]`
- YAML frontmatter is required on all files
- One concept = one file in concepts/
