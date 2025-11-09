# Agent Steering: Provably Safe AI Coding Agents

**Thesis**: Probabilistic programming can ENFORCE correctness in AI agents, not just suggest it.

---

## The Problem

Current AI coding agents (including Amplifier) are "smart but unreliable":

```python
# Agent generates code
agent.generate("Create payment handler")

# Result: Maybe it's good, maybe it has bugs 🤷
# - Might hallucinate non-existent APIs
# - Might forget error handling
# - Might create SQL injection vulnerabilities
# - Might violate type safety
```

**You can PROMPT the agent, but you can't GUARANTEE it listens.**

---

## The Insight: Steering vs Guidance

### ❌ Statistical Guidance (Traditional Approach)

```
Git History → GenJax Model → "87% chance of bugs"
                              ↓
Agent sees warning → Maybe adjusts behavior
```

**Problem**: Agent can ignore the guidance!

### ✅ Constraint Steering (Probabilistic Programming)

```
Agent Generation → SMC Steering → Constraints ENFORCED
                                   ↓
                   Guaranteed correct output
```

**Advantage**: Constraints are mathematically enforced, not suggested.

---

## How LLaMPPL Steering Works

### Traditional LLM Generation

```python
# Sample tokens until done
while not done:
    token = sample_from_llm(context)
    output += token
    if is_complete(output):
        done = True

return output  # Hope it's correct 🤞
```

### LLaMPPL SMC Steering

```python
# Maintain multiple hypotheses (particles)
particles = [Particle() for _ in range(N)]

while not all_done:
    for particle in particles:
        # Sample next token
        token = sample_from_llm(particle.context)
        candidate = particle.output + token

        # CHECK CONSTRAINTS
        for constraint in constraints:
            if not constraint(candidate):
                particle.weight = 0  # Kill this particle
                break

        particle.output = candidate

    # Resample: Keep valid particles, kill invalid ones
    particles = resample_by_weight(particles)

    # MCMC rejuvenation: Prevent particle depletion
    particles = mcmc_rejuvenate(particles)

return best_particle.output  # PROVABLY satisfies constraints ✓
```

**Key difference**: Invalid outputs are REJECTED during generation, not filtered after.

---

## Real-World Example

### Scenario: Create Secure Login Endpoint

**Without Steering** (Current Amplifier):

```python
result = agent.generate("""
Create a login endpoint that:
- Accepts username and password
- Queries the database
- Returns user info if valid
""")

# Generated code (UNSAFE):
def login(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = db.execute(query)
    return result.fetchone()

# ❌ SQL injection vulnerability
# ❌ No rate limiting
# ❌ Plaintext password comparison
# ❌ No input validation
```

**With Steering** (LLaMPPL-Enhanced):

```python
result = steered_agent.generate(
    prompt="""
    Create a login endpoint that:
    - Accepts username and password
    - Queries the database
    - Returns user info if valid
    """,
    constraints=[
        no_sql_injection,        # ENFORCED
        has_rate_limiting,       # ENFORCED
        validates_input,         # ENFORCED
        uses_password_hashing,   # ENFORCED
    ]
)

# Generated code (SAFE):
@rate_limit(max_calls=5, period=60)
def login(username: str, password: str) -> Optional[User]:
    # Input validation
    if not validate_username(username):
        raise ValueError("Invalid username")

    # Parameterized query (no SQL injection possible)
    query = "SELECT * FROM users WHERE username = ?"
    result = db.execute(query, (username,))
    user = result.fetchone()

    if user and verify_password(password, user.password_hash):
        return user
    return None

# ✓ NO SQL injection (constraint enforced)
# ✓ Rate limiting (constraint enforced)
# ✓ Input validation (constraint enforced)
# ✓ Password hashing (constraint enforced)
```

**The difference**: Constraints were ENFORCED during generation, not suggested.

---

## Constraint Examples

### 1. Syntax Validity

```python
def syntax_valid(code: str) -> bool:
    """Code must parse as valid Python."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False
```

**Effect**: IMPOSSIBLE to generate code that doesn't parse.

### 2. Type Safety

```python
def type_checks(code: str) -> bool:
    """Code must pass type checking."""
    result = subprocess.run(
        ["pyright", "--stdout"],
        input=code,
        capture_output=True
    )
    return result.returncode == 0
```

**Effect**: IMPOSSIBLE to generate code with type errors.

### 3. No Hallucinated APIs

```python
def no_hallucinations(code: str) -> bool:
    """All imported functions must exist."""
    imports = extract_imports(code)
    for module, names in imports.items():
        try:
            mod = importlib.import_module(module)
            for name in names:
                if not hasattr(mod, name):
                    return False  # Hallucinated function
        except ImportError:
            return False  # Hallucinated module
    return True
```

**Effect**: IMPOSSIBLE to generate code calling non-existent APIs.

### 4. Security Constraints

