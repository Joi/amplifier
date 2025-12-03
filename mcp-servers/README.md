# Amplifier MCP Servers

**Centralized MCP servers available to all Amplifier projects**

## Purpose

This directory contains Model Context Protocol (MCP) servers that provide Claude Code with access to external tools and data sources. These servers are shared across all Amplifier projects.

## Installed Servers

### 1. Academic Search MCP
**Repository:** https://github.com/afrise/academic-search-mcp-server
**Path:** `academic-search/`

**Features:**
- Semantic Scholar API integration (academic paper database)
- Crossref API integration (DOI resolution, metadata)
- Tools available in Claude:
  - `search_papers` - Query academic papers
  - `fetch_paper_details` - Get comprehensive paper metadata
  - `search_by_topic` - Topic-based search with date filtering

**API Keys (Optional but Recommended):**
- Semantic Scholar: https://www.semanticscholar.org/product/api
- Crossref: https://www.crossref.org/documentation/metadata-api/

**Configuration:** See Claude Desktop config below

---

### 2. Paper Search MCP
**Repository:** https://github.com/openags/paper-search-mcp
**Path:** `paper-search/`

**Features:**
- Multi-database academic paper search
- Databases supported:
  - arXiv (physics, CS, math preprints)
  - PubMed (biomedical literature)
  - bioRxiv (biology preprints)
  - medRxiv (medical preprints)
  - Google Scholar
  - IACR ePrint Archive (cryptography)
  - Semantic Scholar
- Paper download capabilities
- No API keys required

**Configuration:** See Claude Desktop config below

---

## Configuration

### For Claude Code (Recommended)

Add MCP servers using the CLI:

```bash
# Academic Search MCP
claude mcp add --transport stdio academic-search -- \
  /Users/joi/amplifier/mcp-servers/academic-search/.venv/bin/python \
  /Users/joi/amplifier/mcp-servers/academic-search/server.py

# Paper Search MCP
claude mcp add --transport stdio paper-search -- \
  /Users/joi/amplifier/mcp-servers/paper-search/.venv/bin/python \
  -m paper_search_mcp.server
```

**Verify connection:**
```bash
claude mcp list
```

You should see:
```
academic-search: ... - ✓ Connected
paper-search: ... - ✓ Connected
```

**Configuration Location:** `~/.claude.json` (per project)

---

### For Claude Desktop (Alternative)

Location: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "academic-search": {
      "command": "/Users/joi/amplifier/mcp-servers/academic-search/.venv/bin/python",
      "args": [
        "/Users/joi/amplifier/mcp-servers/academic-search/server.py"
      ],
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "",
        "CROSSREF_API_KEY": ""
      }
    },
    "paper-search": {
      "command": "/Users/joi/amplifier/mcp-servers/paper-search/.venv/bin/python",
      "args": [
        "-m",
        "paper_search_mcp.server"
      ]
    }
  }
}
```

**Important:** Restart Claude Desktop after editing the config file.

**Note:** Claude Code and Claude Desktop are separate environments with different configurations.

---

## Installation Details

Both servers are installed with isolated Python virtual environments:

```bash
# Academic Search MCP
cd ~/amplifier/mcp-servers/academic-search
uv venv
source .venv/bin/activate
uv pip install "mcp[cli]" httpx

# Paper Search MCP
cd ~/amplifier/mcp-servers/paper-search
uv venv
source .venv/bin/activate
uv pip install -e .
```

---

## Usage Examples

Once Claude Desktop is restarted, these tools are available in all conversations:

### Academic Search Examples

```
# Search by author
Search for papers by "Vikash Mansinghka" on probabilistic programming

# Search by topic with date range
Search for papers on "bayesian inference" from 2020-2025

# Get detailed paper information
Fetch details for paper with DOI: 10.1145/3453483.3454077
```

### Paper Search Examples

```
# Search specific database
Search arXiv for "Gen probabilistic programming"

# Multi-database search
Find papers on "term sheet valuation" across all databases

# Download papers
Download papers on "Bayesian finance" from arXiv
```

---

## Projects Using These Servers

- **term-sheet-value** - Probabilistic programming for term sheet valuation
- Available to all future Amplifier projects

---

## Maintenance

### Updating Servers

```bash
cd ~/amplifier/mcp-servers/academic-search
git pull

cd ~/amplifier/mcp-servers/paper-search
git pull
source .venv/bin/activate
uv pip install -e .
```

### Adding New Servers

1. Clone server repository to `~/amplifier/mcp-servers/[server-name]/`
2. Set up virtual environment and dependencies
3. Add configuration to Claude Desktop config
4. Restart Claude Desktop
5. Document in this README

---

## Troubleshooting

### Claude Code: MCP Tools Status (Updated 2025-11-28)

**Current Status:** ✅ **WORKING** in main session | ❌ **Subagents still broken**

**Main Session:** MCP tools are now fully accessible! You can use all tools directly:
```
# These all work in the main Claude Code session:
mcp__academic-search__search_papers
mcp__paper-search__search_arxiv
mcp__paper-search__search_semantic
# etc.
```

**Subagents (Task tool):** MCP tools are NOT inherited by subagents launched via Task tool.
- GitHub Issue #7296 remains open
- Workaround: Perform MCP searches in main session, not via delegated agents

### If MCP Tools Still Don't Work

1. **Check configuration location:** Must be in `~/.claude.json` or project `.mcp.json` (NOT `~/.claude/settings.json`)
2. **Verify connection:** Run `claude mcp list` - servers should show "✓ Connected"
3. **Restart Claude Code:** Sometimes needed after config changes
4. **Check tool names:** Use exact format `mcp__server-name__tool_name`

### Subagent MCP Access (Known Issue)

**Symptom:** Subagents report "I cannot see or access the MCP tools" despite main session having access.

**Status:** Known bug (GitHub #7296), no fix yet.

**Workaround:** Use MCP tools in main session only. For delegated research tasks, subagents will fall back to WebSearch/WebFetch.

**Investigation details:** See `~/term-sheet-value/MCP-STATUS.md` for full analysis.

---

### Claude Desktop: MCP Server Not Appearing
- Ensure Claude Desktop was restarted after config changes
- Check `claude_desktop_config.json` for valid JSON syntax
- Verify file paths are absolute and correct
- Check virtual environment is activated and dependencies installed

### Rate Limiting
- **Without API keys:** ~5-10 requests/min for Semantic Scholar
- **With API keys:** 100 requests/min for Semantic Scholar
- **Solution:** Add API keys to config or pace requests

### SSL/Certificate Errors
- Some academic sites have SSL issues
- Use alternative databases via Paper Search MCP
- Check if VPN/proxy is interfering

---

## Security Notes

- API keys stored in Claude Desktop config (not version controlled)
- Virtual environments isolated per server
- No sensitive data stored in this directory
- PDF downloads go to project-specific directories (gitignored)

---

**Last Updated:** 2025-11-28
**Maintained By:** Amplifier team
