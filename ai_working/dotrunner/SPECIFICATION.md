# DotRunner: Authoritative Specification

**Status**: AUTHORITATIVE - Code must implement this specification
**Version**: 1.0
**Created**: 2025-01-20

See ARCHITECTURE_DECISIONS.md for full rationale.

## Quick Reference

### Node Types
- **Agent Node**: Delegates to agent
- **Workflow Node**: Invokes sub-workflow (Phase 2)
- **Parallel Node**: Parallel execution (Phase 2)
- **Terminal Node**: End workflow

### Routing
- **Simple**: Dict with value→node mapping
- **Complex**: Python expressions with ast.literal_eval

### Agent Modes
ANALYZE, EVALUATE, EXECUTE, REVIEW, GENERATE

### State Directory
`.dotrunner/sessions/<session-id>/`

### Files
See `/workspaces/amplifier/ai_working/dotrunner/specs/` for complete specs:
- API_CONTRACT.md
- IMPLEMENTATION_SPEC.md
- BEHAVIOR_SPEC.md
- TEST_SPEC.md

**Location**: `/workspaces/amplifier/ai_working/dotrunner/SPECIFICATION.md`
