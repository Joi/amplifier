# Agent Communication Demo: LLaMPPL vs vLLM

**Goal**: Compare LLaMPPL and vLLM for structured agent-to-agent communication

## The Problem

When AI agents communicate, they need to exchange structured messages with:
- **Type safety**: Correct field types (strings, numbers, booleans)
- **Required fields**: No missing critical information
- **Valid enums**: Actions/statuses from predefined sets
- **Nested structures**: Complex objects with validation

Traditional LLM generation can produce invalid JSON or incorrect types. Both LLaMPPL and vLLM offer solutions, but with different trade-offs.

## Scenario: Multi-Agent Code Review System

Three agents collaborate on code review:
1. **Analyzer Agent**: Analyzes code and creates structured findings
2. **Reviewer Agent**: Evaluates findings and makes recommendations
3. **Coordinator Agent**: Aggregates reviews and makes final decision

Each message must be:
- Valid JSON
- Conform to strict schema
- Have correct types (no "high" when enum is ["LOW", "MEDIUM", "HIGH"])
- Include all required fields

## Approaches Compared

### 1. vLLM Structured Outputs (`vllm_example.py`)

**How it works**:
- Define Pydantic schema for agent messages
- vLLM uses JSON schema to constrain generation
- Fast inference with structured output guarantees
- Production-ready, high-performance

**Pros**:
- Very fast (optimized CUDA kernels, PagedAttention)
- Production-ready and battle-tested
- OpenAI-compatible API
- Easy integration with existing systems

**Cons**:
- Requires running vLLM server
- "Soft" constraints (guides generation, doesn't mathematically prove validity)
- Less flexible than LLaMPPL for complex constraints

### 2. LLaMPPL Constraint-Guided (`llamppl_example.py`)

**How it works**:
- Define constraints as logical predicates
- SMC steering: particle filter with constraint checking
- Mathematical guarantees of constraint satisfaction
- Research-grade, provable correctness

**Pros**:
- **Hard constraints**: Mathematical guarantees
- Can express complex logical constraints beyond JSON schema
- Provably correct outputs
- No hallucinations of invalid values

**Cons**:
- Slower (SMC overhead, particle filtering)
- Research tool (less mature than vLLM)
- More complex setup
- Higher computational cost

## Demo Structure

```
demos/agent_communication/
├── README.md                  # This file
├── schemas.py                 # Shared Pydantic schemas
├── vllm_example.py           # vLLM structured outputs demo
├── llamppl_example.py        # LLaMPPL constraint-guided demo
├── comparison.py             # Side-by-side comparison
└── requirements.txt          # Dependencies
```

## Running the Demos

### Prerequisites

```bash
# Install dependencies
pip install vllm pydantic llamppl

# For vLLM: Start server (in separate terminal)
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --guided-decoding-backend outlines
```

### Run vLLM Demo

```bash
python vllm_example.py
```

**Output**: Structured agent messages generated with vLLM's JSON schema constraints

### Run LLaMPPL Demo

```bash
python llamppl_example.py
```

**Output**: Structured agent messages generated with SMC steering constraints

### Run Comparison

```bash
python comparison.py
```

**Output**: Side-by-side comparison showing:
- Generation speed
- Constraint satisfaction rate
- Output quality
- Resource usage

## Expected Results

### vLLM
- **Speed**: ~100-500ms per message
- **Accuracy**: 95-99% schema compliance
- **Use case**: Production systems needing fast, reliable structured outputs

### LLaMPPL
- **Speed**: ~1-5s per message (SMC overhead)
- **Accuracy**: 100% constraint satisfaction (mathematical guarantee)
- **Use case**: Critical systems requiring provable correctness

## Key Insights

1. **Different guarantees**:
   - vLLM: "Very likely to be correct"
   - LLaMPPL: "Mathematically proven to be correct"

2. **Different trade-offs**:
   - vLLM: Fast + practical
   - LLaMPPL: Slow + provable

3. **Different use cases**:
   - vLLM: Production agent communication at scale
   - LLaMPPL: Critical constraint satisfaction (type systems, API contracts)

## Recommendations

**Use vLLM when**:
- Speed matters
- Production deployment
- Structured outputs sufficient (JSON schema)
- High throughput required

**Use LLaMPPL when**:
- Correctness is critical
- Complex logical constraints
- Research/experimentation
- Can tolerate higher latency

**Hybrid approach**:
- Use vLLM for most agent communication (fast)
- Use LLaMPPL for critical decisions (correct)
- Example: vLLM for code analysis messages, LLaMPPL for final type-safe code generation

## Next Steps

1. Benchmark both on real agent communication workloads
2. Measure constraint violation rates
3. Profile computational costs
4. Design hybrid architecture leveraging both

## References

- [vLLM Documentation](https://docs.vllm.ai/)
- [vLLM Structured Outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/)
- [LLaMPPL Paper](https://arxiv.org/abs/2306.03081)
- [LLaMPPL GitHub](https://github.com/probcomp/llamppl)
