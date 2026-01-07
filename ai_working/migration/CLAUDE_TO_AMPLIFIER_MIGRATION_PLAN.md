# Claude Code Tools to Amplifier CLI Migration Plan

**Version:** 1.0  
**Date:** 2026-01-07  
**Status:** Strategic Analysis (No Implementation)

---

## Executive Summary

This document analyzes the migration path from Claude Code's `.claude/` tool ecosystem (25 commands, 35 agents, 12 hooks, 14 scenarios) to Amplifier CLI's bundle/module system. The analysis reveals:

- **40% GREEN**: Already exists or trivial migration (15 agents, scenarios architecture)
- **30% YELLOW**: Needs adaptation with clear path (most commands → recipes/skills)
- **20% ORANGE**: Requires new module development (custom hooks, integrations)
- **10% RED**: Architectural decisions needed (personal domains, hybrid workflows)

**Key Findings:**
1. Core developer agents already exist in Amplifier (`foundation`, `developer-expertise` collections)
2. Design agents already exist in `design-intelligence` collection
3. Scenarios architecture is identical - scenarios can run in both ecosystems
4. Commands represent the largest migration effort - most map to recipes or skills
5. Hooks require custom module development for Amplifier

**Recommended Timeline:** 4-6 weeks for phased migration

---

## Part 1: Concept Mapping Analysis

### 1.1 Ecosystem Mapping

| Claude Code Concept | Amplifier Equivalent | Notes |
|---------------------|---------------------|-------|
| `.claude/commands/` | Recipes (tool-recipes) or Skills (tool-skills) | Commands → structured workflows or loadable knowledge |
| `.claude/agents/` | Collection agents (`agents/*.md`) | Direct equivalent, same format |
| `.claude/tools/*.py` | Hook modules | Custom Python hooks → Amplifier hook modules |
| `scenarios/` | `scenarios/` | Identical architecture, shared |
| `settings.json` | Profile + Config | Profile YAML + `~/.amplifier/config.yaml` |
| `AGENT_PROMPT_INCLUDE.md` | Profile context | `@mentions` in profiles |

### 1.2 Module Type Mapping

| Claude Code | Amplifier | Migration Path |
|-------------|-----------|----------------|
| Slash command (`/name`) | Recipe OR Skill | Depends on complexity |
| Python hook tool | Hook module | Requires module creation |
| Agent markdown | Agent markdown | Nearly identical format |
| Scenario directory | Scenario directory | No changes needed |

---

## Part 2: Migration Categories

### 2.1 GREEN - Already Exists (No Migration Needed)

These items exist in Amplifier and just need to be used:

#### Agents (15 total - in `foundation` and `developer-expertise` collections)

| Agent | Amplifier Location | Status |
|-------|-------------------|--------|
| zen-architect | `developer-expertise:agents/zen-architect` | Ready |
| modular-builder | `developer-expertise:agents/modular-builder` | Ready |
| bug-hunter | `developer-expertise:agents/bug-hunter` | Ready |
| post-task-cleanup | `developer-expertise:agents/post-task-cleanup` | Ready |
| test-coverage | `developer-expertise:agents/test-coverage` | Ready |
| security-guardian | `developer-expertise:agents/security-guardian` | Ready |
| integration-specialist | `developer-expertise:agents/integration-specialist` | Ready |
| researcher | `developer-expertise:agents/researcher` | Ready |
| explorer | `foundation:agents/explorer` | Ready |

#### Design Agents (7 total - in `design-intelligence` collection)

| Agent | Amplifier Location | Status |
|-------|-------------------|--------|
| art-director | `design-intelligence:agents/art-director` | Ready |
| component-designer | `design-intelligence:agents/component-designer` | Ready |
| design-system-architect | `design-intelligence:agents/design-system-architect` | Ready |
| layout-architect | `design-intelligence:agents/layout-architect` | Ready |
| responsive-strategist | `design-intelligence:agents/responsive-strategist` | Ready |
| animation-choreographer | `design-intelligence:agents/animation-choreographer` | Ready |
| voice-strategist | `design-intelligence:agents/voice-strategist` | Ready |

#### Scenarios (14 total - shared directory)

All scenarios in `/Users/joi/amplifier/scenarios/` work with both ecosystems:

