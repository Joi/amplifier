# Dotfiles-Private Sync Prompt

## Quick Sync

```bash
cd ~/dotfiles-private
git pull
```

## Verify Symlinks

After pulling, ensure symlinks are in place:

```bash
# obs-dailynotes
ls -la ~/obs-dailynotes/.env
# Should show: .env -> /Users/joi/dotfiles-private/obs-dailynotes.env

# If broken, recreate:
cd ~/obs-dailynotes
ln -s ~/dotfiles-private/obs-dailynotes.env .env
```

## What's In This Repo

- `obs-dailynotes.env` - API keys, paths, config
- (Future: other project .env files)

## Security Reminder

- ✅ Repository is PRIVATE
- ✅ Contains API keys (OpenAI, Notion, Talivy, etc.)
- ❌ Never make this repo public
- ✅ Only clone on trusted machines
