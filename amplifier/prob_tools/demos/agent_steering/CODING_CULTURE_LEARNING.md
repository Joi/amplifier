# Learning Coding Culture Through Meta-Cognitive Patterns

**The Big Idea**: Mine git history not just for bugs, but for *how teams think and work*.

---

## What is "Coding Culture"?

Not just style guides or linting rules. It's:

- **How** teams approach problems
- **When** they choose complexity vs simplicity
- **Why** they make certain architectural decisions
- **What** patterns of thinking lead to success vs failure

**Examples**:
- "Move fast and break things" (Facebook)
- "Measure twice, cut once" (NASA)
- "Perfect is the enemy of good" (many startups)
- "Do one thing and do it well" (Unix philosophy)

---

## What You Could Learn from a Codebase

### 1. Decision-Making Patterns

**From commit messages + outcomes**:

```python
# Pattern: "Refactor to simplicity"
commits_with_simplify = find_commits(message_contains="simplify")

# Analyze outcomes
for commit in commits_with_simplify:
    lines_before = count_lines(commit.parent)
    lines_after = count_lines(commit)
    bugs_6_months_later = count_bugs_after(commit, days=180)

# Learn pattern:
# "Teams that simplify see 40% fewer bugs 6 months later"
```

**What this reveals**:
- This team VALUES simplicity
- Simplification is REWARDED (fewer bugs)
- Culture: "Delete code, don't just add"

### 2. Risk Tolerance Patterns

**From deployment frequency + rollback rates**:

```python
# Pattern: "Ship often, rollback when needed"
deployments = get_deployments(last_n_months=12)
rollbacks = get_rollbacks(last_n_months=12)

rollback_rate = len(rollbacks) / len(deployments)
# → 5% rollback rate

# Learn pattern:
# "Team ships 50 times/month, accepts 5% rollback rate"
```

**What this reveals**:
- High risk tolerance
- "Move fast" culture
- Trust in rollback mechanisms
- Culture: "Ship it, we can fix it"

### 3. Testing Philosophy Patterns

**From test coverage over time + bug rates**:

```python
# Pattern: "Test what matters, not everything"
commits = get_all_commits()

for commit in commits:
    test_coverage = measure_coverage(commit)
    test_lines = count_test_lines(commit)
    code_lines = count_code_lines(commit)
    ratio = test_lines / code_lines

# Find teams with:
# - Low coverage (30%) but low bugs → "Test critical paths only"
# - High coverage (90%) but high bugs → "Over-testing wrong things"
```

**What this reveals**:
- Testing philosophy: Coverage vs criticality
- Culture: "Test the money code, not the plumbing"

### 4. Collaboration Patterns

**From code review comments**:

```python
# Pattern: "What gets questioned in reviews?"
pr_comments = get_all_pr_comments()

concerns = categorize_comments(pr_comments)
# → 40% about security
# → 30% about performance
# → 20% about readability
# → 10% about tests

# Learn pattern:
# "Security is the top review concern"
```

**What this reveals**:
- Team priorities: Security > Performance > Readability
- Culture: "Security-first development"

### 5. Architecture Evolution Patterns

**From major refactoring events**:

```python
# Pattern: "When do they choose to refactor vs rewrite?"
big_changes = find_commits(changed_lines > 1000)

for change in big_changes:
    if is_refactor(change):
        # Kept existing structure
        success = measure_success(change, weeks=12)
    elif is_rewrite(change):
        # Started from scratch
        success = measure_success(change, weeks=12)

# Learn:
# Refactors succeed 70% of time
# Rewrites succeed 30% of time
```

**What this reveals**:
- Team learned: "Refactor > Rewrite"
- Culture: "Evolve, don't rebuild"

---

## Concrete Example: Learning from Amplifier's Own Codebase

### What We'd Discover

**From AGENTS.md and CLAUDE.md**:

```python
# Pattern: "Ruthless Simplicity"
philosophy_statements = extract_from_docs([
    "KISS principle taken to heart",
    "Every layer of abstraction must justify its existence",
    "Code you don't write has no bugs",
    "Favor clarity over cleverness",
])

# This IS the coding culture
```

**From commit history**:

```python
# Pattern: "Analysis before implementation"
commits = get_commits()

# Count commits with "Analyze" or "Design" before "Implement"
analysis_first = count_pattern(
    sequence=["analyze", "design", "implement"]
)

# Learn:
# 80% of features start with analysis doc
# Culture: "Think before coding"
```

**From git blame patterns**:

```python
# Pattern: "File ownership"
files = get_all_files()

for file in files:
    contributors = get_contributors(file)
    primary_author = max(contributors, key=lambda c: c.lines_contributed)

    if primary_author.percentage > 70:
        # Strong ownership
        ownership_model = "single owner"
    else:
        # Shared ownership
        ownership_model = "collaborative"

# Learn:
# 60% files have single primary owner
# Culture: "Clear ownership, collaborative reviews"
```

