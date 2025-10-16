# Known Issues - Evidence System & Bplan

## Tool Concurrency Issues (2025-10-16)

### Symptoms
- Tool calls hanging or timing out
- Extremely slow response times
- Potential race conditions with hooks

### Suspected Causes

1. **PostToolUse Hook Overhead**
   - `hook_post_tool_use.py` runs on EVERY tool use
   - Performs async LLM calls for claim validation
   - Creates significant overhead even when disabled via `MEMORY_SYSTEM_ENABLED`
   - The hook processing itself may be causing delays

2. **Hook Chain Processing**
   - Multiple hooks (PreToolUse, PostToolUse, SubagentStop, etc.) create a processing chain
   - Each hook adds latency to tool execution
   - Potential for race conditions when tools are called in parallel

3. **Async Hook Execution**
   - Hooks run Python async code via subprocess
   - May be blocking the main Claude Code process
   - No clear visibility into hook execution timing

### Attempted Solutions

1. Removed `on_code_change_hook.sh` from PostToolUse matcher
2. Disabled memory system via `MEMORY_SYSTEM_ENABLED=false`
3. These changes had minimal impact on concurrency issues

### Recommendations for Investigation

1. **Profile Hook Execution**
   - Add timing instrumentation to each hook
   - Measure total hook chain latency per tool call
   - Identify bottlenecks in the hook processing pipeline

2. **Consider Hook Simplification**
   - Move expensive operations (LLM calls) to background tasks
   - Use file-based queuing instead of inline processing
   - Consider making hooks opt-in rather than running on every tool

3. **Test Without Hooks**
   - Temporarily disable all hooks via settings.json
   - Measure baseline tool execution performance
   - Determine actual overhead contributed by hooks

4. **Async Processing Strategy**
   - Investigate if hooks can run truly async (non-blocking)
   - Consider event-driven architecture for claim validation
   - Batch hook operations instead of per-tool execution

### Workaround

Create a fresh codespace without the accumulated hook state and log files. This often resolves the issue, suggesting:
- Log file accumulation may be slowing things down
- Hook state may be persisting incorrectly
- Fresh environment resets whatever concurrency issues have built up

### Related Files

- `.claude/settings.json` - Hook configuration
- `.claude/tools/hook_post_tool_use.py` - Claim validation hook
- `.claude/tools/subagent-logger.py` - Subagent logging hook
- `.claude/logs/` - Hook execution logs (may accumulate)

### Next Steps

1. Create fresh codespace to continue bplan work
2. Consider implementing evidence system without hooks
3. Re-evaluate hook architecture when concurrency issues are resolved
4. Document any patterns discovered in fresh environment
