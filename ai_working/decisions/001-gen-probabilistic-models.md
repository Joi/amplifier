# Decision Record: Gen.jl for Probabilistic Code Intelligence

**Date:** 2025-10-29
**Status:** Proposed (experimental)
**Deciders:** Joi, Claude Code

## Context

Amplifier needs better ways to:
1. **Remember structure** - Which patterns work when
2. **Retrieve context** - What files are relevant for tasks
3. **Generate tools** - Suggest structures based on intent
4. **Learn from experience** - Improve over time

Current approach relies on:
- Manual templates
- Keyword matching for context
- AI chat without memory of patterns
- No explicit uncertainty modeling

## Decision

Integrate **Gen.jl probabilistic programming** to model:
1. Context relevance (which files matter for this task?)
2. Tool structure (what architecture fits this intent?)
3. Pattern decisions (which approach works in this context?)

## Rationale

### Why Probabilistic Programming?

**Explicit Uncertainty:**
- Software design has multiple valid solutions
- Don't pretend to know "the right answer"
- Model uncertainty, show alternatives

**Learn from Small Data:**
- Your codebase is the training data
- Don't need millions of examples
- Patterns emerge from YOUR work

**Composable Models:**
- Matches "bricks and studs" philosophy
- Each model solves one problem
- Combine for complex intelligence

**Interpretable:**
- See why suggestions are made
- Trace reasoning
- Debug the model

### Why Gen.jl Specifically?

**Designed for this:**
- Models programs/structures, not just patterns
- Built-in inference algorithms
- Small data learning
- Compositional modeling

**Alternatives Considered:**
- **PyTorch/TensorFlow:** Overkill, need large datasets, less interpretable
- **Pure LLMs:** Hallucinate, overconfident, don't learn YOUR patterns
- **Rule-based:** Brittle, hard to maintain, no uncertainty

**Gen.jl hits the sweet spot:**
- Probabilistic but structured
- Learns but interpretable
- Uncertain but useful

## Architecture

```
gen_models/
├── models/              # Gen.jl probabilistic models
├── training_data/       # Your codebase as training data
├── inference/           # Python wrappers for CLI
└── docs/               # Vision and setup
```

**Integration:**
- Julia for models (Gen.jl)
- Python for CLI/tools (subprocess bridge)
- Training data from existing amplifier work

## Consequences

### Positive

**Learns Your Style:**
- Not generic templates
- YOUR patterns, YOUR philosophy
- Adapts as you evolve

**Explicit Uncertainty:**
- "70% confident" is useful information
- Multiple options when uncertain
- Make informed decisions

**Gets Better Over Time:**
- Every tool teaches the model
- DISCOVERIES.md becomes training data
- Continuous improvement

**Novel Combinations:**
- Probabilistically compose patterns
- Not just copy-paste
- Consistent but creative

### Negative

**New Dependency:**
- Requires Julia installation
- Learning curve for team
- Another language to maintain

**Complexity:**
- Python ↔ Julia bridge
- Model maintenance
- Training pipeline needed

**Uncertain Value:**
- Experimental approach
- May not help in practice
- Need to validate empirically

### Mitigation

**Start Small:**
- POC for context retrieval only
- Evaluate usefulness first
- Expand only if valuable

**Keep Simple:**
- Minimal models initially
- Add complexity only when needed
- Ruthless simplicity principle

**Make Optional:**
- Don't require for basic amplifier use
- Advanced feature for power users
- Graceful degradation without Julia

## Alternatives Considered

### 1. Pure Python Probabilistic (Pyro/NumPyro)

**Pros:**
- No Julia dependency
- Same language as amplifier

**Cons:**
- Less mature for program modeling
- More verbose for this use case
- Gen.jl specifically designed for this

**Decision:** Start with Gen.jl, consider Python port if successful

### 2. LLM-based Memory/Context

**Pros:**
- Already using Claude Code SDK
- Natural language understanding

**Cons:**
- No explicit uncertainty
- Doesn't learn from codebase
- Hallucination risk
- Expensive at scale

**Decision:** Complement, don't replace. Use Gen for structure, LLM for content.

### 3. Simple Rule-based System

**Pros:**
- Easy to implement
- No ML complexity
- Predictable

**Cons:**
- Brittle
- Doesn't adapt
- No uncertainty modeling
- Manual rule maintenance

**Decision:** Too limiting for long-term vision

## Implementation Plan

### Milestone 1: POC (Week 1)
- ✅ Create directory structure
- ✅ Basic context retrieval model
- ✅ Python CLI wrapper
- ⏳ Test with real tasks
- ⏳ Evaluate usefulness

### Milestone 2: Learning (Week 2-3)
- Extract training data from git history
- Learn from DISCOVERIES.md
- Improve relevance scoring
- Validate accuracy

### Milestone 3: Tool Generation (Week 4+)
- Model tool structure patterns
- Component reuse learning
- Full suggestion pipeline

## Success Criteria

**Must achieve:**
1. Context suggestions are helpful (>70% accuracy)
2. Confidence scores are calibrated (match actual usefulness)
3. Faster than manual searching (latency <2s)

**Nice to have:**
1. Learns from new tools automatically
2. Suggests novel but valid combinations
3. Adapts to philosophy changes

**Failure conditions:**
1. Suggestions are mostly wrong (<50% useful)
2. Too slow to be practical (>5s)
3. Too complex to maintain

## Review Triggers

**Re-evaluate if:**
- After 2 weeks of use, not providing value
- Maintenance burden exceeds benefits
- Simpler approach emerges
- Team finds it confusing rather than helpful

## References

- [Gen.jl Documentation](https://www.gen.dev/)
- [Probabilistic Programming](https://en.wikipedia.org/wiki/Probabilistic_programming)
- [Amplifier Vision](../../AMPLIFIER_VISION.md)
- [Modular Design Philosophy](../../ai_context/MODULAR_DESIGN_PHILOSOPHY.md)

## Notes

This is an **experiment**. The hypothesis is that probabilistic programming can help Amplifier learn and suggest structure. If it doesn't help in practice, we abandon it.

**Philosophy:** Try, measure, learn, adapt.
