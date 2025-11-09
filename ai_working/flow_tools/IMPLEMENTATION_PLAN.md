# Flow Tools Implementation Plan

**Version**: 1.0.0
**Status**: Draft
**Created**: 2025-01-20

## Overview

Implementation plan for two integrated tools:
1. **Flow Builder** - Interactive workflow creation CLI
2. **Flow Command** - Slash command for workflow execution

Following **bplan** and **this_is_the_way** principles for phased, test-driven development.

## Guiding Principles

### From "this_is_the_way"

- **Evidence First**: Write tests BEFORE implementation
- **Prove It Works**: Every feature must have evidence (tests) before merge
- **No Faith-Based Development**: Don't trust, verify with tests
- **Simplicity**: Ruthlessly eliminate complexity
- **Real Scenarios**: Tests use realistic examples

### From "bplan"

- **Phased Development**: Break into small, testable increments
- **Test-First**: Write tests before code for each phase
- **Incremental Value**: Each phase delivers working functionality
- **Clear Acceptance Criteria**: Each phase has measurable success
- **No Big Bang**: Avoid large, untested changes

## Project Structure

```
amplifier/
├── flow_builder/           # Flow Builder tool
│   ├── __init__.py
│   ├── cli.py             # Click CLI entry point
│   ├── agent.py           # Flow builder agent wrapper
│   ├── discovery.py       # Agent/flow discovery
│   ├── interrogation.py   # Interactive Q&A
│   ├── validation.py      # Workflow validation
│   ├── test_mode.py       # Interactive testing
│   ├── generator.py       # YAML generation
│   └── test_file.py       # Test file generation
│
├── flow_executor/          # Flow Command backend (if agent-based)
│   ├── __init__.py
│   ├── agent.py           # Flow executor agent
│   ├── discovery.py       # Flow discovery/fuzzy matching
│   ├── context.py         # Context collection
│   ├── parser.py          # Natural language parser
│   └── executor.py        # DotRunner wrapper
│
├── ai_flows/               # Workflow storage
│   ├── tests/             # Test files for workflows
│   └── examples/          # Example workflows
│
└── .claude/
    └── commands/
        └── flow.md        # Slash command definition

tests/
├── test_flow_builder/
│   ├── test_discovery.py
│   ├── test_interrogation.py
│   ├── test_validation.py
│   ├── test_test_mode.py
│   ├── test_generator.py
│   └── test_integration.py
│
└── test_flow_executor/
    ├── test_discovery.py
    ├── test_context.py
    ├── test_parser.py
    ├── test_executor.py
    └── test_integration.py
```

## Phase 1: Foundation (Flow Builder Core)

**Goal**: Basic flow builder that creates valid DotRunner workflows through simple interrogation

### Acceptance Criteria

- ✅ Can discover agents from `.claude/agents/`
- ✅ Can create minimal workflow (name, description, single node)
- ✅ Generates valid YAML that DotRunner can load
- ✅ Validates workflow structure
- ✅ 90%+ test coverage for core modules

### Tasks

#### 1.1: Project Setup
- [ ] Create `amplifier/flow_builder/` directory structure
- [ ] Create `ai_flows/` directory
- [ ] Set up pyproject.toml dependencies (click, rich, pyyaml, toml)
- [ ] Create test directory structure
- [ ] Write README with development setup

**Tests**: None (setup task)

#### 1.2: Agent Discovery Module
- [ ] **WRITE TESTS FIRST**:
  - `test_scan_agent_directory()` - Finds all .toml files
  - `test_parse_agent_toml()` - Extracts description, instructions
  - `test_empty_agents_directory()` - Handles no agents gracefully
  - `test_malformed_toml()` - Handles parse errors
- [ ] **THEN IMPLEMENT**:
  - `discovery.py`: `scan_agents()` function
  - Load TOML files from `.claude/agents/`
  - Extract agent metadata
  - Handle errors gracefully

**Evidence**: All tests pass, agent catalog builds successfully