---

## Could You Share These Patterns?

**YES! This is incredibly valuable!**

### Use Case 1: Onboarding New Developers

**Instead of**:
```
"Read the style guide and good luck"
```

**Provide**:
```
Meta-Cognitive Patterns for This Codebase:

1. Simplicity First (90% of commits)
   - When in doubt, delete code
   - Example: PR #342 simplified auth from 500→100 lines

2. Measure Before Optimize (95% of optimizations)
   - Profile first, optimize hotspots only
   - Example: PR #456 profiled, found real bottleneck

3. Test Critical Paths (40% coverage, 0.1% bug rate)
   - We test money code, not plumbing
   - Example: Payment flow has 95% coverage, utils have 10%

4. Security First (security mentioned in 40% of reviews)
   - Every PR reviewed for security implications
   - Example: PR #567 blocked for missing input validation
```

**Value**: New dev learns *how we think*, not just *how we code*.

### Use Case 2: Cross-Team Learning

**Scenario**: Company has multiple teams, different cultures

```python
# Team A (Move Fast)
patterns_team_a = {
    "deployment_frequency": "50/month",
    "rollback_rate": "5%",
    "average_pr_size": "100 lines",
    "review_time": "2 hours",
}

# Team B (Move Carefully)
patterns_team_b = {
    "deployment_frequency": "5/month",
    "rollback_rate": "0.5%",
    "average_pr_size": "500 lines",
    "review_time": "2 days",
}

# Share patterns:
# "Team A ships 10x faster with 10x rollback rate"
# "Team B ships more stable but slower"

# Teams can learn from each other
```

**Value**: Make implicit culture explicit, enable learning.

### Use Case 3: AI Agent Alignment

**The killer application**:

```python
# Amplifier agent working on NEW codebase
agent = AmplifierAgent()

# Load that codebase's meta-cognitive patterns
patterns = extract_patterns_from_git(new_codebase)

# Configure agent to match culture
agent.configure(
    simplicity_bias=patterns["simplicity_first_percentage"],  # 90%
    test_coverage_target=patterns["average_test_coverage"],   # 40%
    security_priority=patterns["security_review_frequency"],  # High
    refactor_vs_rewrite=patterns["refactor_success_rate"],   # 70% refactor
)

# Now agent works LIKE this team works
agent.generate("Add payment feature")
# → Follows THEIR patterns, not generic best practices
```

**Value**: Agent learns "how we do things here" automatically.

---

## What Patterns Could Be Shared

### 1. Decision-Making Patterns

**Shareable as rules**:
```yaml
patterns:
  analysis_paralysis_prevention:
    trigger: "No data yet on performance/scale"
    action: "Start with simplest implementation"
    example: "PR #342: Started with dict cache, measured, then added Redis"

  premature_optimization:
    trigger: "Optimization without profiling"
    action: "Profile first, optimize hotspots only"
    example: "PR #456: Profiled, found 90% time in DB, optimized queries"
```

### 2. Architecture Patterns

**Shareable as preferences**:
```yaml
architecture:
  complexity_threshold:
    trigger: "More than 3 services proposed"
    action: "Justify with data: scale requirements, failure modes"
    example: "We stayed monolith until 1M users, then split"

  abstraction_level:
    trigger: "Generic framework proposed"
    action: "Solve 3 concrete cases first, then abstract"
    example: "Built 3 API clients, then created generic HTTP client"
```

### 3. Collaboration Patterns

**Shareable as norms**:
```yaml
collaboration:
  code_review_focus:
    security: 40%
    performance: 30%
    readability: 20%
    testing: 10%
    example: "Security questions asked in 40% of reviews"

  pr_size:
    preferred: "100-300 lines"
    max: "500 lines"
    rationale: "Easier to review thoroughly"
```

### 4. Quality Patterns

**Shareable as standards**:
```yaml
quality:
  testing_strategy:
    critical_paths: "90% coverage"
    utility_code: "20% coverage"
    rationale: "Test money code, not plumbing"

  bug_tolerance:
    production_bugs_per_month: "< 5"
    acceptable_downtime: "< 1 hour/month"
    example: "We ship fast, but roll back immediately on errors"
```

---

## How to Extract and Share These Patterns

### Phase 1: Extraction (GenJax)

```python
from amplifier.pattern_learning import PatternExtractor

extractor = PatternExtractor(repo_path="./")

# Extract meta-cognitive patterns
patterns = extractor.extract_patterns(
    types=[
        "decision_making",
        "architecture_evolution",
        "testing_philosophy",
        "collaboration_norms",
        "risk_tolerance",
    ]
)

# Get probability models
models = extractor.build_genjax_models(patterns)

# Example query:
outcome = models["refactor_vs_rewrite"].query(
    "If I refactor instead of rewrite, what's success rate?"
)
# → 70% success rate
```

### Phase 2: Validation (Check with Team)

