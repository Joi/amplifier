# Neurosymbolic Coding Agents via Probabilistic Programming

**Joichi Ito**

LLM-based coding agents face three fundamental limitations that cannot be addressed through prompt engineering or architectural improvements: inability to maintain persistent structured memory, failure to distinguish correlation from causation, and soft constraint satisfaction. We propose augmenting LLMs with probabilistic programming to address these limitations through symbolic reasoning capabilities.

---

## Core Limitations

**Memory Degradation**: Context windows constrain persistent knowledge. Agents cannot maintain coherent beliefs about user preferences or codebase patterns across sessions.

**Correlation vs Causation**: LLMs identify statistical patterns but cannot perform causal inference. They recognize that tests and fewer bugs co-occur without understanding that tests *cause* bug reduction.

**Soft Constraints**: Generated code violates type systems, API contracts, and syntax despite explicit instructions. Constraints are weighted preferences, not mathematical guarantees.

These are not implementation issues—they are intrinsic to transformer architectures.

---

## Proposed Architecture

Augment LLMs with probabilistic programming for capabilities they fundamentally lack:

**LLM Layer**: Pattern recognition, natural language understanding, code synthesis from examples

**Probabilistic Computing Layer**: Structured memory (GenJax), causal inference (do-calculus), hard constraints (LLaMPPL)

This is neurosymbolic computing: neural networks for pattern matching, symbolic systems for structured reasoning.

---

## Three Core Components

### 1. Causal Memory (GenJax)

Represent the agent's world model as a structural causal model—not merely observational data but causal structure.

```python
@gen
def agent_world_model():
    # Beliefs with explicit uncertainty
    user_style = categorical(["functional", "oop", "mixed"]) @ "style"
    test_rigor = beta(2, 8) @ "test_rigor"

    # Causal dependencies
    if user_style == "functional":
        bug_rate = normal(0.05, 0.02) @ "bug_rate"
    else:
        bug_rate = normal(0.08, 0.03) @ "bug_rate"

    # Causal mechanism: tests reduce bugs
    has_tests = flip(test_rigor) @ "has_tests"
    if has_tests:
        bug_rate = bug_rate * 0.2

    return {"style": user_style, "bug_rate": bug_rate, "has_tests": has_tests}
```

**Capabilities**:
- Belief queries with uncertainty quantification
- Causal structure discovery (parent-child relationships)
- Interventional reasoning via do-calculus: `do(tests=True)` answers "What if we mandate tests?"

**Advantage**: Persistent structured beliefs, explicit uncertainty, counterfactual queries.

### 2. Constraint-Guided Generation (LLaMPPL)

Generate code satisfying formal specifications with mathematical guarantees, not probabilistic adherence.

```python
from llamppl import Model, Transformer, smc_steer

class TypeSafeCodeGen(Model):
    def step(self):
        token = self.sample(Transformer(self.context))

        # Hard constraints (violations impossible)
        self.condition(syntax_valid(self.code + token))
        self.condition(type_checks(self.code + token))
        self.condition(token not in HALLUCINATED_APIS)

        self.code += token
        if self.is_complete():
            self.finish()

# Sequential Monte Carlo steering
particles = smc_steer(model, N=10, K=3)
code = particles[0].code  # Provably satisfies constraints
```

**Method**: SMC steering treats generation as probabilistic program execution. Constraints are enforced during sampling, not filtered post-hoc.

**Advantage**: Zero type errors, zero hallucinations. Constraints are invariants, not suggestions.

### 3. Causal Decision Making

Interventional queries enable principled decision-making under uncertainty.

```python
# Counterfactual: "What if we add tests first?"
outcome_tests = memory.do_intervention("has_tests", True)
# Returns: {"bug_rate": 0.08}

# Alternative: "What if we fix bugs without tests?"
outcome_no_tests = memory.do_intervention("bug_count", 0)
# Returns: {"bug_rate": 0.35}  # Bugs recur

# Decision based on causal inference
action = min(outcomes, key=lambda x: x[1]["bug_rate"])
```

**Advantage**: Interventional reasoning, not pattern matching. Understanding mechanisms, not correlations.

---

## System Architecture

```
┌───────────────────────────────┐
│   LLM Agent (Amplifier)        │
│   • Code generation            │
│   • Natural language           │
│   • Task planning              │
└──────────┬────────────────────┘
           │
           ↓ Queries & Updates
┌───────────────────────────────┐
│   Probabilistic Layer          │
│                                │
│   CausalMemory (GenJax):       │
│     • SCM representation       │
│     • Bayesian updates         │
│     • Do-calculus              │
│                                │
│   ConstrainedGen (LLaMPPL):    │
│     • Type constraints         │
│     • API validation           │
│     • SMC steering             │
└───────────────────────────────┘
```

---

## Theoretical Foundation

**Causal Memory**: Structural causal models (Pearl, 2009) represented as GenJax generative functions. Interventions via graph surgery: remove incoming edges to intervened variable, set value deterministically, forward sample from modified model.

**Constrained Generation**: Sequential Monte Carlo steering of LLMs (Lew et al., 2023). Particle filter maintains diverse hypotheses, resamples based on constraint satisfaction, applies MCMC rejuvenation to prevent depletion.

**Complexity**: Memory queries O(1) for beliefs, O(N·T) for interventions (N samples, T variables). Constrained generation O(T·N·K) where T is code length, N particles, K MCMC steps. For N=10, K=3, T=100: ~3000 constraint checks vs potentially exponential rejection sampling.

---