#### 1.3: Workflow Validation Module
- [ ] **WRITE TESTS FIRST**:
  - `test_validate_empty_workflow()` - Catches no nodes
  - `test_validate_duplicate_ids()` - Catches duplicate node IDs
  - `test_validate_invalid_next()` - Catches broken references
  - `test_validate_circular_deps()` - Detects cycles
  - `test_validate_valid_workflow()` - Passes valid workflows
- [ ] **THEN IMPLEMENT**:
  - `validation.py`: `validate_workflow()` function
  - Use DotRunner's Workflow.validate()
  - Add custom checks (complexity, cycles)
  - Return structured errors

**Evidence**: All validation tests pass, detects known issues

#### 1.4: YAML Generator Module
- [ ] **WRITE TESTS FIRST**:
  - `test_generate_minimal_workflow()` - Single node workflow
  - `test_generate_linear_workflow()` - A → B → C
  - `test_generate_conditional_workflow()` - With routing
  - `test_generated_yaml_loads()` - DotRunner can load it
- [ ] **THEN IMPLEMENT**:
  - `generator.py`: `generate_yaml()` function
  - Takes workflow structure, outputs YAML
  - Proper formatting and indentation
  - DotRunner-compatible format

**Evidence**: Generated YAML loads in DotRunner without errors

#### 1.5: Basic Interrogation (Linear Flows Only)
- [ ] **WRITE TESTS FIRST**:
  - `test_collect_workflow_name()` - Gets valid name
  - `test_collect_description()` - Gets description
  - `test_collect_single_node()` - Creates one node
  - `test_invalid_agent_name()` - Handles unknown agents
- [ ] **THEN IMPLEMENT**:
  - `interrogation.py`: `InterrogationSession` class
  - Ask for: name, description, goal
  - Create single node workflow
  - Recommend agent based on goal

**Evidence**: Can create single-node workflow via interaction

#### 1.6: CLI Entry Point
- [ ] **WRITE TESTS FIRST**:
  - `test_cli_help()` - Shows help message
  - `test_cli_no_args()` - Enters interrogation mode
  - `test_cli_with_description()` - Quick mode
- [ ] **THEN IMPLEMENT**:
  - `cli.py`: Click CLI
  - `amplifier flow-builder` command
  - Wire to interrogation module
  - Save output to `ai_flows/`

**Evidence**: CLI runs, creates workflow file

#### 1.7: Phase 1 Integration Test
- [ ] **WRITE TEST**:
  - `test_end_to_end_simple_flow()` - Full workflow creation
  - Mock user input for interrogation
  - Verify file created in ai_flows/
  - Verify DotRunner can load and validate
- [ ] **RUN TEST**: Should pass with Phase 1 implementation

**Evidence**: End-to-end test passes, workflow executes in DotRunner

---

## Phase 2: Advanced Interrogation (Multi-Node & Routing)

**Goal**: Create complex workflows with multiple nodes and conditional routing

### Acceptance Criteria

- ✅ Can create workflows with multiple nodes
- ✅ Handles linear and conditional routing
- ✅ Recommends agents for each step
- ✅ Allows agent override
- ✅ 90%+ test coverage

### Tasks

#### 2.1: Multi-Node Interrogation
- [ ] **WRITE TESTS FIRST**:
  - `test_collect_multiple_steps()` - Creates 3+ node workflow
  - `test_step_outputs_become_inputs()` - Variable flow
  - `test_recommend_agent_per_step()` - Different agents
- [ ] **THEN IMPLEMENT**:
  - Extend `interrogation.py`
  - Loop through steps
  - Track outputs for next step inputs
  - Agent recommendation per step

**Evidence**: Creates multi-node workflows with proper variable flow

#### 2.2: Routing Configuration
- [ ] **WRITE TESTS FIRST**:
  - `test_linear_routing()` - A → B → C
  - `test_conditional_routing()` - Based on outputs
  - `test_default_fallback()` - Handles default case
  - `test_routing_validation()` - Invalid routes caught
- [ ] **THEN IMPLEMENT**:
  - Routing question in interrogation
  - Parse routing logic
  - Generate conditional `next` blocks
  - Validate routing references

**Evidence**: Creates workflows with conditional routing

