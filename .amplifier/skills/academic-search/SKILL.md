---
name: academic-search
description: Search academic papers via Semantic Scholar. Use when user wants to find research papers, look up citations, or explore academic literature.
version: 1.0.0
---

# Academic Search Skill

Search academic papers using Semantic Scholar API with authenticated access (100 req/min).

## When to Use

- User asks to "find papers about X" or "search for research on Y"
- User wants to look up a specific paper by DOI or title
- User asks about academic citations or references
- User wants recent research on a topic
- User mentions an author and wants their publications

## Python API (Preferred)

```python
from amplifier.skills.academic_search import search_papers, search_author, get_paper, search_recent

# Search for papers
papers = await search_papers("transformer attention mechanism", limit=10)
for p in papers:
    print(f"{p.title} ({p.year}) - {p.citation_count} citations")

# Search by author
papers = await search_author("Geoffrey Hinton", topic="deep learning")

# Get paper details by DOI
paper = await get_paper("10.1145/3453483.3454077")
print(paper.abstract)

# Search recent papers (last 2 years, sorted by citations)
papers = await search_recent("large language models", years_back=2, min_citations=10)
```

## CLI Interface

```bash
# Search for papers
python -m amplifier.skills.academic_search search "Sen no Rikyu tea ceremony" -n 10 -v

# Search by author
python -m amplifier.skills.academic_search author "Vikash Mansinghka" -t "probabilistic programming"

# Get paper details
python -m amplifier.skills.academic_search paper "10.1145/3453483.3454077"

# Recent papers on a topic
python -m amplifier.skills.academic_search recent "bayesian inference" -y 2 -c 5
```

## Paper Object

Each result is a `Paper` object with:
- `paper_id`: Semantic Scholar ID
- `title`: Paper title
- `authors`: List of author names
- `year`: Publication year
- `abstract`: Paper abstract
- `citation_count`: Number of citations
- `url`: Link to paper
- `doi`: DOI if available

## Authentication

Uses Semantic Scholar API key from `amplifier.utils.secrets`:
- Authenticated: 100 requests/minute
- Unauthenticated fallback: ~5-10 requests/minute

API key is retrieved automatically from:
1. Cache (~/.cache/amplifier/secrets/)
2. Apple Keychain ("Semantic Scholar API")
3. age-encrypted dotfiles
4. Environment variable (SEMANTIC_SCHOLAR_API_KEY)

## Examples

```bash
# Find papers about Japanese tea ceremony
python -m amplifier.skills.academic_search search "Sen no Rikyu wabi-sabi" -v

# Find recent ML papers with high citations
python -m amplifier.skills.academic_search recent "machine learning" -y 1 -c 100 -n 20

# Look up a specific paper
python -m amplifier.skills.academic_search paper "arXiv:2103.14030"
```

## Advantages Over MCP

- ✅ Works in subagents (MCP tools don't inherit to subagents)
- ✅ Uses Amplifier secrets system (age + Keychain)
- ✅ Pure Python, no Node.js dependency
- ✅ Works in scripts, cron jobs, SDK calls
- ✅ Simpler debugging and customization
