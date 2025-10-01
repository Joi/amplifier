---
description: Migrate Amplifier from v0.1.0 to v0.2.0
category: amplifier-setup
allowed-tools: Bash, Read, Write, Edit, Glob
---

# Claude Command: Amplifier Migrate to v0.2.0

This command helps you migrate an Amplifier installation from v0.1.0 to v0.2.0. As this may be a customized branch of the original amplifier v0.1.0 repository, we go to some lengths to ensure your customizations are preserved as an amplifier-dev mode overlay.

## Usage

To migrate your customized Amplifier installation, just type:

```
/amplifier-migrate-0.2.0
```

## What This Command Does

This command performs the following steps to migrate your current project folder to amplifier from a v0.1.0 layout to v0.2.0:

### 1. Pre-Migration Checks
- Verify we're in an Amplifier repository
- Check for existing v0.1.0 artifacts (.claude, CLAUDE.md, AGENTS.md, etc.)
- Confirm user wants to proceed with migration

### 2. Move Existing Amplifier Files
Move existing Amplifier files out of the way:
```bash
mkdir -p backup
mv .claude backup/ 2>/dev/null || true
mv CLAUDE.md backup/ 2>/dev/null || true
mv AGENTS.md backup/ 2>/dev/null || true
mv ai_context backup/amplifier-context 2>/dev/null || true
mv .env backup/ 2>/dev/null || true
mv .env.example backup/ 2>/dev/null || true
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
    - Ignore any files in `ai_context/generated`
    - Ignore any files in `ai_context/git_collector`
    - Copy all other files in `ai_context` that don't already exist into `.amplifier.local/directory/modes/amplifier-dev/context/`
- If there are any customizations, explain the custom directory overlay system and offer to create custom overrides in `.amplifier.local/directory/modes/amplifier-dev`.
- If they want custom overrides, copy any custom commands, agents, tools, CLAUDE.md changes, AGENT.md changes and amplifier-context into the `.amplifier.local/directory/modes/amplifier-dev` directory.
- **IMPORTANT** Add references to the customizations in the overlay mode configuration at: `.amplifier.local/directory/modes/amplifier-dev/amplifier.yaml`. If you do not add references, they will not be copied when `amplifier mode set amplifier-dev` is run.

### 6. Update .gitignore

Ensure the following entries are in the .gitignore file:

```
# Amplifier-created artifacts.
.claude
AGENT.md
CLAUDE.md
```

### 7. Update Makefile

Remove the worktree and transcript commands from the Makefile.

### 8. Migration Report
Provide a summary of:
- What was backed up
- What was migrated
- Configuration items that need manual review
- Next steps for the user
  - They will need to exit claude-code, run `uvx amplifier mode unset && uvx amplifier mode set amplifier-dev`, and restart claude code it to see the new version
  - They can continue to work on their custom files in `.amplifier.local`
  - Review the files in `/backup`. Once you are happy that you are happy with the new v0.2.0 layout, you can delete it.
  - If they want to do more than just customize the existing amplifier-dev mode, they can create a new mode by adding a mode directory in `.amplifier.local/modes/` and whatever items they would like there and setting up their `.amplifier/local/modes/<new-mode>/amplifier.yaml` file.
  - `git pull` and fix any merge conflicts to be on the actual v0.2.0 version, now in the main branch.

## Migration Process

**Step-by-step execution:**

1. **Confirm Migration Start**
   - Ask user if they want to proceed
   - Explain what will happen

2. **Amplifier Backup (move) Phase**
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

6. **.gitignore Update Phase**
   - Update the .gitignore with the appropriate amplifier entries.

7. **Update Makefile**
   - Remove the worktree and transcript commands from the Makefile.

8. **Report Phase**
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