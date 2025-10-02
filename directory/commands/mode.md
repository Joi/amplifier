# /mode - Natural Language Mode Management

Unified command for all mode operations. I'll analyze your request and execute the appropriate `amplifier` command.

Read @amplifier-context/AMPLIFIER_CLI.md

## Intent Detection Process

I'll analyze the input in `$ARGUMENTS` to determine which operation you want:

### Phase 1: Direct Command Detection
First, I'll check if you're using explicit command syntax:
- `create <name>` → Create a new mode
- `list` → List available modes
- `freeze` → Freeze current modes to directory

### Phase 2: Keyword Pattern Analysis
If no direct command, I'll look for operation indicators:

**CREATE indicators:**
- Keywords: "create", "new", "make", "build", "setup", "initialize", "add", "generate"
- Example inputs:
  - "create a golang mode"
  - "new mode for python projects"
  - "make a mode called data-science"
  - "setup security-audit mode"

**LIST indicators:**
- Keywords: "list", "show", "what", "available", "see", "display", "have", "which"
- Question patterns: "what modes", "which modes", "modes?"
- Example inputs:
  - "list all modes"
  - "what modes are available?"
  - "show me the modes"
  - "which modes do I have?"

**FREEZE indicators:**
- Keywords: "freeze", "lock", "preserve", "customize", "overlay", "snapshot"
- Example inputs:
  - "freeze the current modes"
  - "lock modes for customization"
  - "preserve mode state"
  - "create overlay for modes"

### Phase 3: Contextual Inference
If intent is still unclear, I'll analyze context:
- Mentions of customization → suggest freeze
- Questions about available options → list
- Descriptions of new workflows → create

## Mode Name Extraction (for create operations)

When creating a mode, I'll extract the name using these patterns:

1. **Explicit formats:**
   - Quoted: `"mode-name"` or `'mode-name'`
   - After keywords: `create MODE-NAME`, `called MODE-NAME`, `named MODE-NAME`
   - With prepositions: `mode for MODE-NAME`, `MODE-NAME mode`

2. **Inference from description:**
   - "golang projects" → suggest "golang"
   - "python development" → suggest "python"
   - "security audit" → suggest "security-audit"
   - "data science workspace" → suggest "data-science"
   - "react frontend" → suggest "react"

3. **Name validation:**
   - Convert to lowercase
   - Replace spaces with dashes
   - Remove invalid characters (keep only letters, numbers, dashes, underscores)
   - Examples:
     - "Data Science" → "data-science"
     - "React Frontend!" → "react-frontend"
     - "C++ Tools" → "cpp-tools"

## Execution Logic

Based on the detected intent:

### CREATE Operation
```bash
# After extracting/validating mode name
uv run amplifier mode create <mode-name>
```

If name is missing or unclear:
```
To create a mode, I need a name. Based on your request, would "[suggested-name]" work?

You can also specify directly: /mode create <your-mode-name>
```

### LIST Operation
```bash
uv run amplifier mode list
```

### FREEZE Operation
```bash
uv run amplifier directory freeze
```

### Ambiguous Intent
When intent cannot be determined:
```
I'm not sure which mode operation you want:
• Create a new mode: /mode create <name>
• List available modes: /mode list
• Freeze current modes: /mode freeze

What would you like to do?
```

## Examples of Natural Language Processing

**Input:** "I want to create a new golang mode"
**Detection:** CREATE keyword "create", mode name "golang"
**Execution:** `uv run amplifier mode create golang`

**Input:** "what modes do we have?"
**Detection:** LIST keywords "what" + "modes" + "have"
**Execution:** `uv run amplifier mode list`

**Input:** "freeze the modes for customization"
**Detection:** FREEZE keyword "freeze"
**Execution:** `uv run amplifier directory freeze`

**Input:** "set up a python development environment"
**Detection:** CREATE keyword "set up", inferred name "python"
**Execution:** `uv run amplifier mode create python`

**Input:** "show available modes"
**Detection:** LIST keywords "show" + "available"
**Execution:** `uv run amplifier mode list`

## Decision Priority

1. If input starts with explicit command word → execute immediately
2. If multiple operation keywords present → use first detected operation
3. If no clear match → present options to user
4. Always validate mode names before execution
5. Provide helpful feedback on what will be executed

## Error Recovery

**Invalid characters in name:**
Show the sanitized version and proceed:
```
Converting "[original]" to "[sanitized]" (mode names can only contain letters, numbers, dashes, and underscores)
Executing: amplifier mode create [sanitized]
```

**Empty or missing arguments:**
For list/freeze → execute directly
For create → ask for mode name

**Command execution failure:**
Show the error and suggest alternatives or corrections.

---

Now I'll analyze "$ARGUMENTS" and execute the appropriate mode operation.