| Scenario | Status | Notes |
|----------|--------|-------|
| article_illustrator | Shared | Works in both |
| blog_extract | Shared | Works in both |
| blog_integrate | Shared | Works in both |
| blog_poster | Shared | Works in both |
| blog_synthesize | Shared | Works in both |
| blog_writer | Shared | Works in both |
| chanoyu_retrieval | Shared | Works in both |
| gtd_review | Shared | Works in both |
| ideas_tracker | Shared | Works in both |
| knowledge_curator | Shared | Works in both |
| project_planner | Shared | Works in both |
| smart_decomposer | Shared | Works in both |
| tips_synthesizer | Shared | Works in both |
| transcribe | Shared | Works in both |
| web_to_md | Shared | Works in both |

### 2.2 YELLOW - Needs Adaptation (Clear Migration Path)

#### Commands to Recipes

These commands have multi-step workflows that map well to Amplifier recipes:

| Command | Lines | Migration Target | Complexity |
|---------|-------|-----------------|------------|
| designer.md | 737 | Recipe: Multi-agent design orchestration | Medium |
| superplanner.md | 335 | Recipe: Project planning workflow | Medium |
| bplan.md | 334 | Recipe: Interactive planning with beads | High |
| ddd/* (8 files) | ~300 | Recipe: Document-Driven Development | Medium |
| ultrathink-task.md | 177 | Recipe: Agent orchestration pattern | Low |
| modular-build.md | 90 | Recipe: Module building workflow | Low |
| transcripts.md | 70 | Recipe: Transcript processing | Low |

**Migration Strategy:** Use `amplifier-collection-recipes` pattern to create recipe definitions.

#### Commands to Skills

These commands are knowledge/context loaders that map to skills:

| Command | Lines | Migration Target | Complexity |
|---------|-------|-----------------|------------|
| prime.md | 10 | Skill: Context priming knowledge | Low |
| review-code-at-path.md | 20 | Skill: Code review guidelines | Low |
| review-changes.md | 20 | Skill: Change review guidelines | Low |
| name.md | 30 | Skill: Naming conventions | Low |

**Migration Strategy:** Use `tool-skills` module to load domain knowledge dynamically.

#### Commands - Simple Tool Wrappers

These commands are thin wrappers around bash/tools:

| Command | Lines | Migration Target | Complexity |
|---------|-------|-----------------|------------|
| commit.md | 60 | Profile context OR simple recipe | Low |
| loop.md | 20 | Built-in orchestrator behavior | Low |
| session.md | 15 | Profile/context management | Low |

### 2.3 ORANGE - Requires New Module Development

#### Custom Agents Needing Migration (20 total)

These agents exist in `.claude/agents/` but not in Amplifier:

| Agent | Size | Domain | Priority |
|-------|------|--------|----------|
| amplifier-cli-architect | 32KB | Amplifier development | High |
| super-planner-coordinator | 18KB | Project management | High |
| project-planner | 8KB | Project management | High |
| phase-executor | 10KB | Workflow execution | Medium |
| phase-reviewer | 11KB | Workflow review | Medium |
| knowledge-curator | 22KB | Knowledge management | Medium |
| knowledge-archaeologist | 21KB | Knowledge discovery | Medium |
| pattern-emergence | 20KB | Pattern recognition | Medium |
| insight-synthesizer | 20KB | Knowledge synthesis | Medium |
| visualization-architect | 24KB | Data visualization | Medium |
| database-architect | 18KB | Database design | Medium |
| api-contract-designer | 18KB | API design | Medium |
| contract-spec-author | 18KB | Contract specification | Medium |
| module-intent-architect | 17KB | Module design | Medium |
| graph-builder | 16KB | Graph construction | Low |
| concept-extractor | 18KB | Concept extraction | Low |
| analysis-engine | 20KB | Generic analysis | Low |
| ambiguity-guardian | 19KB | Ambiguity detection | Low |
| subagent-architect | 18KB | Sub-agent design | Low |
| performance-optimizer | 18KB | Performance tuning | Low |

**Migration Strategy:** Create new collection(s) to house these agents:
- `developer-expertise-extended` - For dev-focused agents
- `knowledge-management` - For knowledge/insight agents
- `planning` - For project management agents

#### Hook Tools Requiring Module Development

| Hook Tool | Purpose | Migration Target |
|-----------|---------|-----------------|
| hook_logger.py | Unified logging | `hooks-logging` (exists) or custom |
| hook_post_tool_use.py | Post-tool processing | New hook module |
| hook_precompact.py | Pre-compaction export | New hook module |
| hook_session_start.py | Session initialization | New hook module |
| hook_stop.py | Session cleanup | New hook module |
| imagen.py | Google Imagen integration | New tool module |
| memory_cli.py | Memory management | New tool module |
| on_code_change_hook.sh | Code change detection | New hook module |
| on_notification_hook.py | Notification handling | New hook module |
| subagent-logger.py | Sub-agent logging | Extend `hooks-logging` |

### 2.4 RED - Architectural Decisions Required

#### Personal/Domain-Specific Commands

These commands are highly personal and need architectural decisions:

| Command | Domain | Issue |
|---------|--------|-------|
| chanoyu-letter.md | Tea ceremony | Personal domain knowledge |
| chanoyu-add.md | Tea ceremony | Personal vault management |
| chanoyu-word.md | Tea ceremony | Word doc conversion |
| morning.md | GTD/Productivity | Personal workflow |
| apple-note.md | Apple ecosystem | Apple integration |
| ideas.md | Personal | Ideas management |

**ADR Required:** Should personal tools be:
- A) A personal bundle (`~/.amplifier/collections/personal/`)
- B) Project-local `.amplifier/` directory
- C) Hybrid approach with shared + personal

#### External Service Integrations

| Integration | Status | Issue |
|-------------|--------|-------|
| Google Imagen API | Custom | No Amplifier equivalent |
| Apple Reminders | Custom | No Amplifier equivalent |
| Apple Notes | Custom | No Amplifier equivalent |
| Obsidian Vault | Custom | File operations work, need workflow |
| Beads issue tracker | Custom | No Amplifier equivalent |

**ADR Required:** How to handle external service integrations:
- A) Create custom tool modules for each
- B) Use MCP servers (tool-mcp exists)
- C) Bash tool with scripts

---

## Part 3: Phased Migration Plan

### Phase 1: Quick Wins (Week 1)

**Goal:** Start using Amplifier for daily work immediately

| Task | Action | Effort |
|------|--------|--------|
| Install collections | `amplifier collection add` for design-intelligence, toolkit | 1 hour |
| Create dev profile | Profile using existing agents | 2 hours |
| Port simple commands | commit, review-changes, review-code-at-path | 4 hours |
| Test scenarios | Verify all scenarios work via `make` | 2 hours |

**Deliverables:**
- Working Amplifier profile for development
- 3-4 simple commands working as skills/recipes
- Confirmed scenario compatibility

### Phase 2: Recipe Migration (Weeks 2-3)

**Goal:** Migrate complex commands to recipes

| Task | Priority | Effort |
|------|----------|--------|
| Create recipe collection structure | High | 4 hours |
| Migrate designer.md → recipe | High | 8 hours |
| Migrate ultrathink-task.md → recipe | High | 4 hours |
| Migrate modular-build.md → recipe | Medium | 4 hours |
| Migrate ddd/* → recipe suite | Medium | 12 hours |
| Migrate superplanner.md → recipe | Medium | 8 hours |

**Deliverables:**
- `amplifier-collection-workflows` with migrated recipes
- Documentation for each recipe

### Phase 3: Agent Migration (Week 3-4)

**Goal:** Migrate custom agents to Amplifier collections

| Task | Priority | Effort |
|------|----------|--------|
| Create agent collection structure | High | 2 hours |
| Migrate planning agents (3) | High | 6 hours |
| Migrate knowledge agents (4) | Medium | 8 hours |
| Migrate specialized dev agents (5) | Medium | 10 hours |
| Migrate utility agents (8) | Low | 16 hours |

**Deliverables:**
- `amplifier-collection-planning` with project management agents
- `amplifier-collection-knowledge` with knowledge management agents
- Extended `developer-expertise` collection (or fork)

### Phase 4: Scenario Validation (Week 4)

**Goal:** Ensure all scenarios work seamlessly

| Task | Action | Effort |
|------|--------|--------|
| Test each scenario | Run with example inputs | 8 hours |
| Document any issues | Create issue list | 2 hours |
| Fix compatibility issues | Address blockers | 8 hours |
| Create scenario index | Documentation | 2 hours |

**Deliverables:**
- All 14+ scenarios validated
- Known issues documented
- Scenario catalog with usage examples

### Phase 5: Hook Migration (Weeks 5-6)

**Goal:** Port custom hooks to Amplifier modules

| Task | Priority | Effort |
|------|----------|--------|
| Analyze existing hooks | Understand dependencies | 4 hours |
| Create hook module template | Based on hooks-logging pattern | 4 hours |
| Port session hooks | start, stop, precompact | 12 hours |
| Port tool hooks | post_tool_use | 8 hours |
| Port logging/notification hooks | logger, notification | 8 hours |
| Test hook integration | End-to-end testing | 8 hours |

**Deliverables:**
- 4-6 custom hook modules
- Documentation for each hook
- Integration tests

---

## Part 4: Architecture Decision Records

### ADR-001: Personal Tools Bundle Strategy

**Status:** Proposed

**Context:**
Several Claude Code commands are highly personal (chanoyu, morning routine, ideas tracking). These don't belong in shared collections but need a home in Amplifier.

**Options:**

| Option | Pros | Cons |
|--------|------|------|
| A) User collection (`~/.amplifier/collections/personal/`) | Clean separation, follows collection pattern | Need to implement user collections |
| B) Project `.amplifier/` directory | Already supported, simple | Only works in specific projects |
| C) Recipe files in user config | Simple, no new concepts | Limited to recipes, no agents |
| D) Hybrid: user profile + project recipes | Flexible, works now | More complex mental model |

**Recommendation:** Option D (Hybrid)
- User profile (`~/.amplifier/profiles/personal.md`) for common context
- Project-specific recipes in `.amplifier/recipes/` for workflows
- Later: Implement proper user collections when needed

### ADR-002: External Service Integration Pattern

**Status:** Proposed

**Context:**
Several integrations (Apple Notes, Apple Reminders, Imagen) require custom code. Amplifier has tool-mcp for MCP servers but no native support for these services.

**Options:**

| Option | Pros | Cons |
|--------|------|------|
| A) Custom tool modules | Full integration | Significant dev effort |
| B) MCP servers | Standard protocol, reusable | Need to create MCP servers |
| C) Bash + scripts | Quick, works now | Fragile, no error handling |
| D) Hybrid: Scripts now, MCP later | Progressive enhancement | Technical debt |

**Recommendation:** Option D (Hybrid)
- Immediate: Use bash tool with existing scripts
- Short-term: Create simple MCP servers for critical integrations
- Long-term: Evaluate which deserve full tool modules

### ADR-003: Command to Recipe vs Skill Decision Framework

**Status:** Proposed

**Context:**
Commands need to be migrated to either recipes (workflows) or skills (knowledge). Need clear criteria.

**Decision Framework:**

| Criterion | Use Recipe | Use Skill |
|-----------|-----------|-----------|
| Has multi-step workflow | Yes | No |
| Orchestrates agents | Yes | No |
| Produces artifacts | Yes | Maybe |
| Primarily provides context | No | Yes |
| Needs state management | Yes | No |
| Interactive questionnaire | Yes | No |
| Pure knowledge/guidelines | No | Yes |

**Examples:**
- `designer.md` (orchestrates 7 agents) → Recipe
- `prime.md` (loads context) → Skill
- `bplan.md` (multi-phase workflow) → Recipe
- `name.md` (naming conventions) → Skill

---

## Part 5: Risk Assessment

### 5.1 Functionality at Risk

| Feature | Risk Level | Mitigation |
|---------|------------|------------|
| Apple integrations | High | Scripts work, but no deep integration |
| Imagen image generation | Medium | Can create tool module |
| Beads issue tracking | Medium | Can port as scenario or tool |
| Session state export | Medium | Need custom hook |
| Sub-agent logging | Low | Extend existing hooks-logging |

### 5.2 Significant Rework Required

| Item | Effort | Reason |
|------|--------|--------|
| bplan.md | High | Complex state machine, beads integration |
| superplanner.md | High | Agent orchestration, persistence |
| designer.md | Medium | Multi-agent routing, registry pattern |
| Hook ecosystem | High | Need to create multiple modules |

### 5.3 Claude Code-Specific Features

| Feature | Amplifier Equivalent | Gap |
|---------|---------------------|-----|
| `/command` syntax | None (use recipes) | Different UX |
| AskUserQuestion tool | Built-in prompting | Works differently |
| TodoWrite tool | todo tool | Equivalent |
| Task tool for agents | task tool | Equivalent |
| Statusline hook | hooks-status-context | Equivalent |

---

## Part 6: Next Steps

### Immediate Actions (This Week)

1. **Decision Required:** Approve ADR-001 (Personal Tools Strategy)
2. **Decision Required:** Approve ADR-002 (Integration Pattern)
3. **Setup:** Install required Amplifier collections
4. **Start:** Phase 1 quick wins

### Owner Assignments

| Phase | Owner | Timeline |
|-------|-------|----------|
| Phase 1: Quick Wins | TBD | Week 1 |
| Phase 2: Recipes | TBD | Weeks 2-3 |
| Phase 3: Agents | TBD | Weeks 3-4 |
| Phase 4: Scenarios | TBD | Week 4 |
| Phase 5: Hooks | TBD | Weeks 5-6 |

### Success Criteria

- [ ] All daily development workflows work in Amplifier
- [ ] 80% of commands have working equivalents
- [ ] All scenarios run successfully
- [ ] Personal tools strategy implemented
- [ ] External integrations functional (even if via scripts)

---

## Appendix A: Complete Command Inventory

| Command | Lines | Category | Migration Target | Priority |
|---------|-------|----------|-----------------|----------|
| apple-note.md | 60 | Personal | Script + Profile | Low |
| bplan.md | 334 | Workflow | Recipe | High |
| chanoyu-add.md | 30 | Personal | Script + Profile | Low |
| chanoyu-letter.md | 245 | Personal | Recipe | Low |
| chanoyu-word.md | 50 | Personal | Script | Low |
| commit.md | 60 | Dev | Profile context | Medium |
| create-plan.md | 30 | Workflow | Recipe | Medium |
| designer.md | 737 | Design | Recipe | High |
| execute-plan.md | 30 | Workflow | Recipe | Medium |
| ideas.md | 30 | Personal | Scenario | Low |
| imagen.md | 40 | Tool | Tool module | Medium |
| loop.md | 20 | Meta | Orchestrator config | Low |
| modular-build.md | 90 | Dev | Recipe | Medium |
| morning.md | 80 | Personal | Recipe | Low |
| name.md | 30 | Dev | Skill | Low |
| prime.md | 10 | Context | Skill | Low |
| review-changes.md | 20 | Dev | Skill | Medium |
| review-code-at-path.md | 20 | Dev | Skill | Medium |
| session.md | 15 | Meta | Profile | Low |
| standardize-slides.md | 50 | Tool | Recipe | Low |
| superplanner.md | 335 | Workflow | Recipe | High |
| test-webapp-ui.md | 60 | Testing | Recipe | Medium |
| transcripts.md | 70 | Tool | Recipe | Medium |
| ultrathink-task.md | 177 | Workflow | Recipe | High |
| ddd/0-help.md | 140 | DDD | Recipe suite | Medium |
| ddd/1-plan.md | 100 | DDD | Recipe suite | Medium |
| ddd/2-docs.md | 150 | DDD | Recipe suite | Medium |
| ddd/3-code-plan.md | 160 | DDD | Recipe suite | Medium |
| ddd/4-code.md | 170 | DDD | Recipe suite | Medium |
| ddd/5-finish.md | 160 | DDD | Recipe suite | Medium |
| ddd/prime.md | 80 | DDD | Recipe suite | Medium |
| ddd/status.md | 100 | DDD | Recipe suite | Medium |

## Appendix B: Complete Agent Inventory

### Already in Amplifier (15)

| Agent | Collection | Status |
|-------|------------|--------|
| zen-architect | developer-expertise | Ready |
| modular-builder | developer-expertise | Ready |
| bug-hunter | developer-expertise | Ready |
| post-task-cleanup | developer-expertise | Ready |
| test-coverage | developer-expertise | Ready |
| security-guardian | developer-expertise | Ready |
| integration-specialist | developer-expertise | Ready |
| researcher | developer-expertise | Ready |
| explorer | foundation | Ready |
| art-director | design-intelligence | Ready |
| component-designer | design-intelligence | Ready |
| design-system-architect | design-intelligence | Ready |
| layout-architect | design-intelligence | Ready |
| responsive-strategist | design-intelligence | Ready |
| animation-choreographer | design-intelligence | Ready |
| voice-strategist | design-intelligence | Ready |

### Needs Migration (20)

| Agent | Size | Proposed Collection |
|-------|------|-------------------|
| amplifier-cli-architect | 32KB | developer-expertise-extended |
| super-planner-coordinator | 18KB | planning |
| project-planner | 8KB | planning |
| phase-executor | 10KB | planning |
| phase-reviewer | 11KB | planning |
| knowledge-curator | 22KB | knowledge-management |
| knowledge-archaeologist | 21KB | knowledge-management |
| pattern-emergence | 20KB | knowledge-management |
| insight-synthesizer | 20KB | knowledge-management |
| visualization-architect | 24KB | developer-expertise-extended |
| database-architect | 18KB | developer-expertise-extended |
| api-contract-designer | 18KB | developer-expertise-extended |
| contract-spec-author | 18KB | developer-expertise-extended |
| module-intent-architect | 17KB | developer-expertise-extended |
| graph-builder | 16KB | knowledge-management |
| concept-extractor | 18KB | knowledge-management |
| analysis-engine | 20KB | developer-expertise-extended |
| ambiguity-guardian | 19KB | developer-expertise-extended |
| subagent-architect | 18KB | developer-expertise-extended |
| performance-optimizer | 18KB | developer-expertise-extended |

---

**Document End**

*Generated by zen-architect for strategic migration planning*