```python
# Generate report
report = patterns.generate_report()

"""
EXTRACTED PATTERNS FROM YOUR CODEBASE:

1. Simplicity First (found in 90% of commits)
   Evidence:
   - PR #123: "Deleted 300 lines, simplified auth"
   - PR #234: "Removed abstraction, inlined logic"
   - PR #345: "Replaced framework with 20 lines"

   Is this accurate? [Y/N]
"""

# Team validates or corrects
```

### Phase 3: Sharing (Export)

```python
# Export as machine-readable patterns
patterns.export(
    format="yaml",
    output="codebase_patterns.yaml"
)

# Export as human-readable guide
patterns.export(
    format="markdown",
    output="HOW_WE_CODE.md"
)

# Export as agent configuration
patterns.export(
    format="agent_config",
    output="amplifier_agent_config.json"
)
```

### Phase 4: Application (Other Teams/Agents)

```python
# New team member
onboarding_guide = patterns.generate_onboarding_guide()
# → "Here's how we think about code here"

# AI agent on different codebase
other_agent = AmplifierAgent()
other_agent.load_patterns("codebase_patterns.yaml")
# → Agent now works like YOUR team

# Cross-team learning
all_teams = [team_a_patterns, team_b_patterns, team_c_patterns]
comparison = compare_patterns(all_teams)
# → "Team A ships 5x faster but with 3x rollback rate"
```

---

## Real-World Example: Learning from Django

**If we analyzed Django's codebase**:

```python
patterns_django = {
    "decision_making": {
        "batteries_included": {
            "frequency": "95%",
            "evidence": "Admin, ORM, auth all built-in",
            "philosophy": "Don't make users assemble basics"
        },
        "backwards_compatibility": {
            "frequency": "99%",
            "evidence": "Deprecation warnings, migration paths",
            "philosophy": "Never break user code without warning"
        }
    },

    "architecture": {
        "monolithic_preference": {
            "frequency": "90%",
            "evidence": "Single framework, not microservices",
            "philosophy": "Cohesion over distribution"
        }
    },

    "testing": {
        "comprehensive_coverage": {
            "coverage": "95%",
            "evidence": "20K+ tests in codebase",
            "philosophy": "Test everything, stability matters"
        }
    },

    "collaboration": {
        "consensus_driven": {
            "evidence": "Django Enhancement Proposals (DEPs)",
            "philosophy": "Community decides features"
        }
    }
}

# Share these patterns
export_as_guide(patterns_django, "HOW_DJANGO_THINKS.md")
```

**Value**: New Django contributor learns *Django's way of thinking*, not just syntax.

---

## The Ultimate Use Case: Pattern Marketplaces

### Vision: "Coding Culture as a Service"

```python
# Pattern marketplace
marketplace = PatternMarketplace()

# Browse patterns
patterns = marketplace.search(
    tags=["startups", "move-fast", "python"],
    min_stars=1000
)

# Example results:
# 1. Airbnb's Testing Patterns (4.2★)
# 2. Stripe's Security-First Patterns (4.8★)
# 3. Netflix's Chaos Engineering Patterns (4.5★)

# Apply to your codebase
your_codebase = Codebase("./")
your_codebase.adopt_patterns(patterns["stripe_security_first"])

# Your AI agents now work like Stripe's team
agent = AmplifierAgent()
agent.load_patterns("stripe_security_first")
# → Agent prioritizes security like Stripe does
```

**Value**: Share and adopt proven patterns from successful teams.

---

## Summary: Is This a Good Way to Learn Coding Culture?

### ✅ **YES! Because:**

1. **Captures implicit knowledge**
   - What's never written in docs
   - How teams actually work vs how they say they work

2. **Evidence-based**
   - Not opinions, but patterns from real commits
   - Probabilistic: "70% of refactors succeed"

3. **Transferable**
   - Export as docs, configs, agent settings
   - New devs learn faster
   - Agents align with team culture

4. **Comparable**
   - Compare Team A vs Team B patterns
   - Learn from successful teams
   - Identify anti-patterns

### ✅ **What You Could Learn:**

- Decision-making patterns (simplicity, premature optimization)
- Risk tolerance (ship frequency, rollback rates)
- Testing philosophy (coverage targets, what to test)
- Architecture preferences (refactor vs rewrite)
- Collaboration norms (review focus, PR size)
- Quality standards (acceptable bug rates)

### ✅ **Could You Share?**

**Absolutely!**
- Export as onboarding docs
- Configure AI agents to match culture
- Create pattern marketplaces
- Enable cross-team learning

---

## The Amplifier Opportunity

**Combine probabilistic programming + meta-cognitive patterns:**

1. **Extract** patterns from git history (GenJax)
2. **Model** success rates (causal inference)
3. **Enforce** patterns in new code (LLaMPPL steering)
4. **Share** patterns across teams/codebases

**Result**: AI agents that learn and embody team culture, not just code patterns.

**This is the killer feature**: "Amplifier agents that code like YOUR team codes."
