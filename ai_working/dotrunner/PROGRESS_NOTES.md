# DotRunner Implementation Progress Notes

**Last Updated**: 2025-10-18
**Status**: Design Complete ✅ - Ready for Implementation
**Current Phase**: About to begin Phase 1 (Core Data Models and YAML Parsing)

## Executive Summary

DotRunner is a **declarative agentic workflow orchestration system** that executes multi-agent workflows defined in YAML dotfiles. Design and planning phases are **100% complete** with comprehensive documentation, clear architecture, and detailed implementation tasks in beads.

**Key Achievement**: Complete design approved by zen-architect as "READY FOR IMPLEMENTATION" with no blocking issues.

## What's Been Completed

### 1. Design Phase (100% Complete)

**Comprehensive Documentation Created:**
- ✅ `README.md` - User-facing documentation (following blog_writer exemplar)
- ✅ `DESIGN.md` - Technical architecture and implementation details
- ✅ `examples/simple_linear.yaml` - Linear workflow example
- ✅ `examples/conditional_flow.yaml` - Conditional branching example
- ✅ `create_beads_tasks.py` - Script to generate beads issues

**Architecture Defined:**
- Core data models (Workflow, Node, WorkflowState, NodeResult)
- Module structure (parser, engine, executor, evaluator, state, cli)
- Integration points (ccsdk_toolkit, Task tool, file_io)
- Execution flow (node-by-node with state persistence)
- Error handling strategy (retry logic, clear messages)

**Implementation Strategy:**
- Test-first development (RED/GREEN cycle)
- Evidence-based validation (golden file comparison)
- Incremental state persistence
- Modular "bricks and studs" design

### 2. Task Breakdown (100% Complete)

**Beads Issues Created** (8 phases):
- **dr-1** (Epic): DotRunner: Declarative Agentic Workflow System
- **dr-2** (Phase 1): Core Data Models and YAML Parsing
- **dr-3** (Phase 2): Linear Execution Engine
- **dr-4** (Phase 3): State Persistence and Resume
- **dr-5** (Phase 4): CLI and User Interface
- **dr-6** (Phase 5): Agent Integration via Task Tool
- **dr-7** (Phase 6): Conditional Routing and Branching
- **dr-8** (Phase 7): Error Handling and Retry Logic
- **dr-9** (Phase 8): Validation, Documentation, and Evidence

Each phase includes:
- Clear TESTS FIRST (RED) requirements
- Specific IMPLEMENTATION (GREEN) tasks
- ACCEPTANCE CRITERIA for validation
- DEPENDENCIES explicitly stated
- GOLDEN FILE workflows for evidence

### 3. Agent Consultations Completed

**amplifier-cli-architect (CONTEXTUALIZE mode):**
- Confirmed perfect fit for amplifier CLI tool pattern
- Start in `ai_working/dotrunner/` for rapid iteration
- Use ccsdk_toolkit foundation (SessionManager, ClaudeSession)
- Follow blog_writer exemplar for documentation
- Progressive maturity model (ai_working → scenarios after proven)

**zen-architect (ANALYZE mode):**
- Designed comprehensive architecture
- Defined module structure and responsibilities
- Specified data models and interfaces
- Outlined execution flow and integration points
- Prioritized MVP features vs future enhancements

**zen-architect (REVIEW mode):**
- **Status**: ✅ READY FOR IMPLEMENTATION
- All components specified with clear interfaces
- Phase 1 can start immediately
- No blocking issues identified
- Philosophy alignment confirmed
- Task breakdown quality excellent

## Current State

### Files Created

```
ai_working/dotrunner/
├── README.md                    ✅ Complete
├── DESIGN.md                    ✅ Complete
├── PROGRESS_NOTES.md           ✅ This file
├── create_beads_tasks.py       ✅ Complete
├── examples/
│   ├── simple_linear.yaml      ✅ Complete
│   └── conditional_flow.yaml   ✅ Complete
└── (implementation files)       ⏳ To be created in Phase 1
```

### Beads Issues Status

All 8 DotRunner phases created in `.beads/issues.jsonl`:
- Epic (dr-1): Open
- Phases 2-9 (dr-2 through dr-9): Open, ready to work

### Branch

Current branch: `dotrunner` (created from `main`)
- Switched from `bplantest` for this work
- Clean slate for dotrunner implementation

## Next Steps (Immediate)

### Phase 1: Core Data Models and YAML Parsing

**Objective**: Foundation - workflow and node data models, YAML parsing with validation

**Step 1: Create Tests (RED)**

Create test files in `ai_working/dotrunner/tests/`:

