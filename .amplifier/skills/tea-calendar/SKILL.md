---
name: tea-calendar
description: Tea ceremony calendar with Google Sheets sync and kimono tracking. Use when user asks about tea events, kimono schedule, or syncing tea calendar.
triggers:
  - tea ceremony
  - tea events
  - kimono schedule
  - chado
  - 茶道
  - 着物
  - sync tea calendar
---

# Tea Calendar Skill

Two-way sync between Google Sheet (source of truth) and Google Calendar for tea ceremony events, with kimono/attire tracking.

## When to Use

- User asks about upcoming tea events
- User wants to see kimono schedule
- User wants to sync tea calendar from sheet
- User asks "what tea events do I have?"
- User asks "when do I need to wear kimono?"

## Quick Usage

```python
from amplifier.skills import (
    get_tea_events,
    get_kimono_events,
    generate_kimono_table,
    sync_tea_calendar,
)

# Get all tea events
events = await get_tea_events()

# Get events requiring kimono
kimono = await get_kimono_events()

# Generate markdown table for kimono events
table = await generate_kimono_table()

# Sync from Google Sheet to Calendar
result = await sync_tea_calendar()
# Returns: {"created": N, "updated": N, "unchanged": N}
```

## CLI Commands

```bash
# List tea events from calendar
python -m amplifier.skills.tea_calendar list

# List only kimono events
python -m amplifier.skills.tea_calendar list --kimono

# Generate kimono table
python -m amplifier.skills.tea_calendar table

# Sync sheet to calendar
python -m amplifier.skills.tea_calendar sync

# Dry run sync (see what would happen)
python -m amplifier.skills.tea_calendar sync --dry-run

# Show events from sheet (source of truth)
python -m amplifier.skills.tea_calendar sheet
```

## Data Model

### TeaEvent
```python
@dataclass
class TeaEvent:
    date: date
    event: str           # 初釜, お稽古, etc.
    location: str        # 東京, 京都, etc.
    style: str           # 紋付袴, 黒紋付, or empty
    calendar_id: str     # Google Calendar event ID
    
    @property
    def requires_kimono(self) -> bool
    
    @property
    def tags(self) -> list[str]  # ["tea", "kimono", "紋付袴"]
```

## Google Sheet Format

The source spreadsheet should have these columns:

| Date | Event | Location | Style |
|------|-------|----------|-------|
| 2026/1/11 | 初釜 | 東京 | 紋付袴 |
| 2026/1/14 | 善田初釜 | 京都 | 紋付袴 |
| 2026/2/5 | お稽古 | 東京 | |

Default sheet ID: `1hOwDgfhrLkeJzUmEWoUlH63l7q54cH9vCvQRSt5b--Q`

## Calendar Event Format

Events are created with:
- **Title**: 🍵 {event name}
- **All-day**: Yes
- **Location**: From sheet
- **Description**:
  ```
  Location: 東京
  Attire: 紋付袴
  
  tags: tea, kimono, 紋付袴
  ```

## Tag System

Events are tagged in the description for easy filtering:
- `tags: tea` - All tea events
- `tags: tea, kimono` - Events requiring kimono
- `tags: tea, kimono, 紋付袴` - With specific attire type

## Attire Types

| Japanese | English | When |
|----------|---------|------|
| 紋付袴 | Montsuki hakama | Formal tea gatherings |
| 黒紋付 | Kuro-montsuki | Very formal (graduation, etc.) |
| (empty) | Casual | Practice (お稽古) |
