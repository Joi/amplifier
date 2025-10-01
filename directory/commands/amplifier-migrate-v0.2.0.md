---
description: Migrate Amplifier from v0.1.0 to v0.2.0
category: amplifier-setup
allowed-tools: Bash, Read, Write, Edit, Glob
---

# Claude Command: Amplifier Migrate to v0.2.0

This command helps you migrate an Amplifier installation from v0.1.0 to v0.2.0, automating the migration steps outlined in MIGRATING_FROM_v0.1.0.md.

## Usage

To migrate your Amplifier installation, just type:

```
/amplifier-migrate-0.2.0
```

## What you've already done


## What This Command Does

This command performs the following steps to migrate your project folder to amplifier from v0.1.0 layout to v0.2.0:

### 1. Pre-Migration Checks
- Verify we're in an Amplifier repository
- Check for existing v0.1.0 artifacts (.claude, CLAUDE.md, AGENTS.md, etc.)
- Confirm user wants to proceed with migration

### 2. Backup Existing Files
Create backups of existing Amplifier files that will be replaced:
```bash
mkdir -p backup
mv .claude backup/.claude 2>/dev/null || true
mv CLAUDE.md backup/CLAUDE.md 2>/dev/null || true
mv AGENTS.md backup/AGENTS.md 2>/dev/null || true
mv ai_context backup/ai_context 2>/dev/null || true
mv .env backup/.env 2>/dev/null || true
mv .env.example backup/.env.example 2>/dev/null || true
```

### 3. Amplifier v0.2.0 installation
- Install amplifier v0.2.0 : `uv tool install --from git+https://github.com/microsoft/amplifier@v0.2.0 amplifier`
- Intall amplifier v0.2.0 into your project `amplifier init`
- Put amplifier v0.2.0 into amplifier-dev mode: `amplifier mode set amplifier-dev`

### 4. Configuration Migration
- Check for custom `.env` settings in backup that differ from what has been set in `.amplifier/config.yaml`
- Guide user to migrate settings to `.amplifier/config.yaml`
- Explain environment variable override format: `AMPLIFIER__NESTED__KEY`

### 5. Custom Files Migration
- Check backup directory for customizations
  - Are there any `backup/.claude/commands` that aren't in `.amplifier/directory/commands`?
  - Are there any `backup/.claude/agents` that aren't in `.amplifier/directory/agents`?
  - Are there any `backup/.claude/tools` or `tools` that aren't in `.amplifier/directory/tools`?
  - Are there any instructions from `backup/CLAUDE.md` that aren't in `.amplifier/directory/modes/amplifier-dev/CLAUDE.md`?
  - Are there any instructions from `backup/AGENT.md` that aren't in `.amplifier/directory/modes/amplifier-dev/AGENT.md`?
  - Are there any files in `ai_context` that aren't in `.amplifier/directory/modes/amplifier-dev/context/`?
- If there are any customizations, explain the custom directory overlay system and offer to create custom overrides in `.amplifier.local/directory/modes/amplifier-dev`.
- If they want custom overrides, copy any custom commands, agents, tools, CLAUDE.md changes, AGENT.md changes and ai_context into the `.amplifier.local/directory/modes/amplifier-dev` directory.
- Verify all new files are referenced in `.amplifier.local/directory/modes/amplifier-dev/amplifier.yaml`

### 6. Migration Report
Provide a summary of:
- What was backed up
- What was migrated
- Configuration items that need manual review
- Next steps for the user
  - They will need to exit claude-code, run `uvx amplifier mode unset && uvx amplifier mode set amplifier-dev`, and restart claude code it to see the new version
  - They can continue to work on their custom files in `.amplifier.local`

## Migration Process

**Step-by-step execution:**

1. **Confirm Migration Start**
   - Ask user if they want to proceed
   - Explain what will happen

2. **Backup Phase**
   - Create backup directory
   - Move existing files to backup
   - Report what was backed up

3. **Installation Phase**
    - Install amplifier v0.2.0 : `uv tool install --from git+https://github.com/microsoft/amplifier@v0.2.0 amplifier`
    - Intall amplifier v0.2.0 into your project `amplifier init`
    - Put amplifier v0.2.0 into amplifier-dev mode: `amplifier mode set amplifier-dev`

4. **Configuration Phase**
   - Guide config migration

5. **Customization Phase**
   - Identify custom files in backup
   - Explain overlay system
   - Offer to migrate to `.amplifier.local/directory/amplifier-dev`
   - Migrate the custom files and content

6. **Report Phase**
   - Summarize what was done
   - List manual steps needed
   - Provide next steps

## Important Notes

- **Backup Safety**: All existing files are backed up to `backup/` directory before changes
- **Custom Configurations**: `.env` settings need manual migration to `.amplifier/config.yaml`
- **Custom Files**: Any customizations in backup need to be manually copied to `.amplifier.local/directory/`
- **New Structure**: v0.2.0 uses `.amplifier/` instead of top-level files
- **Mode System**: v0.2.0 introduces modes - we are set to `amplifier-dev` by default
- **Directory System**: Official resources are now fetched from remote and can be customized via overlay

## Post-Migration Steps

After migration completes, you should:

1. **Review Configuration**
   - Check `.amplifier/config.yaml` for settings
   - Migrate any custom `.env` values

2. **Review Customizations**
   - Check `backup/` for any custom files
   - Copy customizations to `.amplifier.local/directory/` if needed
   - Ensure all customizations for amplifier-dev mode are references in `.amplifier.local/directory/modes/amplifier-dev/amplifier.yaml`

3. **Test Functionality**
   - Start Claude Code: `claude`
   - Verify agents are available
   - Test a simple command

4. **Clean Up**
   - Once verified, you can remove the `backup/` directory
   - Keep `.amplifier.local/` if you have customizations

## Additional Guidance

$ARGUMENTS