```python
def no_sql_injection(code: str) -> bool:
    """No string interpolation in SQL queries."""
    # Detect f-strings or .format() with SQL keywords
    pattern = r'(f".*SELECT.*{|".*SELECT.*".format\()'
    return not re.search(pattern, code, re.IGNORECASE)
```

**Effect**: IMPOSSIBLE to generate SQL injection vulnerabilities.

### 5. Architectural Constraints

```python
def follows_project_patterns(code: str) -> bool:
    """Must follow project architecture."""
    # Example: All API handlers must use @rate_limit decorator
    if "def " in code and "request" in code:
        return "@rate_limit" in code
    return True
```

**Effect**: IMPOSSIBLE to violate project patterns.

---

## The Value Proposition

### For Developers

**Before**: "I hope the AI agent doesn't make mistakes"
**After**: "The AI agent CANNOT make certain classes of mistakes"

### For Organizations

**Before**: Manual code review required to catch AI errors
**After**: Mathematical guarantees reduce review burden

### For Prob Comp Community

**Before**: "Probabilistic programming is useful for reasoning"
**After**: "Probabilistic programming can ENFORCE safety in AI systems"

---

## Implementation Strategy

### Phase 1: Wrapper for Claude Code SDK

```python
from amplifier.ccsdk import ClaudeCodeSDK
from llamppl import smc_steer

class SteeredAgent:
    def __init__(self, agent: ClaudeCodeSDK):
        self.agent = agent

    def generate(self, prompt: str, constraints: List[Callable]):
        """Generate with hard constraint satisfaction."""
        return smc_steer_wrapper(
            agent=self.agent,
            prompt=prompt,
            constraints=constraints
        )
```

### Phase 2: Common Constraint Library

```python
from amplifier.steering.constraints import (
    syntax_valid,
    type_checks,
    no_hallucinations,
    no_sql_injection,
    has_error_handling,
    follows_style_guide,
)

# Use pre-built constraints
code = agent.generate(
    prompt="Create login handler",
    constraints=[
        syntax_valid,
        type_checks,
        no_sql_injection,
        has_error_handling,
    ]
)
```

### Phase 3: Integration with Amplifier Agents

```python
# Existing Amplifier agents
from amplifier.agents import ZenArchitect, ModularBuilder

# Steered versions
steered_architect = SteeredAgent(
    ZenArchitect(),
    default_constraints=[
        syntax_valid,
        type_checks,
        follows_amplifier_philosophy,
    ]
)

steered_builder = SteeredAgent(
    ModularBuilder(),
    default_constraints=[
        syntax_valid,
        type_checks,
        no_hallucinations,
        follows_project_patterns,
    ]
)
```

---

## Demo Structure

```
demos/agent_steering/
├── README.md                       # This file
├── core_concept.py                 # Conceptual explanation
├── constraint_examples.py          # Constraint function library
├── unsteered_vs_steered.py        # Side-by-side comparison
├── real_world_scenario.py         # Login endpoint example
├── integration_amplifier.py       # How to integrate with Amplifier
└── benchmarks.py                  # Performance analysis
```

---

## Trade-offs

### Advantages
✓ Mathematical guarantees (not probabilities)
✓ Impossible to violate constraints
✓ Reduces manual review burden
✓ Catches errors at generation time

### Disadvantages
✗ Slower (SMC overhead: ~10-50x)
✗ Can fail if constraints too tight (particle depletion)
✗ Requires defining constraints upfront
✗ Research-grade tooling (LLaMPPL still maturing)

---

## When to Use Steering

### Use For:
- **Critical code generation** (auth, payments, security)
- **Type-safe APIs** (must compile, must type-check)
- **Regulated domains** (healthcare, finance)
- **Architectural enforcement** (must follow patterns)

### Don't Use For:
- **Exploratory coding** (too constraining)
- **Documentation** (no hard constraints needed)
- **High-volume generation** (too slow)
- **Creative tasks** (constraints limit creativity)

---

## The Bigger Picture

This is not just about Amplifier. This is about:

**"Can we make AI systems provably safe?"**

- Self-driving cars: Constraints on safety
- Medical diagnosis: Constraints on recommendations
- Financial trading: Constraints on risk
- **Code generation**: Constraints on correctness

**Probabilistic programming provides the mathematical framework for enforced safety.**

---

## Next Steps

1. **Build minimal wrapper** - Steer a simple code generation task
2. **Define constraint library** - Common safety constraints
3. **Benchmark overhead** - Measure slowdown vs guarantee
4. **Show compelling demo** - Unsteered vs steered comparison
5. **Write paper** - "Provably Safe AI Coding Agents via SMC Steering"

---

## References

- LLaMPPL Paper: https://arxiv.org/abs/2306.03081
- Amplifier: https://github.com/microsoft/amplifier
- GenJax: https://github.com/probcomp/genjax
- Strategic Vision: `../STRATEGIC_VISION.md`
