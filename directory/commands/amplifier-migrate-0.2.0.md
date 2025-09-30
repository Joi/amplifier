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

- amplifier has been installed: `uv tool install --from git+https://github.com/microsoft/amplifier@v0.2.0 amplifier`
- an amplifier directory has been fetched `amplifier directory fetch`
- amplifier has been put in python-coder mode: `amplifier mode set python-coder`

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

### 3. Configuration Migration
- Check for custom `.env` settings in backup that differ from what has been set in `.amplifier/config.yaml`
- Guide user to migrate settings to `.amplifier/config.yaml`
- Explain environment variable override format: `AMPLIFIER__NESTED__KEY`

### 4. Custom Files Migration
- Check backup directory for customizations
- Offer to copy customizations to `.amplifier.local/directory/python-coder`
- Explain the custom directory overlay system

### 5. Migration Report
Provide a summary of:
- What was backed up
- What was migrated
- Configuration items that need manual review
- Next steps for the user

## Migration Process

**Step-by-step execution:**

1. **Confirm Migration Start**
   - Ask user if they want to proceed
   - Explain what will happen

2. **Backup Phase**
   - Create backup directory
   - Move existing files to backup
   - Report what was backed up

3. **Configuration Phase**
   - Guide config migration

4. **Customization Phase**
   - Identify custom files in backup
   - Offer to migrate to `.amplifier.local/`
   - Explain overlay system

5. **Report Phase**
   - Summarize what was done
   - List manual steps needed
   - Provide next steps

## Important Notes

- **Backup Safety**: All existing files are backed up to `backup/` directory before changes
- **Custom Configurations**: `.env` settings need manual migration to `.amplifier/config.yaml`
- **Custom Files**: Any customizations in backup need to be manually copied to `.amplifier.local/directory/`
- **New Structure**: v0.2.0 uses `.amplifier/` instead of top-level files
- **Mode System**: v0.2.0 introduces modes - we are set to `python-coder` by default
- **Directory System**: Official resources are now fetched from remote and can be customized via overlay

## Post-Migration Steps

After migration completes, you should:

1. **Review Configuration**
   - Check `.amplifier/config.yaml` for settings
   - Migrate any custom `.env` values

2. **Review Customizations**
   - Check `backup/` for any custom files
   - Copy customizations to `.amplifier.local/directory/` if needed

3. **Test Functionality**
   - Start Claude Code: `claude`
   - Verify agents are available
   - Test a simple command

4. **Clean Up**
   - Once verified, you can remove the `backup/` directory
   - Keep `.amplifier.local/` if you have customizations

## Additional Guidance

$ARGUMENTS