## Implementation Plan (12 Weeks)

**Phase 1 (Weeks 1-2)**: Causal memory infrastructure
- GenJax world model (5-10 variables)
- Importance sampling for belief updates
- Do-operator implementation
- JSONL persistence

**Phase 2 (Weeks 3-4)**: LLaMPPL integration
- TypeSafeCodeGen model
- Incremental type checking (pyright API)
- SMC steering with adaptive proposals
- Particle depletion handling

**Phase 3 (Weeks 5-6)**: Amplifier integration
- CausalMemoryAgent wrapper
- Query APIs: `query()`, `causal_query()`, `do_intervention()`, `generate()`
- Belief update loop

**Phase 4 (Weeks 7-8)**: Empirical evaluation
- Benchmark 1: Type-safe API client (hallucination rate)
- Benchmark 2: Memory-guided refactoring (style consistency)
- Benchmark 3: Causal debugging (precision/recall on causal factors)
- Ablation: LLM vs +memory vs +constraints vs full system

**Phase 5 (Weeks 9-12)**: Optimization and analysis
- Computational optimization (caching, pruning)
- Causal graph learning experiments (PC algorithm)
- Documentation and release

---

## Success Criteria

**Minimum Viable**:
- Memory persistence >80% after 10 sessions
- Zero type errors in constrained generation
- Causal estimates directionally correct
- 10× speedup vs rejection sampling

**Strong**:
- Statistical significance vs baselines (GPT-4, Copilot)
- Ablation confirms necessity of both components
- <30 second generation latency
- Positive user evaluation

**Ambitious**:
- Automated causal graph learning from commit history
- Scalability to 100+ variables (Gen.jl migration)
- Multi-language support (TypeScript, Rust)
- Production deployment

---

## Technical Challenges

**Computational Cost**: Type checking at each token is prohibitive
- *Mitigation*: Incremental checking at expression boundaries only, memoization, particle pruning

**Particle Depletion**: Tight constraints eliminate all particles
- *Mitigation*: Adaptive proposals learned from successful particles, temporary constraint relaxation, intelligent restart

**Causal Graph Discovery**: Requires structure learning from observational data
- *Mitigation*: Bootstrap with domain knowledge, PC algorithm on historical data, active learning

**Scalability**: Current design handles 20-50 variables
- *Mitigation*: Exploit conditional independence, variational inference for >100 variables, Gen.jl for production scale

---

## Related Work

**LLaMPPL** (Lew et al., 2023): SMC steering of LLMs for constrained text generation. We extend to code generation with type/API constraints.

**Gen.jl** (Cusumano-Towner et al., 2019): Universal probabilistic programming with programmable inference. GenJax provides Python interface; Gen.jl offers superior performance for production.

**Causal Inference** (Pearl, 2009; Peters et al., 2017): Do-calculus for interventional reasoning from observational data.

**MemPrompt** (Madaan et al., 2022): Episodic memory via retrieval. We provide structured beliefs with causal semantics.

**Comparison**:
- Copilot: No memory, no causation, no hard constraints
- MemPrompt: Episodic text, no structure, no causation
- Reflexion: Reflection without causal understanding
- LLaMPPL: Constrained text generation, no memory
- **This work**: Causal memory + constrained code generation

---

## Why This Approach

**Addresses Fundamental Limitations**: These capabilities are not achievable through improved prompting or fine-tuning—they require symbolic reasoning.

**Leverages Existing Work**: Builds directly on LLaMPPL (proven for text) and extends to code with domain-specific constraints.

**Neurosymbolic Architecture**: Each component handles tasks suited to its computational model. Neural for pattern recognition, symbolic for structured reasoning.

**Practical Deployment**: Integration with existing agent system (Amplifier) enables real-world validation.

**Novel Contribution**: First system combining persistent causal memory with hard-constrained code generation.

---

## Open Questions

1. **Implementation**: GenJax (Python, easier integration) vs Gen.jl (performance)? Start with GenJax, migrate if necessary?

2. **Theoretical**: Does incremental type checking (only at expression boundaries) preserve SMC's theoretical guarantees?

3. **Feasibility**: Can causal graphs be learned from commit history with sufficient accuracy? Or require manual specification?

4. **Scalability**: Practical limits of GenJax inference? When does migration to Gen.jl become necessary?

5. **Alternative Approaches**: Better formulations we're overlooking?

---

## References

- Lew, A. K., et al. (2023). Sequential Monte Carlo Steering of Large Language Models. *arXiv:2306.03081*
- Cusumano-Towner, M. F., et al. (2019). Gen: A General-Purpose Probabilistic Programming System. *PLDI*
- Pearl, J. (2009). *Causality: Models, Reasoning, and Inference*
- Peters, J., et al. (2017). *Elements of Causal Inference*
- Madaan, A., et al. (2022). Memory-Assisted Prompt Editing. *arXiv:2201.06009*

---

## Summary

LLMs lack three capabilities essential for robust coding agents: persistent structured memory, causal reasoning, and hard constraint satisfaction. Probabilistic programming provides precisely these capabilities through symbolic reasoning. We propose a neurosymbolic architecture combining GenJax (causal memory with do-calculus) and LLaMPPL (type-safe code generation via SMC steering) integrated into Amplifier. 12-week implementation yields working prototype; empirical evaluation via benchmarks and ablation studies demonstrates value of both components.

Core insight: Use each computational paradigm for what it does well. Neural networks for pattern matching, symbolic systems for structured reasoning. This is not incremental improvement but addressing fundamental limitations through architectural composition.