1. **test_workflow_model.py**
   - Test Workflow dataclass creation
   - Test Node dataclass creation
   - Test field validation
   - Test defaults

2. **test_yaml_parsing.py**
   - Test loading valid YAML workflows
   - Test example workflows parse correctly
   - Test YAML syntax errors caught

3. **test_schema_validation.py**
   - Test required fields validated
   - Test type checking works
   - Test missing field errors clear

4. **test_context_merging.py**
   - Test global context available to nodes
   - Test node-level context overrides
   - Test environment variable expansion

5. **Antagonistic tests** (in each file):
   - Invalid YAML syntax
   - Missing required fields
   - Circular node dependencies
   - Malformed node references

**Step 2: Implementation (GREEN)**

Create implementation files:

1. **workflow.py**
   ```python
   @dataclass
   class Node:
       id: str
       name: str
       prompt: str
       agent: str = "auto"
       outputs: List[str] = field(default_factory=list)
       next: Optional[Union[str, List[Dict]]] = None
       retry_on_failure: int = 1
       type: Optional[str] = None

   @dataclass
   class Workflow:
       name: str
       description: str
       nodes: List[Node]
       context: Dict[str, Any] = field(default_factory=dict)

       @classmethod
       def from_yaml(cls, path: Path) -> 'Workflow':
           # Load and validate YAML
           pass

       def get_node(self, node_id: str) -> Optional[Node]:
           # Node lookup
           pass

       def validate(self) -> None:
           # Schema and relationship validation
           pass
   ```

2. **parser.py**
   ```python
   def parse_workflow(path: Path) -> Workflow:
       # YAML → Workflow
       pass

   def validate_schema(data: Dict) -> None:
       # Schema validation
       pass

   def validate_node_refs(workflow: Workflow) -> None:
       # Check node ID references
       pass

   def detect_cycles(workflow: Workflow) -> None:
       # Prevent infinite loops
       pass
   ```

**Step 3: Validation (EVIDENCE)**

- Run all tests and verify they pass
- Create golden files:
  - `tests/golden/simple_linear_parsed.json` - Expected parse output
  - `tests/golden/conditional_flow_parsed.json` - Expected parse output
- Store test evidence in `.beads/evidence/dotrunner/phase1/`
- Verify example workflows parse successfully

**Acceptance Criteria** (from dr-2):
- ✓ Workflow and Node models defined with all required fields
- ✓ YAML files parse correctly into data models
- ✓ Schema validation catches missing/invalid fields
- ✓ Node reference validation catches broken links
- ✓ Circular dependency detection works
- ✓ Clear error messages for validation failures
- ✓ Example workflows parse successfully
- ✓ All tests pass with real YAML files

## Key Decisions Made

### 1. Start in ai_working/dotrunner/
- Rapid iteration before graduating to scenarios/
- Proven pattern (blog_writer started as scenario)
- Graduate after 2-3 successful uses

### 2. Use ccsdk_toolkit Foundation
- SessionManager for workflow state persistence
- ClaudeSession for AI operations
- Defensive utilities (parse_llm_json, retry_with_feedback)
- File I/O with retry logic

### 3. MVP Simplicity
- Start with linear workflows only (Phase 1-4)
- Add conditionals in Phase 6
- Agent delegation via system prompts (Phase 5)
- Focus on working code over perfect design

### 4. Test-First with Golden Files
- Write tests before implementation (RED)
- Create expected outputs as golden files
- Byte-for-byte comparison for validation
- Evidence stored in `.beads/evidence/dotrunner/`

### 5. Modular "Bricks and Studs"
- Each module self-contained (parser, engine, executor, etc.)
- Clear public interfaces
- Regeneratable from specifications
- Test alongside implementation

## Important Context for Implementation

### Philosophy Alignment

