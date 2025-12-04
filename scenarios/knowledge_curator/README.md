# Knowledge Curator

**Wikipedia-editor style agent for knowledge vaults.**

Transform your Switchboard vault from a personal note collection into a well-sourced, verified knowledge base.

## The Problem

You have markdown files full of claims, facts, and ideas - but:
- Many lack citations or sources
- You don't know which claims need verification
- Finding and adding sources is tedious manual work
- There's no visibility into knowledge quality

## The Solution

Knowledge Curator acts like a Wikipedia editor for your vault:
1. **Scans** files to identify claims needing citations
2. **Searches** academic databases for authoritative sources
3. **Adds** citations in Obsidian-compatible format
4. **Reports** status in your daily notes

## Quick Start

```bash
# Process entire vault
make knowledge-curate VAULT=~/switchboard

# Process specific domain
make knowledge-curate VAULT=~/switchboard DOMAIN=chanoyu/

# Resume interrupted run
make knowledge-curate VAULT=~/switchboard --resume

# Report only (no modifications)
make knowledge-curate VAULT=~/switchboard --report-only
```

## Features

### Incremental Processing
- Saves progress after each file
- Resume from interruption with `--resume`
- Never lose work on long-running jobs

### Daily Notes Integration
- Shows items needing attention in daily notes
- Displays recent curation activity
- Links to full knowledge status report

### Academic Source Search
- Integrates with paper-search MCP server
- Searches Semantic Scholar, arXiv, Google Scholar
- Finds relevant citations automatically

### Citation Formats

**Footnote style** (default, best for academic content):
```markdown
According to research on complex systems[^1], emergence occurs when...

[^1]: Holland, J. (1998). *Emergence: From Chaos to Order*. Basic Books.
```

**Inline style** (for quick references):
```markdown
The concept of wabi-sabi emphasizes imperfection ([Koren 1994](https://example.com)).
```

## Pipeline Stages

| Stage | Purpose | Output |
|-------|---------|--------|
| **Scan** | Extract claims from markdown | `claims_found` per file |
| **Search** | Find authoritative sources | `sources` matched to claims |
| **Cite** | Add citations to files | Modified markdown files |
| **Report** | Generate status report | `knowledge-status.json` |

## Configuration

```bash
# State directory for resume capability
--state-dir ~/.data/knowledge_curator

# Output file for daily notes integration
--status-file ~/switchboard/amplifier/knowledge-status.json

# Enable verbose logging
--verbose
```

## Daily Notes Integration

After running, your daily note shows:

```markdown
## 📚 Knowledge Status

### Needs Attention
- 🟡 [[chanoyu/concepts/ichigo-ichie|Ichigo Ichie]] - uncited claims
- 🔴 [[Literature/Scholars/Negroponte|Negroponte]] - outdated info

### Recent Curation
- ✅ [[chanoyu/concepts/wabi|Wabi]] - added 4 citations (Dec 4)

_Last analysis: Dec 4 • [[amplifier/KNOWLEDGE-STATUS|Full Report]]_
```

## Architecture

```
knowledge_curator/
├── main.py              # CLI entry point
├── state.py             # State management for resume
├── claim_extractor/     # Stage 1: Find claims
├── source_searcher/     # Stage 2: Search sources
├── citation_adder/      # Stage 3: Add citations
└── gap_reporter/        # Stage 4: Generate report
```

## How It Was Built

This tool follows the Amplifier scenario pattern:
1. Define the metacognitive recipe (how to think through curation)
2. Let Amplifier implement the pipeline stages
3. Integrate with existing daily notes workflow

The recipe:
1. "Read each file and identify claims that would benefit from citations"
2. "For each claim, search academic databases for relevant sources"
3. "Add citations in Obsidian-compatible format"
4. "Report which files still need attention"

## Related

- [KNOWLEDGE-CURATOR.md](~/switchboard/amplifier/KNOWLEDGE-CURATOR.md) - Project documentation
- [Daily Notes Integration](~/obs-dailynotes) - Where status appears
- [paper-search MCP](../README.md) - Academic search integration

## Status

**Experimental** - Core pipeline working, academic search integration in progress.