#### 2.3: Agent Recommendation with Override
- [ ] **WRITE TESTS FIRST**:
  - `test_accept_recommended_agent()` - Uses suggestion
  - `test_override_with_custom_agent()` - Uses user choice
  - `test_show_all_agents_on_reject()` - Lists alternatives
  - `test_invalid_agent_name()` - Handles typos
- [ ] **THEN IMPLEMENT**:
  - Agent recommendation using AI analysis
  - Parse user response (Y/n/agent-name)
  - Show all agents if rejected
  - Validate agent exists

**Evidence**: Agent recommendation and override work smoothly

---

## Phase 3: AI-Powered Discovery & Composition

**Goal**: Use AI to analyze agents deeply and suggest existing flows

### Acceptance Criteria

- ✅ AI analyzes agent capabilities from TOML
- ✅ Detects redundant workflow creation
- ✅ Suggests existing flows for composition
- ✅ 85%+ test coverage

### Tasks

#### 3.1: Flow Discovery Module
- [ ] **WRITE TESTS FIRST**:
  - `test_scan_flows_directory()` - Finds all workflows
  - `test_parse_flow_metadata()` - Extracts name, description, I/O
  - `test_empty_flows_directory()` - Handles no flows
- [ ] **THEN IMPLEMENT**:
  - `discovery.py`: `scan_flows()` function
  - Parse YAML files in `ai_flows/`
  - Extract metadata without full validation
  - Build flow catalog

**Evidence**: Flow catalog builds correctly

#### 3.2: AI Agent Analysis
- [ ] **WRITE TESTS FIRST**:
  - `test_analyze_agent_capabilities()` - Uses LLM
  - `test_cache_agent_analysis()` - Doesn't re-analyze
  - `test_handle_llm_failure()` - Falls back gracefully
- [ ] **THEN IMPLEMENT**:
  - Extend `discovery.py`
  - Use Claude to analyze agent descriptions
  - Extract capabilities, use cases
  - Cache results for session

**Evidence**: Agent capabilities extracted via AI

#### 3.3: Redundancy Detection
- [ ] **WRITE TESTS FIRST**:
  - `test_detect_similar_workflow()` - Finds matches
  - `test_suggest_existing_flow()` - Offers alternative
  - `test_user_ignores_suggestion()` - Continues creation
  - `test_user_accepts_suggestion()` - Uses existing flow
- [ ] **THEN IMPLEMENT**:
  - Compare user's goal to existing flow descriptions
  - Use AI to detect similarity
  - Suggest existing flows
  - Allow user to ignore

**Evidence**: Detects redundant workflows and suggests alternatives

---

## Phase 4: Interactive Test Mode

**Goal**: Let users test workflows interactively by simulating agent responses

### Acceptance Criteria

- ✅ Can step through workflow nodes
- ✅ User provides mock outputs
- ✅ Shows routing decisions
- ✅ Can generate test files from session
- ✅ 85%+ test coverage

### Tasks

#### 4.1: Test Mode Core
- [ ] **WRITE TESTS FIRST**:
  - `test_step_through_nodes()` - Iterates nodes
  - `test_collect_mock_outputs()` - Gets user input
  - `test_parse_natural_language_outputs()` - Parses outputs
  - `test_skip_node()` - Handles skips
- [ ] **THEN IMPLEMENT**:
  - `test_mode.py`: `TestSession` class
  - Iterate through workflow nodes
  - Show current node context
  - Collect outputs from user
  - Parse natural language outputs

**Evidence**: Can step through workflow interactively

#### 4.2: Routing Simulation
- [ ] **WRITE TESTS FIRST**:
  - `test_evaluate_routing_simple()` - Linear routing
  - `test_evaluate_routing_conditional()` - Dict-based
  - `test_show_routing_decision()` - Displays choice
  - `test_routing_to_nonexistent_node()` - Catches errors
- [ ] **THEN IMPLEMENT**:
  - Evaluate routing based on mock outputs
  - Show routing decision to user
  - Navigate to next node
  - Detect routing errors

**Evidence**: Routing logic validated through simulation

