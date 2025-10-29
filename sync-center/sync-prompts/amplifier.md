# Amplifier Sync Prompt

## Quick Sync

```bash
cd ~/amplifier
git pull
make install  # If dependencies changed
```

## Verify

```bash
# Check version
python --version  # Should be 3.11+

# Check dependencies
pip list | grep anthropic
pip list | grep pydantic

# Run a test
make test
```

## Common Issues

### New Dependencies
If `make install` shows new packages:
- Review what changed: `git log --oneline -10`
- Check DISCOVERIES.md for any breaking changes

### Python Version
If Python version mismatch:
```bash
pyenv install 3.11
pyenv local 3.11
make install
```

## No Migration Needed
Amplifier repo is straightforward - just pull and install.
