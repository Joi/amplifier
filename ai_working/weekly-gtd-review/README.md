# Weekly GTD Review CLI Tool

**Status**: ✅ Core implementation complete, ready for testing
**Location**: `ai_working/weekly-gtd-review/`
**Purpose**: Interactive weekly review of todos, reading queue, calendar, and presentations

## Overview

This tool implements a comprehensive GTD (Getting Things Done) weekly review workflow with AI-powered recommendations using Claude Haiku.

## Quick Start

```bash
# From the amplifier root directory
cd ai_working/weekly-gtd-review

# Install dependencies (if needed)
uv sync

# Run the review
python -m gtd_review.cli

# Or without resume (start fresh)
python -m gtd_review.cli --no-resume
```

## Features

- ✅ **Session persistence** - Resume from where you left off
- ✅ **Multi-source review** - Reminders, Reading Queue (Calendar coming soon)
- ✅ **AI-powered recommendations** - Claude Haiku analyzes each item
- ✅ **Interactive decisions** - You make the final call
- ✅ **Pattern learning** - Gets smarter from your review history
- ✅ **Beautiful CLI** - Rich formatting and clear presentation
- ⏳ **Gmail integration** (planned)
- ⏳ **Google Calendar** (planned)

## Architecture

Built following the "bricks and studs" modular design philosophy. See `IMPLEMENTATION.md` for details.

### Core Components

```
gtd_review/
├── session/         # Session management brick
│   ├── schema.py   # Data models
│   └── manager.py  # Persistence logic
├── sources/         # Data source bricks
│   ├── base.py     # Contract interface
│   ├── reminders.py
│   └── reading_queue.py
├── review/          # AI recommendation brick
│   ├── recommender.py  # Claude Haiku integration
│   └── presenter.py    # Rich CLI interface
├── actions/         # Execution brick
│   └── executor.py
├── analytics/       # Pattern analysis brick
│   └── patterns.py
├── orchestrator.py  # Workflow coordinator
└── cli.py          # Entry point
```

**Design Philosophy**: Each brick is self-contained with a clear contract, making it easy to:
- Test in isolation
- Replace implementations
- Add new data sources
- Regenerate from spec

## Data Sources

### Apple Reminders
- **Reads from**: `~/switchboard/reminders/reminders_cache.json`
- **Updates**: Via obs-dailynotes sync (TODO: implement direct updates)
- **Context**: Shows age, overdue status, list name

### Reading Queue
- **Reads from**: `~/switchboard/data/reading-queue.json`
- **Updates**: Direct JSON modification
- **Context**: Shows age, source, category

### Google Calendar (Coming Soon)
- Will integrate via Google Calendar API
- Show upcoming meetings
- Identify scheduling conflicts

## Usage

### Basic Workflow

1. **Start Review**
   ```bash
   python -m gtd_review.cli
   ```

2. **For Each Item**:
   - See item details and AI recommendation
   - Choose action:
     - `1` - Complete (mark as done)
     - `2` - Defer to next week
     - `3` - Delete (remove entirely)
     - `4` - Reschedule (pick new date)
     - `5` - Change priority
     - `s` - Skip for now
     - `q` - Quit review

3. **Progress Saved**
   - Every decision saved immediately
   - Can resume anytime with `--resume`

4. **Review Insights**
   - See patterns in your decisions
   - Completion rate, defer rate
   - Action distribution

### Command Line Options

```bash
# Resume from previous session (default)
python -m gtd_review.cli --resume

# Start fresh session
python -m gtd_review.cli --no-resume

# Filter sources (future)
python -m gtd_review.cli --sources reminders,reading
```

## Session Management

Sessions are saved in `~/Library/Application Support/amplifier/data/gtd-review/sessions/`

**Session includes**:
- Current position (source, index)
- All reviewed items
- All decisions made
- Completion status

**Resume capability**:
- Automatic on restart
- Skips already-reviewed items
- Preserves all history

## AI Recommendations

Uses **Claude 3.5 Haiku** for fast, cost-effective recommendations.

**AI considers**:
- Item age and overdue status
- Your past decision patterns
- Item priority and tags
- Source-specific context

**Recommendation includes**:
- Suggested action
- Reasoning (1-2 sentences)
- Confidence level (0-100%)
- Suggested date/priority

You always make the final decision!

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gtd_review

# Run specific test
pytest tests/test_session.py -v
```

**Current test coverage**: 18 tests passing (session, reminders, reading queue)

## Development

### Adding a New Data Source

1. **Create source file**: `sources/my_source.py`
2. **Implement interface**:
   ```python
   from .base import DataSource, ReviewItem

   class MySource(DataSource):
       def name(self) -> str:
           return "my_source"

       async def load_items(self) -> list[ReviewItem]:
           # Load items from your source
           pass

       async def execute_action(self, item, action, **kwargs):
           # Execute user decision
           pass

       def get_context(self, item) -> dict:
           # Return AI context
           pass
   ```

3. **Wire it up** in `cli.py`:
   ```python
   from .sources.my_source import MySource

   sources = [
       RemindersSource(),
       ReadingQueueSource(),
       MySource(),  # Add here
   ]
   ```

4. **Test it**:
   ```python
   # tests/test_my_source.py
   import pytest
   from gtd_review.sources.my_source import MySource

   @pytest.mark.asyncio
   async def test_load_items():
       source = MySource()
       items = await source.load_items()
       assert isinstance(items, list)
   ```

### File Structure

All source-specific code stays in the source's file. No cross-source dependencies except through the base contract.

## Next Steps

1. ✅ **Test with real data** - Run a complete review session
2. ⏳ **Calendar source** - Google Calendar integration
3. ⏳ **Gmail integration** - Review inbox and follow-ups
4. ⏳ **Slash command** - `.claude/commands/weekly-review.md`
5. ⏳ **Make target** - `make weekly-review`
6. ⏳ **Graduate to scenarios/** - After validation
7. ⏳ **Full documentation** - Model after `blog_writer`

## Troubleshooting

### "No items to review"
- Check that data files exist:
  - `~/switchboard/reminders/reminders_cache.json`
  - `~/switchboard/data/reading-queue.json`
- Verify files contain incomplete items

### Import errors
- Run from `ai_working/weekly-gtd-review/` directory
- Or add to PYTHONPATH: `PYTHONPATH=. python -m gtd_review.cli`

### AI recommendation fails
- Check Anthropic API key is set
- Verify internet connection
- Falls back to "defer" with confidence 0

### Session not resuming
- Check session file: `~/Library/Application Support/amplifier/data/gtd-review/sessions/current_session.json`
- Use `--no-resume` to force new session

## Dependencies

- **amplifier** - Core toolkit (logging, file I/O, config)
- **pydantic-ai** - AI agent framework
- **rich** - Beautiful CLI presentation
- **click** - Command line interface

## Philosophy

Built following amplifier CLI tool patterns:
- Modular "bricks and studs" architecture
- Defensive file I/O with retries
- Structured logging throughout
- Session-based persistence
- AI-powered intelligence where helpful

See `@scenarios/blog_writer/` for documentation standards to match.

## Contributing

When adding features:
1. Keep bricks self-contained
2. Define contracts clearly
3. Test in isolation
4. Update this README
5. Add to IMPLEMENTATION.md

## License

Part of the Amplifier project.
