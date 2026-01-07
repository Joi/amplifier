# External Integration Tools - Migration Analysis

**Date:** 2026-01-07
**Status:** Analysis Complete
**Scope:** Commands, Scenarios, and Scripts with External Dependencies

---

## Executive Summary

This analysis covers **5 commands**, **13 scenarios**, and **11 scripts/hooks** for migration to Amplifier CLI. The overall picture is positive:

- **Most scenarios already work** - They're native Amplifier scenario tools
- **Commands need conversion** - From Claude Code `.md` format to Amplifier recipes/skills
- **Scripts are mixed** - Some already integrated, some need registration as tool modules
- **External dependencies are manageable** - Most use APIs already integrated or simple system calls

### Key Findings

| Category | Count | Already Works | Needs Migration | Blocked |
|----------|-------|---------------|-----------------|---------|
| Commands | 5 | 0 | 5 | 0 |
| Scenarios | 13 | 13 | 0 | 0 |
| Scripts/Hooks | 11 | 9 | 2 | 0 |

**Total Effort Estimate:** 20-35 hours

---

## Migration Chart

### Commands

| Name | Type | External Dependencies | Internal Dependencies | Migration Path | Effort | Risk | Key Questions |
|------|------|----------------------|----------------------|----------------|--------|------|---------------|
| `morning.md` | Command | Apple Reminders, Notes.app, Obsidian | obs-dailynotes npm scripts | **Recipe** | Medium | Low | Should npm scripts be called directly or wrapped? |
| `chanoyu-add.md` | Command | None | Obsidian vault (~switchboard/chanoyu) | **Skill** | Low | Low | Keep as file-based or add vault validation? |
| `chanoyu-letter.md` | Command | None | Obsidian vault templates, SEASONS.md | **Skill** | Medium | Low | How to handle interactive questionnaire flow? |
| `apple-note.md` | Command | Apple Notes (osascript) | tools/apple_notes.py | **Custom Tool Module** | Low | Low | Register apple_notes.py as Amplifier tool? |
| `imagen.md` | Command | Google Gemini API | tools/imagen.py | **Custom Tool Module** | Low | Low | Already has imagen.py - just needs registration |

### Scenarios

| Name | Type | External Dependencies | Internal Dependencies | Migration Path | Effort | Risk | Key Questions |
|------|------|----------------------|----------------------|----------------|--------|------|---------------|
| `gtd_review/` | Scenario | Apple Reminders (indirect), Claude API | amplifier.ccsdk_toolkit, rich | **Already Works** | N/A | N/A | In development - complete implementation first |
| `chanoyu_retrieval/` | Scenario | None | Obsidian vault index JSON | **Already Works** | N/A | N/A | None |
| `blog_extract/` | Scenario | Claude API | amplifier.utils.logger | **Already Works** | N/A | N/A | None |
| `blog_integrate/` | Scenario | None | amplifier.utils.logger | **Already Works** | N/A | N/A | None |
| `blog_poster/` | Scenario | **Notion API (MCP)** | MCP notion-* tools | **Already Works** | N/A | Medium | Requires Notion MCP server configured |
| `blog_synthesize/` | Scenario | None | amplifier.utils.logger | **Already Works** | N/A | N/A | None |
| `blog_writer/` | Scenario | Claude API | amplifier modules | **Already Works** | N/A | N/A | None |
| `knowledge_curator/` | Scenario | **Semantic Scholar, arXiv (MCP)**, Claude API | paper-search MCP | **Already Works** | N/A | Medium | Requires paper-search MCP server |
| `transcribe/` | Scenario | YouTube (yt-dlp), **OpenAI Whisper API**, Claude API | ffmpeg (system) | **Already Works** | N/A | Low | Requires yt-dlp, ffmpeg installed |
| `ideas_tracker/` | Scenario | **GitHub** (ramparte/amplifier-ideas-data) | Git | **Already Works** | N/A | Low | Requires GitHub repo access |
| `article_illustrator/` | Scenario | **OpenAI GPT-Image-1**, **Google Imagen 4**, DALL-E 3 | amplifier modules | **Already Works** | N/A | Low | Requires API keys configured |
| `tips_synthesizer/` | Scenario | Claude API | amplifier modules | **Already Works** | N/A | N/A | None |
| `web_to_md/` | Scenario | Web (httpx) | markdownify, beautifulsoup4 | **Already Works** | N/A | N/A | None |