#### 4.3: Test File Generation
- [ ] **WRITE TESTS FIRST**:
  - `test_capture_test_session()` - Records all outputs
  - `test_generate_test_yaml()` - Creates test file
  - `test_test_file_format()` - Valid YAML structure
- [ ] **THEN IMPLEMENT**:
  - `test_file.py`: `generate_test_file()` function
  - Capture all mock outputs during session
  - Generate structured test YAML
  - Save to `ai_flows/tests/`

**Evidence**: Test files generated from interactive sessions

---

## Phase 5: Flow Executor (/flow command)

**Goal**: Slash command for discovering and executing workflows

### Acceptance Criteria

- ✅ `/flow` lists available workflows
- ✅ `/flow name` executes workflow
- ✅ Fuzzy matching works with confirmation
- ✅ Interactive context collection works
- ✅ Shows progress during execution
- ✅ 85%+ test coverage

### Tasks

#### 5.1: Flow Discovery for Executor
- [ ] **WRITE TESTS FIRST**:
  - `test_list_flows()` - Lists all in ai_flows/
  - `test_exact_match()` - Finds exact name
  - `test_fuzzy_match_single()` - One partial match
  - `test_fuzzy_match_multiple()` - Multiple matches
  - `test_no_match()` - Handles no results
- [ ] **THEN IMPLEMENT**:
  - `flow_executor/discovery.py`
  - Scan ai_flows/ directory
  - Exact and fuzzy matching
  - Return match results

**Evidence**: Discovery and matching work correctly

#### 5.2: Context Collection & Parsing
- [ ] **WRITE TESTS FIRST**:
  - `test_parse_natural_language_context()` - Extracts values
  - `test_structured_prompts_fallback()` - Explicit prompts
  - `test_validate_context()` - All required fields
  - `test_confirm_context()` - User confirmation
- [ ] **THEN IMPLEMENT**:
  - `flow_executor/context.py`
  - `flow_executor/parser.py`
  - Natural language parsing with LLM
  - Fallback to structured prompts
  - Validation and confirmation

**Evidence**: Context collection works naturally

#### 5.3: DotRunner Execution Wrapper
- [ ] **WRITE TESTS FIRST**:
  - `test_execute_workflow()` - Runs dotrunner
  - `test_stream_progress()` - Shows updates
  - `test_handle_failure()` - Error messages
  - `test_session_tracking()` - Creates session
- [ ] **THEN IMPLEMENT**:
  - `flow_executor/executor.py`
  - Wrap `dotrunner run` command
  - Stream progress to chat
  - Display results
  - Handle errors

**Evidence**: Workflows execute via /flow command

#### 5.4: Slash Command Definition
- [ ] **WRITE TEST**:
  - Manual test: `/flow` in Claude Code
- [ ] **THEN IMPLEMENT**:
  - Create `.claude/commands/flow.md`
  - Define command behavior
  - Wire to executor agent/tool
  - Test in Claude Code

**Evidence**: `/flow` command works in Claude Code

#### 5.5: Phase 5 Integration Test
- [ ] **WRITE TEST**:
  - `test_end_to_end_flow_execution()`
  - Create workflow with flow-builder
  - Execute with /flow command
  - Verify results
- [ ] **RUN TEST**: Should pass with Phase 5 implementation

**Evidence**: Complete workflow creation → execution cycle works

---

## Phase 6: Polish & Documentation

**Goal**: Production-ready tools with great UX and documentation

### Acceptance Criteria

- ✅ Error messages are helpful
- ✅ All edge cases handled
- ✅ Documentation complete
- ✅ Example workflows provided
- ✅ 90%+ overall test coverage

### Tasks

#### 6.1: Error Handling & Edge Cases
- [ ] **WRITE TESTS FIRST**:
  - Test all error paths
  - Test edge cases (empty inputs, special chars, etc.)
  - Test graceful degradation
- [ ] **THEN IMPLEMENT**:
  - Improve error messages
  - Add recovery paths
  - Handle edge cases

**Evidence**: Robust error handling, all tests pass

