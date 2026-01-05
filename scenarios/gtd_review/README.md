# GTD Weekly Review Tool

**Status:** In Development
**Purpose:** AI-powered weekly review system for GTD workflow

## Overview

This scenario implements a weekly GTD review tool that:
- Loads items from multiple sources (reading queue, todos, calendar)
- Uses AI to recommend actions (complete, defer, delete, reschedule)
- Provides interactive CLI for making decisions
- Executes decisions on appropriate data sources
- Learns patterns from review history

## Architecture

Built as self-contained "bricks" following modular design philosophy:

```
gtd_review/
├── sources/           # Data source integrations
│   ├── base.py        # Abstract DataSource + ReviewItem
│   └── reading_queue.py
├── session/           # Review session management
│   └── schema.py      # Decision dataclass
├── review/            # Core review logic
│   ├── recommender.py # AI recommendations
│   ├── presenter.py   # Interactive CLI
│   └── orchestrator.py # Main workflow
├── actions/           # Action execution
│   └── executor.py    # Routes decisions to sources
└── analytics/         # Pattern analysis
    └── patterns.py    # Learn from history
```

## Public Interface

```python
from gtd_review import run_review

# Run interactive weekly review
await run_review()
```

## Data Sources

### Reading Queue (`sources/reading_queue.py`)

Integrates with `~/switchboard/data/reading-queue.json`:
- Loads unread/unarchived items
- Provides context (age, type, estimated time)
- Executes actions (complete, defer, delete, prioritize)

### Future Sources

- Todos (todotxt integration)
- Calendar (calendar events requiring decisions)
- Notes (Obsidian daily notes)

## AI Recommendations

Uses Claude Haiku for fast, intelligent recommendations:
- Analyzes item age, priority, context
- Considers past decision patterns
- Suggests appropriate action with confidence score
- Provides reasoning for transparency

## Interactive Presentation

Rich CLI interface shows:
- Item details with metadata
- AI recommendation with confidence
- Clear action choices
- Progress through review

## Pattern Learning

Analyzes review history to:
- Track completion/defer/delete rates
- Identify patterns in decision-making
- Generate actionable insights
- Improve future recommendations

## Design Philosophy

Following amplifier's modular design:
- **Self-contained bricks**: Each module is independent
- **Clear contracts**: Well-defined interfaces between modules
- **Regeneratable**: Can rebuild from specifications
- **Testable**: Each component tested in isolation

## Dependencies

- `amplifier.ccsdk_toolkit.claude_session`: AI recommendations
- `amplifier.ccsdk_toolkit.defensive`: Robust LLM response parsing
- `amplifier.utils.file_io`: Reliable file operations
- `rich`: Beautiful CLI presentation

## Testing

```bash
# Run all tests
pytest scenarios/gtd_review/tests/

# Run specific test
pytest scenarios/gtd_review/tests/test_reading_queue.py -v
```

## Status

- [x] Base architecture designed
- [x] Data source abstractions
- [ ] Reading queue source
- [ ] AI recommender
- [ ] Interactive presenter
- [ ] Action executor
- [ ] Pattern analyzer
- [ ] Orchestrator
- [ ] CLI entry point
- [ ] Tests
- [ ] Documentation

## Next Actions

1. Implement all components
2. Add comprehensive tests
3. Wire together in orchestrator
4. Create CLI entry point
5. Test end-to-end workflow
6. Add more data sources (todos, calendar)