### Scripts/Hooks

| Name | Type | External Dependencies | Internal Dependencies | Migration Path | Effort | Risk | Key Questions |
|------|------|----------------------|----------------------|----------------|--------|------|---------------|
| `imagen.py` | Script | Google Gemini API (google-genai) | amplifier.utils.secrets | **Custom Tool Module** | Low | Low | Register as callable tool |
| `memory_cli.py` | Script | None | amplifier.memory | **Already Works** | N/A | N/A | Already uses Amplifier modules |
| `hook_logger.py` | Hook | None | None | **Already Works** | N/A | N/A | Utility for other hooks |
| `hook_post_tool_use.py` | Hook | None | amplifier.memory, .validation | **Already Works** | N/A | N/A | Memory system hook |
| `hook_precompact.py` | Hook | None | hook_logger | **Already Works** | N/A | N/A | Transcript export |
| `hook_session_start.py` | Hook | tmux (optional) | amplifier.memory, .search | **Already Works** | N/A | N/A | Session tracking |
| `hook_stop.py` | Hook | None | amplifier.extraction, .memory | **Already Works** | N/A | N/A | Memory extraction |
| `on_code_change_hook.sh` | Hook | make (system) | None | **Already Works** | N/A | N/A | Build system hook |
| `on_notification_hook.py` | Hook | macOS notifications (osascript) | amplifier.utils.notifications | **Already Works** | N/A | N/A | Desktop notifications |
| `subagent-logger.py` | Hook | None | amplifier.config.paths | **Already Works** | N/A | N/A | Subagent logging |
| `apple_notes.py` | Script | Apple Notes (osascript) | None | **Custom Tool Module** | Low | Low | Register as callable tool |

---

## External Dependencies Inventory

### APIs Requiring Keys

| Service | Used By | Key Location | Status |
|---------|---------|--------------|--------|
| Google Gemini API | imagen.py, article_illustrator | `GOOGLE_API_KEY` or secrets system | Configured |
| OpenAI API | transcribe (Whisper), article_illustrator | `OPENAI_API_KEY` | Configured |
| Anthropic Claude API | Multiple scenarios | `ANTHROPIC_API_KEY` | Configured |

### MCP Servers Required

| MCP Server | Used By | Purpose |
|------------|---------|---------|
| `notion` | blog_poster | Create/update Notion pages |
| `paper-search` | knowledge_curator | Search academic databases |

### System Tools Required

| Tool | Used By | Installation |
|------|---------|--------------|
| `osascript` | apple_notes.py, on_notification_hook.py | macOS built-in |
| `ffmpeg` | transcribe | `brew install ffmpeg` |
| `yt-dlp` | transcribe | `uv add yt-dlp` |
| `make` | on_code_change_hook.sh | macOS built-in |
| `tmux` | hook_session_start.py | Optional, `brew install tmux` |

### External Data Sources

| Source | Used By | Access Method |
|--------|---------|---------------|
| Apple Reminders | morning.md, gtd_review | npm scripts (obs-dailynotes) |
| Apple Notes | apple-note.md, morning.md | osascript via apple_notes.py |
| Obsidian Vault | chanoyu-*, morning.md | Direct file access (~switchboard) |
| GitHub Repo | ideas_tracker | Git clone/push |
| Notion | blog_poster | MCP server |

---

## MCP Server Opportunities

### Currently Using MCP

1. **blog_poster** - Uses Notion MCP for page creation
2. **knowledge_curator** - Uses paper-search MCP for academic sources

### Potential MCP Candidates

| Tool | Current Method | MCP Opportunity | Benefit |
|------|----------------|-----------------|---------|
| Apple Notes | osascript calls | Apple Notes MCP | Unified interface, better error handling |
| Apple Reminders | npm scripts | Apple Reminders MCP | Direct integration, no npm dependency |
| Obsidian | File system | Obsidian MCP | Vault abstraction, link resolution |
| Google Imagen | Direct API | Image Generation MCP | Unified image API (DALL-E, Imagen, etc.) |

### Recommendation

**Low Priority for New MCP Servers** - Current implementations work well. Consider MCP consolidation only if:
- Multiple tools need the same service
- Error handling becomes complex
- Need cross-session state management

---

## Questions for Decision

### Architecture Decisions

1. **Tool Registration Pattern**
   - How should standalone scripts (imagen.py, apple_notes.py) be registered as Amplifier tools?
   - Should they be in `amplifier/tools/` or remain in user `tools/` directory?

