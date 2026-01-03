# Chanoyu Retrieval Tool

Find sources and context for Japanese tea ceremony research from the Jikunyu Raku knowledge base.

## Overview

This CLI tool helps locate relevant primary sources when researching tea ceremony topics. It queries the concept-source index built from extracted learnings files in `~/switchboard/chanoyu/`.

## Usage

```bash
# From amplifier directory
uv run python -m scenarios.chanoyu_retrieval [command]
```

### Commands

#### `search` - Find sources about a concept or person

```bash
# Search for concepts
uv run python -m scenarios.chanoyu_retrieval search wabi
uv run python -m scenarios.chanoyu_retrieval search "korean-tea-bowls"

# Search for people
uv run python -m scenarios.chanoyu_retrieval search rikyu --type person
uv run python -m scenarios.chanoyu_retrieval search chojiro --type person -v  # verbose
```

Output shows sources with relevance badges:
- `[PRIMARY]` - Main source for this topic
- `[supporting]` - Additional relevant coverage
- `[mentioned]` - Topic appears in source
- `[learnings]` - Extracted learnings available

#### `context` - Get files to load for a research task

```bash
# Find files relevant to a research topic
uv run python -m scenarios.chanoyu_retrieval context "raku"
uv run python -m scenarios.chanoyu_retrieval context "wabi aesthetic"
uv run python -m scenarios.chanoyu_retrieval context "korean bowls" --max-files 3
```

Returns copy-paste ready file paths for loading into Claude context.

#### `sources` - List all indexed sources

```bash
# List all sources with learnings status
uv run python -m scenarios.chanoyu_retrieval sources

# List all indexed concepts
uv run python -m scenarios.chanoyu_retrieval sources --concepts

# List all indexed people
uv run python -m scenarios.chanoyu_retrieval sources --people

# Verbose with details
uv run python -m scenarios.chanoyu_retrieval sources -v
```

## Data Sources

The tool reads from:
- **Index**: `~/switchboard/chanoyu/_concept-source-index.json`
- **Learnings**: `~/switchboard/chanoyu/sources/jikunyu-raku/*/_learnings.md`

### Currently Indexed Sources (5 of 22)

| Year | Title | Author |
|------|-------|--------|
| 1933 | On Raku Ware | Raku Kichizaemon XIII |
| 1947 | Raku Tea Bowls: Essays from Seibien | Ōkōchi Masatoshi |
| 1955 | World Ceramics Collection Vol. 7 | Ed. Okuda Seiichi |
| 1967 | Tea Talk: Wabi and Sabi | Emori Nahiko |
| 1977 | Tea Ceramics and Their Masters | Raku Kichizaemon XIV |

## Integration with /chanoyu-letter

This tool is designed to support the `/chanoyu-letter` skill by providing:

1. **Pre-research**: Find relevant sources before writing
2. **Context loading**: Get exact file paths to add to Claude context
3. **Citation support**: Identify primary vs supporting sources

Example workflow:
```bash
# Find sources about seasonal topics
uv run python -m scenarios.chanoyu_retrieval search "hearth"

# Get files to load for robiraki letter
uv run python -m scenarios.chanoyu_retrieval context "robiraki winter"

# Then in Claude: load the suggested files and run /chanoyu-letter
```

## Extending the Index

To add more sources to the index:

1. Create `_learnings.md` in the source folder with YAML frontmatter
2. Run the index builder to regenerate `_concept-source-index.json`
3. The CLI will automatically pick up new entries

See `~/switchboard/chanoyu/_STRUCTURE.md` for learnings file format.