**Ruthless Simplicity:**
- Start minimal, grow as needed
- No future-proofing
- Direct implementations (no abstractions for abstractions' sake)
- Code for structure, AI for intelligence

**Evidence-Based Coding:**
- Test-first development (from bplantest branch)
- Golden file validation
- Antagonistic tests for edge cases
- Evidence collection for all criteria

**Modular Design:**
- Self-contained modules with clear interfaces
- "Bricks and studs" - regeneratable components
- Specification-driven development

### Integration Points

**From ccsdk_toolkit:**
```python
from amplifier.ccsdk_toolkit import SessionManager, ClaudeSession, SessionOptions
from amplifier.ccsdk_toolkit.defensive import parse_llm_json, retry_with_feedback
from amplifier.utils.file_io import write_json, read_json
```

**State Directory Structure:**
```
.data/dotrunner/runs/
└── <workflow-name>/
    ├── state.json          # Execution state
    ├── results/
    │   └── <node-id>.json  # Node results
    └── workflow.yaml       # Copy of workflow
```

**Evidence Directory Structure:**
```
.beads/evidence/dotrunner/
├── phase1/
│   ├── test_results.txt
│   └── golden/
│       ├── simple_linear_parsed.json
│       └── conditional_flow_parsed.json
├── phase2/
└── ...
```

### Agent Delegation Strategy (Phase 5)

Two approaches documented:

**Approach 1: System Prompts (MVP)**
```python
async def _delegate_to_agent(agent: str, task: str):
    options = SessionOptions()
    options.system_prompt = get_agent_system_prompt(agent)

    async with ClaudeSession(options) as session:
        return await session.generate(task)
```

**Approach 2: Manual Delegation (Fallback)**
- Print delegation instructions to user
- User runs via Claude Code Task tool
- User pastes result back
- Document in README

### Error Handling Pattern

```python
# Use defensive utilities
from amplifier.ccsdk_toolkit.defensive import parse_llm_json, retry_with_feedback

# Parse LLM responses defensively
result = parse_llm_json(llm_response)

# Retry with feedback on failure
result = await retry_with_feedback(
    async_func=execute_node,
    prompt=node.prompt,
    max_retries=node.retry_on_failure
)
```

## Risks and Mitigations

### Risk 1: Agent Delegation Complexity (Phase 5)
**Mitigation**: Two approaches documented (system prompts vs manual). Won't block MVP (Phases 1-4).

### Risk 2: Condition Evaluation Complexity (Phase 6)
**Mitigation**: Start with simple string interpolation and comparison. AI evaluation for complex expressions. Well-isolated in evaluator module.

### Risk 3: State File Corruption
**Mitigation**: Atomic writes (temp file + rename). Retry logic for cloud-synced directories. Use `amplifier.utils.file_io`.

## Success Metrics

**Phase 1 Complete When:**
- All tests pass (RED → GREEN)
- Example workflows parse successfully
- Golden files validate correctly
- Evidence files created
- Beads issue dr-2 can be closed with evidence

**Overall MVP Complete When:**
- Phases 1-4 complete (linear workflows work end-to-end)
- Can run: `python -m ai_working.dotrunner run examples/simple_linear.yaml`
- State persists after each node
- Resume works after interruption
- All acceptance criteria met with evidence

## Resumption Checklist

When resuming this work after compaction:

1. **Read this file first** to understand current state
2. **Check beads issues** - See which phases are open/closed
3. **Review DESIGN.md** - Refresh on architecture
4. **Read README.md** - Understand user-facing functionality
5. **Start with Phase 1** if not yet complete:
   - Create test files first (RED)
   - Implement to make tests pass (GREEN)
   - Create golden files for evidence
   - Store evidence in `.beads/evidence/dotrunner/`
6. **Follow test-first approach** for all phases
7. **Use existing agents** for help:
   - `zen-architect` for design questions
   - `modular-builder` for implementation
   - `test-coverage` for test strategy
   - `bug-hunter` for debugging

## Files to Reference

**Documentation:**
- `README.md` - User guide with examples
- `DESIGN.md` - Technical architecture
- `examples/*.yaml` - Example workflows

**Beads:**
- `.beads/issues.jsonl` - Implementation tasks (dr-1 through dr-9)

**Evidence (to be created):**
- `.beads/evidence/dotrunner/phase*/` - Test evidence and golden files

**Implementation (to be created):**
- `ai_working/dotrunner/workflow.py` - Data models
- `ai_working/dotrunner/parser.py` - YAML parsing
- `ai_working/dotrunner/engine.py` - Execution engine
- `ai_working/dotrunner/executor.py` - Node executor
- `ai_working/dotrunner/state.py` - State manager
- `ai_working/dotrunner/evaluator.py` - Condition evaluator
- `ai_working/dotrunner/cli.py` - CLI interface
- `ai_working/dotrunner/tests/` - Test suite

## Branch Strategy

- **Current branch**: `dotrunner`
- **Parent branch**: `main`
- **Evidence system**: Available from `bplantest` branch patterns
- **Commit strategy**: Commit after each phase completion with evidence

## Contact Points

- **Original requirements**: User message requesting dotrunner system
- **Design validation**: zen-architect approved as "READY FOR IMPLEMENTATION"
- **Implementation guidance**: amplifier-cli-architect provided context
- **Test strategy**: Evidence-based coding from bplantest branch

---

**Next Action**: Begin Phase 1 implementation - Create test files for data models and YAML parsing.

**Remember**: Test-first! Write failing tests, then make them pass. Create golden files for evidence. Follow ruthless simplicity principle.