2. **Recipe vs Skill for Commands**
   - morning.md is a sequence of bash commands - Recipe pattern
   - chanoyu-letter.md is interactive with conditional logic - Skill pattern
   - What's the boundary between Recipe and Skill in Amplifier?

3. **MCP Server Strategy**
   - Should Apple Notes/Reminders get their own MCP servers?
   - Or keep as simple osascript/npm wrappers?

### Configuration Questions

4. **Vault Paths**
   - chanoyu commands assume `~/switchboard/chanoyu/`
   - morning.md assumes `~/obs-dailynotes/` and `~/switchboard/`
   - Should these be configurable or hardcoded?

5. **API Key Management**
   - imagen.py uses `amplifier.utils.secrets.get_gemini_api_key()`
   - Is this the standard pattern for all API keys?

### Migration Strategy Questions

6. **Priority Order**
   - Start with low-effort, high-value items?
   - Or group by external dependency?

7. **Testing Strategy**
   - How to test Apple-specific tools (Notes, Reminders)?
   - Mock osascript calls or use integration tests?

---

## Recommended Migration Order

### Phase 1: Quick Wins (2-4 hours)
Low effort, immediate value

1. **Register `imagen.py` as Amplifier tool** (1 hr)
   - Already working, just needs registration
   - Used by imagen.md command

2. **Register `apple_notes.py` as Amplifier tool** (1 hr)
   - Standalone, well-tested
   - Used by apple-note.md command

3. **Convert `apple-note.md` to Recipe** (1 hr)
   - Simple command, calls apple_notes.py
   - Template conversion

### Phase 2: Content Commands (4-8 hours)
Vault-related commands

4. **Convert `chanoyu-add.md` to Skill** (2 hrs)
   - File-based operations
   - Needs vault path configuration

5. **Convert `chanoyu-letter.md` to Skill** (4 hrs)
   - Complex interactive flow
   - Seasonal logic
   - Template loading

### Phase 3: Integration Commands (4-8 hours)
External system integration

6. **Convert `morning.md` to Recipe** (4 hrs)
   - Multiple external systems
   - Depends on obs-dailynotes npm scripts
   - May need to port npm scripts or create wrappers

### Phase 4: Scenario Enhancement (Optional)
Already working but could be improved

7. **Complete gtd_review implementation** (8+ hrs)
   - Currently in development
   - All components designed

8. **Add Apple Notes MCP server** (4 hrs)
   - Only if multiple tools need it
   - Currently apple_notes.py works fine

---

## Appendix: File Locations

### Commands
```
.claude/commands/
  morning.md
  chanoyu-add.md
  chanoyu-letter.md
  apple-note.md
  imagen.md
```

### Scenarios
```
scenarios/
  gtd_review/          # In development
  chanoyu_retrieval/   # Working
  blog_extract/        # Working
  blog_integrate/      # Working
  blog_poster/         # Working (needs Notion MCP)
  blog_synthesize/     # Working
  blog_writer/         # Working
  knowledge_curator/   # Working (needs paper-search MCP)
  transcribe/          # Working
  ideas_tracker/       # Working
  article_illustrator/ # Working
  tips_synthesizer/    # Working
  web_to_md/           # Working
```

### Scripts/Hooks
```
tools/
  imagen.py            # Needs registration
  memory_cli.py        # Working
  hook_logger.py       # Working (utility)
  hook_post_tool_use.py    # Working (hook)
  hook_precompact.py       # Working (hook)
  hook_session_start.py    # Working (hook)
  hook_stop.py             # Working (hook)
  on_code_change_hook.sh   # Working (hook)
  on_notification_hook.py  # Working (hook)
  subagent-logger.py       # Working (hook)
  apple_notes.py           # Needs registration
```

---

## Summary

**Good News:**
- 13 of 13 scenarios already work in Amplifier
- 9 of 11 scripts/hooks already work
- External dependencies are well-managed

**Work Needed:**
- 5 commands need conversion to recipes/skills
- 2 scripts need registration as tool modules
- Total: ~20-35 hours of migration work

**Risks:**
- Medium: MCP server dependencies (Notion, paper-search)
- Low: System tool availability (ffmpeg, yt-dlp)
- Low: API key configuration (already handled)

**Recommendation:** Start with Phase 1 (Quick Wins) to validate the migration pattern, then proceed through phases based on priority and available time.
