# Person Files Structure Exploration Summary

## Overview

Located 880 person markdown files in `~/switchboard/Private/People/` containing a rich social graph of relationships, interactions, and interests. Total file size: ~18,296 lines across all person files.

## 1. Frontmatter Schema

### Standard Fields
All person files follow a consistent YAML frontmatter structure:

```yaml
---
type: 'person'           # Always 'person'
slug: 'username-slug'    # Kebab-case identifier
id: 'person:slug-name'   # Namespaced unique identifier
emails:                  # Optional array of email addresses
  - 'email@domain.com'
  - 'alternate@email.com'
aliases:                 # Optional alternative names
  - 'common-name'
---
```

### Example from Actual Files

**adam-back.md**:
```yaml
---
type: 'person'
slug: 'adam-back'
id: 'person:adam-back'
emails:
  - 'adam@blockstream.io'
  - 'adam@cypherspace.org'
---
```

**adrianna-ma.md**:
```yaml
---
type: 'person'
slug: 'adrianna-ma'
id: 'person:adrianna-ma'
emails:
  - 'adrianna.ma@gmail.com'
---
```

## 2. Content Structure

All person files follow a consistent section-based structure. Sections are marked with markdown headers (####) and contain human-readable information:

### Section Patterns

**Always Present Sections**:
- `#### Relationship Summary` - Overview of the relationship with date range and key topics
- `#### Recent Interactions` - Timestamped interactions from Gmail/Mail with links
- `#### How we met` - Origin story of how the relationship began
- `#### Recent Interests` - List of topics the person is interested in

**Optional/Conditional Sections**:
- `#### Connected People` - Other people you're both connected to
- `#### Projects` - Active projects person is involved in
- `#### Expertise Areas` - Domains where person has recognized expertise

## 3. Real-World Examples

### Example 1: adam-back.md (Sparse Profile)

```markdown
---
type: 'person'
slug: 'adam-back'
id: 'person:adam-back'
emails:
  - 'adam@blockstream.io'
  - 'adam@cypherspace.org'
---

PRIVATE_NOTES

#### Relationship Summary
- Email history spans 2020-04-06 to 2021-11-24 (13 messages indexed).
- Topics discussed include: `Some CAO/Defi/NFT links` (2021), `[bitcoin-dev] Yesterday's Taproot activation meeting on lockinontimeout (LOT)` (2021), `Liquid` (2021), `[bitcoin-dev] BIP32/43-based standard for Schnorr signatures & decentralized identity` (2021), `[bitcoin-dev] Deterministic Entropy From BIP32 Keychains` (2020).
- Connected people (inferred from headers, may be uncertain): Karl-Johan Alm (2021), Joichi Ito (2021), Taro Watanabe (2021), Matt Corallo via bitcoin-dev (2021), Bitcoin Protocol Discussion (2020–2021), ZmnSCPxj (2021), Dr Maxim Orlovsky via bitcoin-dev (2021), Christopher Allen via bitcoin-dev (2020).

#### How we met
- Uncertain; possibly connected via Karl-Johan Alm (inferred from headers).

#### Recent Interests
- Some CAO/Defi/NFT links (2021)
- [bitcoin-dev] Yesterday's Taproot activation meeting on lockinontimeout (LOT) (2021)
- Liquid (2021)
- [bitcoin-dev] BIP32/43-based standard for Schnorr signatures & decentralized identity (2021)
- [bitcoin-dev] Deterministic Entropy From BIP32 Keychains (2020)
```

### Example 2: adrianna-ma.md (Rich Profile with Temporal Data)

```markdown
---
type: 'person'
slug: 'adrianna-ma'
id: 'person:adrianna-ma'
emails:
  - 'adrianna.ma@gmail.com'
---

PRIVATE_NOTES

#### Relationship Summary
- Email history spans 2020-01-18 to 2025-01-03 (20 messages indexed).
- Topics discussed include:
  - Carta - Questions - Neoteny 3+4 (2020)
  - New Role at CIT: A New Chapter Begins (2023)
  - SVB Update from Neoteny (2023)
  - Neoteny Annual Meeting: Save the Date (2020)
  - Contact Info (2020)
  - Your Card (2020)
  - 2025 New Year Update (2025)
  - Happy New Year! (2022)

#### Recent Interactions (links open in Mail.app)
- 2025-01-03 — 2025 New Year Update [Mail](...) [Gmail](...)
- 2023-07-01 — New Role at CIT: A New Chapter Begins [Mail](...) [Gmail](...)
- 2023-03-11 — SVB Update from Neoteny [Mail](...) [Gmail](...)
- 2022-12-31 — Happy New Year! [Mail](...) [Gmail](...)
- 2020-12-01 — Contact Info [Mail](...) [Gmail](...)

#### How we met
- Uncertain; possibly connected via Adam Mullinax (inferred from headers).

#### Recent Interests
- Carta - Questions - Neoteny 3+4 (2020)
- New Role at CIT: A New Chapter Begins (2023)
- SVB Update from Neoteny (2023)
- Neoteny Annual Meeting: Save the Date (2020)
- Contact Info (2020)
```

### Example 3: ado-machida.md (Events-Focused)

```markdown
---
type: 'person'
slug: 'ado-machida'
id: 'person:ado-machida'
emails:
  - 'ado.machida@hardrock.com'
---

PRIVATE_NOTES

#### Relationship Summary
- Email history spans 2025-03-26 to 2025-05-12 (20 messages indexed).
- Topics discussed include:
  - [External Email]  Re: Machida Dinner Party (4/12) (2025)
  - [External Email]  Dress Code Tonight (2025)
  - Smithsonian Museum Reception (5/27) (2025)
  - [External Email]  デジタルガレージ 30周年記念パーティーのご案内（7月1日(火) 18:00より） (2025)

#### Recent Interactions (links open in Mail.app)
- 2025-05-12 — Smithsonian Museum Reception (5/27) [Mail](...) [Gmail](...)
- 2025-04-28 — [External Email] デジタルガレージ 30周年記念パーティー... [Mail](...) [Gmail](...)
- 2025-04-13 — [External Email] Dress Code Tonight [Mail](...) [Gmail](...)
- 2025-04-12 — [External Email] Dress Code Tonight [Mail](...) [Gmail](...)

#### How we met
- Uncertain; possibly connected via Machida (inferred from headers).

#### Recent Interests
- [External Email]  Re: Machida Dinner Party (4/12) (2025)
- [External Email]  Dress Code Tonight (2025)
- Smithsonian Museum Reception (5/27) (2025)
```

## 4. Relationship Data Format

Current relationship representations use **prose-based inference** rather than structured data:

### Current Format (Prose)

```markdown
#### Relationship Summary
- Email history spans 2020-04-06 to 2021-11-24 (13 messages indexed).
- Topics discussed include: `topic1` (year), `topic2` (year)
- Connected people (inferred from headers): Person A (year), Person B (year), Person C (year)

#### How we met
- Uncertain; possibly connected via Some Person (inferred from headers).
```

### Key Characteristics

1. **Temporal**: Email date ranges, message counts, year annotations
2. **Inferred**: Relationships parsed from email headers, not explicitly stored
3. **Contextual**: Includes email subjects and topics as relationship context
4. **Human-Readable**: Designed for human reading, not machine parsing
5. **Uncertain**: Explicitly notes when inference is low-confidence

### Data Quality Issues

- **"Uncertain"** qualifier appears frequently - relationships marked as inferred, not confirmed
- **No relationship strength** - No numerical representation of relationship closeness
- **No explicit link types** - All relationships represented as prose, not typed edges
- **Scattered representation** - "Connected people" section mentions relationships but format varies
- **No directional info** - Doesn't distinguish "I know them" vs "They know me" vs "mutual"

## 5. Existing Graph Infrastructure

### Knowledge Graph System (obs-dailynotes)

Located at: `/Users/joi/obs-dailynotes/lib/knowledgeGraph/`

**Status**: Phase 1 - Foundation structure created (all files empty stubs as of Nov 12, 2025)

**Design (from README.md)**:

**Node Types**:
- Person (880+ from Private/People/)
- Organization
- Paper (academic literature)
- Idea/Topic
- Meeting
- Project

**Edge Types**:
```
Person ↔ Person: knows, worked-with, introduced-by, discussed-with
Person ↔ Organization: works-at, founded, advises
Person/Paper ↔ Paper: authored, cited, discussed
Person ↔ Idea: interested-in, working-on, expert-in
Meeting ↔ Person/Idea: attended, discussed
```

**Storage Format** (NetworkX-compatible JSON):
```json
{
  "directed": true,
  "multigraph": true,
  "graph": {},
  "nodes": [
    {
      "id": "person:joi-ito",
      "type": "person",
      "name": "Joi Ito",
      "slug": "joi-ito",
      "emails": ["joi@example.com"],
      "filePath": "Private/People/Joi Ito.md"
    }
  ],
  "links": [
    {
      "source": "person:joi-ito",
      "target": "person:neha-narula",
      "type": "knows",
      "strength": 0.9,
      "firstContact": "2015-03-15",
      "lastContact": "2025-11-10",
      "context": ["meeting:2025-11-10-lab-sync"]
    }
  ]
}
```

**Planned Modules**:
- `graphBuilder.js` - Extract entities and relationships from markdown
- `extractors.js` - Entity-specific parsers
- `graphQuery.js` - Query interface (path finding, expert search, etc.)
- `models.js` - Data structures and validation
- `index.js` - Main API and CLI

**Planned Features**:
- Find connection paths between people
- Find experts by topic
- Suggest introductions
- Relationship timelines
- Community detection
- Ego network visualization

### Amplifier DAG Loader

Located at: `/Users/joi/amplifier/tools/dag_loader.py`

**Purpose**: Loads Claude Code session JSONL files and builds conversation DAG structures

**Relevant Data Structures**:
```python
@dataclass
class Message:
    uuid: str
    type: str  # user, assistant, system
    parent_uuid: str | None
    content: Any
    timestamp: datetime | None = None
    is_sidechain: bool = False
    metadata: dict[str, Any]

@dataclass
class SessionData:
    messages: dict[str, Message]
    parent_child_map: dict[str, list[str]]  # Parent → [children]
    root_messages: list[str]
```

**Could be adapted for**: Building relationship DAGs, connection paths, conversation graphs

## 6. Key Insights for Graph Building

### Strengths of Current Person Files

1. **Rich temporal data** - Email date ranges, message counts, interaction history
2. **Inferred relationships** - Email headers already extract connected people
3. **Topic tagging** - Recent interests are captured and timestamped
4. **Consistent structure** - All files follow same section patterns
5. **880 nodes ready** - Complete person dataset available for graph construction
6. **Email context** - Links to Gmail/Mail for relationship context

### Challenges to Address

1. **Inference uncertainty** - Many relationships marked "Uncertain; possibly connected via..."
2. **No explicit strength** - No way to distinguish strong vs weak relationships
3. **Unidirectional inference** - Extracted from email headers, not mutual confirmations
4. **Scattered prose** - Need NLP to extract structured relationship types from text
5. **No explicit link types** - All "knows" relationships, but could be "worked-with", "advised-by", etc.
6. **Missing person profiles** - Only 880 of potentially 2000+ referenced people have files

### Building Blocks Available

1. **Email history**: Date ranges, message counts, topics for relationship strength
2. **Topic overlap**: Same interests as weak tie indicator
3. **Co-mention**: People mentioned together as introduction path indicator
4. **Temporal continuity**: Recency as relationship strength factor
5. **Organization inference**: Email domains as organization membership
6. **Interaction frequency**: Message count as engagement metric

## 7. Template Structure

Found at: `/Users/joi/switchboard/Private/People/person-quick.md`

```yaml
---
type: 'person'
slug: 'person-quick'
id: 'person:person-quick'
aliases:
  - 'person'
  - 'person (quick)'
---

PRIVATE_NOTES
#### Recent Interactions (Gmail)
- None

#### How we met
- Unknown

#### Connected People
- None

#### Recent Interests
- None
```

Minimal but complete - shows the four essential sections for any person profile.

## Data Statistics

- **Total person files**: 880
- **Total lines**: ~18,296 across all files
- **Average per file**: ~21 lines (very compact)
- **Frontmatter size**: ~4-6 lines consistently
- **Content patterns**: Highly standardized sections
- **Email coverage**: Most files have 1-3 email addresses
- **Temporal range**: Email histories span 5-10+ years (2015-2025)

## Recommendations for Graph Implementation

1. **Start with structured extraction**: Use person file frontmatter as initial node data
2. **Infer edge strength**: Calculate from email message counts, recency, topic overlap
3. **Extract link types**: Parse "Relationship Summary" and "How we met" for typed edges
4. **Build confidence scores**: Track inference certainty (marked vs inferred vs explicit)
5. **Implement incremental updates**: Watch person files for changes, update graph live
6. **Leverage existing architecture**: Use obs-dailynotes knowledge graph stubs as foundation
7. **Add NLP enrichment**: Parse prose sections to extract structured relationship types

## Files to Integrate With

- `~/switchboard/Private/People/*.md` - 880 person nodes (primary data source)
- `~/obs-dailynotes/lib/knowledgeGraph/` - Graph system stubs (foundation ready)
- `~/amplifier/tools/dag_loader.py` - DAG/graph utilities (can reuse patterns)
- `~/switchboard/_Index_of_knowledge_graph.md` - Index page setup (Dataview ready)