#### 6.2: Example Workflows
- [ ] Create 5 example workflows:
  - `evidence-based-development.yaml`
  - `code-review.yaml`
  - `architecture-review.yaml`
  - `bug-fix-workflow.yaml`
  - `documentation-generator.yaml`
- [ ] Test each workflow executes successfully
- [ ] Add tests to verify examples

**Evidence**: All examples work correctly

#### 6.3: User Documentation
- [ ] Create `ai_flows/README.md` - How to use /flow
- [ ] Create `amplifier/flow_builder/README.md` - How to create flows
- [ ] Add examples and screenshots
- [ ] Document troubleshooting

**Evidence**: Documentation complete and accurate

#### 6.4: Developer Documentation
- [ ] Create `ARCHITECTURE.md` - System design
- [ ] Create `TESTING.md` - How to run tests
- [ ] Create `CONTRIBUTING.md` - How to extend
- [ ] Document all modules and functions

**Evidence**: Developers can understand and extend tools

---

## Testing Strategy

### Test Pyramid

- **70% Unit Tests**: Test individual functions and modules
- **20% Integration Tests**: Test module interactions
- **10% E2E Tests**: Test complete workflows

### Test-First Discipline

**Every feature follows this order:**

1. **Write test** - What should this do?
2. **Run test** - It should fail (red)
3. **Implement** - Make it work
4. **Run test** - It should pass (green)
5. **Refactor** - Clean up code
6. **Run test** - Still passes (green)

### Key Test Areas

**Flow Builder**:
- Agent discovery and analysis
- Workflow interrogation
- Validation logic
- YAML generation
- Test mode simulation
- Test file generation

**Flow Executor**:
- Flow discovery and matching
- Context parsing
- Natural language understanding
- DotRunner integration
- Progress display

### Coverage Requirements

- **Minimum**: 85% overall
- **Target**: 90%+ overall
- **Critical modules**: 95%+ (validation, generator, executor)

### Test Tools

- **pytest**: Test runner
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking
- **pytest-asyncio**: Async testing
- **hypothesis**: Property-based testing (for complex parsers)

---

## Risk Mitigation

### Risk: AI Analysis Too Slow

**Mitigation**:
- Cache agent analysis results
- Use async LLM calls where possible
- Provide progress feedback to user
- Fall back to simple parsing if LLM unavailable

### Risk: Natural Language Parsing Unreliable

**Mitigation**:
- Always confirm parsed context with user
- Fall back to structured prompts
- Allow edit/retry
- Test with diverse input examples

### Risk: DotRunner Changes Break Integration

**Mitigation**:
- Use DotRunner's public API only
- Test against actual DotRunner (not mocks)
- Version-pin DotRunner dependency
- Monitor DotRunner changes

### Risk: Complexity Creep

**Mitigation**:
- Strictly follow ruthless simplicity principle
- Regular code reviews
- Keep modules small and focused
- Defer Phase 2 features aggressively

---

## Success Metrics

### Phase 1 Success
- Can create single-node workflow
- 90%+ test coverage
- All tests pass

### Phase 3 Success
- Can create multi-node workflows with routing
- AI recommendations work
- Flow composition works
- 90%+ test coverage

### Phase 5 Success
- `/flow` command works end-to-end
- Natural language context collection works
- Progress display is clear
- 85%+ test coverage

### Overall Success
- Users can create workflows without YAML knowledge
- Users can execute workflows with simple commands
- 90%+ overall test coverage
- All integration tests pass
- Documentation complete

---

## Timeline Estimate

**Phase 1**: 3-4 days
**Phase 2**: 2-3 days
**Phase 3**: 2-3 days
**Phase 4**: 2-3 days
**Phase 5**: 3-4 days
**Phase 6**: 1-2 days

**Total**: 13-19 days (estimated)

**Note**: These are development days, not calendar days. Actual timeline depends on complexity discovered during implementation.

---

## Next Steps

1. Review specs with user
2. Get approval on implementation plan
3. Set up project structure (Phase 1.1)
4. Begin Phase 1 development with test-first approach
5. Iterate through phases with continuous validation

**Remember**: Write tests FIRST, prove it works, then move forward. No faith-based development!
