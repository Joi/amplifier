# Phase 2 Integration Test Cases

This document defines comprehensive integration test cases for validating Phase 2 (Linear Execution Engine) with realistic workflows.

## Test Strategy

### Validation Goals
1. **End-to-end execution** - Full workflow runs to completion
2. **Context flow** - Variables pass correctly between nodes
3. **Output extraction** - Named outputs captured accurately
4. **Error handling** - Clear errors for missing context/failures
5. **AI integration** - ClaudeSession executes prompts correctly
6. **Golden file validation** - Results match expected outcomes

### Test Categories

#### Unit Tests (tests/test_*.py)
- Context interpolation with various patterns
- Output extraction from different response formats
- Node execution with mocked AI responses
- Engine orchestration logic

#### Integration Tests (tests/integration_test_*.py)
- Full workflow execution with real AI calls
- Golden file validation against expected results
- Error scenario handling

## Integration Test Workflows

### Test 1: Code Review Workflow (Existing)
**File**: `examples/simple_linear.yaml`

**Purpose**: Validate basic 3-node sequential execution

**Nodes**:
1. `analyze` - Analyze code structure and patterns
2. `find-bugs` - Identify potential bugs
3. `summarize` - Create final summary

**Context Flow**:
```
Initial: {file_path: "src/auth.py"}
After analyze: {file_path: "...", code_structure: "..."}
After find-bugs: {..., code_structure: "...", bugs_found: "..."}
After summarize: {..., final_summary: "..."}
```

**Validation**:
- All 3 nodes execute in order
- Context flows through nodes
- Final summary references both structure and bugs

---

### Test 2: Research Paper Analysis
**File**: `examples/integration_tests/research_analysis.yaml`

**Purpose**: Multi-stage document analysis with progressive refinement

**Workflow**:
```yaml
workflow:
  name: "research-paper-analysis"
  description: "Analyze research paper through multiple lenses"
  context:
    paper_path: "docs/ai_safety_paper.pdf"

nodes:
  - id: "extract-thesis"
    name: "Extract Core Thesis"
    prompt: |
      Read the research paper at {paper_path} and extract:
      1. Main thesis statement
      2. Key research questions
      3. Core methodology

      Provide structured output:
      thesis: <main thesis>
      questions: <key questions>
      methodology: <approach>
    outputs: [thesis, questions, methodology]
    next: "evaluate-evidence"

  - id: "evaluate-evidence"
    name: "Evaluate Evidence Quality"
    prompt: |
      Given the thesis: "{thesis}"
      And methodology: "{methodology}"

      Evaluate the quality and strength of evidence presented:
      1. Data sources and reliability
      2. Statistical rigor
      3. Potential biases

      Provide:
      evidence_quality: <assessment>
      strengths: <key strengths>
      weaknesses: <key weaknesses>
    outputs: [evidence_quality, strengths, weaknesses]
    next: "synthesize-critique"

  - id: "synthesize-critique"
    name: "Synthesize Critical Analysis"
    prompt: |
      Create a comprehensive critique synthesizing:

      Thesis: {thesis}
      Questions: {questions}
      Evidence Quality: {evidence_quality}
      Strengths: {strengths}
      Weaknesses: {weaknesses}

      Provide balanced analysis with:
      overall_assessment: <summary>
      recommendations: <next steps>
    outputs: [overall_assessment, recommendations]
    type: "terminal"
```

**Context Flow**:
```
Initial: {paper_path: "docs/ai_safety_paper.pdf"}
After extract-thesis: {paper_path, thesis, questions, methodology}
After evaluate-evidence: {..., evidence_quality, strengths, weaknesses}
After synthesize-critique: {..., overall_assessment, recommendations}
```

**Validation Points**:
- Each node references outputs from previous nodes
- Progressive refinement of analysis
- Final synthesis incorporates all prior work
- Complex context interpolation with multiple variables

---

### Test 3: Data Transformation Pipeline
**File**: `examples/integration_tests/data_pipeline.yaml`

**Purpose**: Data processing with validation and transformation

**Workflow**:
```yaml
workflow:
  name: "data-transformation-pipeline"
  description: "Clean, validate, and transform dataset"
  context:
    input_csv: "data/raw_users.csv"
    date_format: "YYYY-MM-DD"

nodes:
  - id: "load-and-inspect"
    name: "Load and Inspect Data"
    prompt: |
      Load the CSV file at {input_csv} and provide:
      1. Row count
      2. Column names and types
      3. Sample of first 3 rows
      4. Any obvious data quality issues

      Output:
      row_count: <number>
      columns: <list>
      sample_data: <first 3 rows>
      issues: <identified issues>
    outputs: [row_count, columns, sample_data, issues]
    next: "validate-schema"

  - id: "validate-schema"
    name: "Validate Data Schema"
    prompt: |
      Given the data structure:
      Columns: {columns}
      Sample: {sample_data}

      Validate against expected schema:
      - user_id (integer)
      - email (string, valid format)
      - created_at (date, format: {date_format})
      - status (enum: active, inactive, pending)

      Report:
      schema_valid: true/false
      validation_errors: <any errors found>
      correction_steps: <how to fix>
    outputs: [schema_valid, validation_errors, correction_steps]
    next: "transform-data"

  - id: "transform-data"
    name: "Transform and Enrich"
    prompt: |
      Apply transformations:
      1. Normalize email addresses to lowercase
      2. Parse created_at to {date_format}
      3. Add derived field: account_age_days
      4. Filter: only status='active'

      Given schema validation: {schema_valid}
      Apply corrections: {correction_steps}

      Report:
      transformed_count: <rows after transformation>
      summary_stats: <min/max/avg account_age>
      output_path: <where to save>
    outputs: [transformed_count, summary_stats, output_path]
    type: "terminal"
```

**Context Flow**:
```
Initial: {input_csv: "...", date_format: "YYYY-MM-DD"}
After load: {..., row_count, columns, sample_data, issues}
After validate: {..., schema_valid, validation_errors, correction_steps}
After transform: {..., transformed_count, summary_stats, output_path}
```

**Validation Points**:
- Context variables used in multiple nodes
- Validation results influence transformation
- Numeric and structured outputs
- Error handling for invalid schema

---

### Test 4: Content Synthesis Workflow
**File**: `examples/integration_tests/content_synthesis.yaml`

**Purpose**: Multi-source content aggregation and synthesis

**Workflow**:
```yaml
workflow:
  name: "content-synthesis"
  description: "Synthesize insights from multiple sources"
  context:
    topic: "Large Language Models"
    sources: "docs/llm/*.md"

nodes:
  - id: "scan-sources"
    name: "Scan and Catalog Sources"
    prompt: |
      Scan directory {sources} for documents about {topic}.

      For each document, extract:
      1. Title
      2. Main themes (3-5 keywords)
      3. Key claims or insights
      4. Publication date if available

      Provide:
      source_count: <number of documents>
      source_list: <list with metadata>
    outputs: [source_count, source_list]
    next: "identify-themes"

  - id: "identify-themes"
    name: "Identify Common Themes"
    prompt: |
      Across {source_count} sources about {topic}:
      Sources: {source_list}

      Identify:
      1. Recurring themes (mentioned in 3+ sources)
      2. Conflicting viewpoints
      3. Emerging trends
      4. Knowledge gaps

      Output:
      common_themes: <list of themes>
      conflicts: <list of disagreements>
      trends: <emerging patterns>
      gaps: <what's missing>
    outputs: [common_themes, conflicts, trends, gaps]
    next: "synthesize-insights"

  - id: "synthesize-insights"
    name: "Synthesize Unified Insights"
    prompt: |
      Create a cohesive synthesis on {topic}.

      Integrate:
      - Common themes: {common_themes}
      - Conflicts to address: {conflicts}
      - Emerging trends: {trends}
      - Gaps to highlight: {gaps}

      Generate:
      1. Executive summary (3-5 sentences)
      2. Key insights (5-7 bullet points)
      3. Areas for further research

      Output:
      executive_summary: <concise overview>
      key_insights: <main takeaways>
      research_areas: <future directions>
    outputs: [executive_summary, key_insights, research_areas]
    type: "terminal"
```

**Context Flow**:
```
Initial: {topic: "LLM", sources: "docs/llm/*.md"}
After scan: {..., source_count, source_list}
After identify: {..., common_themes, conflicts, trends, gaps}
After synthesize: {..., executive_summary, key_insights, research_areas}
```

**Validation Points**:
- Complex multi-variable context interpolation
- List-based outputs
- Progressive insight building
- Multiple outputs extracted per node

---

### Test 5: Error Scenarios
**File**: `examples/integration_tests/error_scenarios.yaml`

**Purpose**: Validate error handling and recovery

**Test Cases**:

#### 5a: Missing Context Variable
```yaml
nodes:
  - id: "broken-node"
    prompt: "Analyze the file at {nonexistent_var}"
    # Should fail with clear error: "Missing context variable: nonexistent_var"
```

#### 5b: Output Extraction Failure
```yaml
nodes:
  - id: "missing-outputs"
    prompt: "Just analyze this."
    outputs: [analysis, recommendations]
    # Should handle missing outputs gracefully
```

#### 5c: Empty Workflow
```yaml
workflow:
  name: "empty-workflow"
  description: "No nodes"
nodes: []
# Should fail validation from Phase 1
```

---

## Test Execution Plan

### Phase 2a: Unit Tests with Mocks
```bash
pytest tests/test_context.py -v
pytest tests/test_executor.py -v
pytest tests/test_engine.py -v
```

### Phase 2b: Integration Tests (Mock AI)
```bash
pytest tests/integration_test_workflows.py -v --mock-ai
```

### Phase 2c: Integration Tests (Real AI)
```bash
pytest tests/integration_test_workflows.py -v --real-ai
```

### Phase 2d: Golden File Generation
```bash
pytest tests/integration_test_workflows.py --generate-golden
```

## Success Criteria

- ✅ All unit tests pass (context, executor, engine)
- ✅ Integration tests pass with mocked AI responses
- ✅ At least 2 integration tests pass with real AI
- ✅ Golden files generated and validated
- ✅ Error scenarios handled gracefully
- ✅ Clear, actionable error messages
- ✅ Execution progress visible in logs

## Golden File Structure

```
tests/golden/
├── simple_linear_result.json       # Test 1
├── research_analysis_result.json   # Test 2
├── data_pipeline_result.json       # Test 3
├── content_synthesis_result.json   # Test 4
└── error_scenarios/
    ├── missing_context.json
    ├── missing_outputs.json
    └── empty_workflow.json
```

Each golden file contains:
```json
{
  "workflow_id": "workflow-name",
  "status": "completed",
  "total_time": 45.23,
  "node_results": [
    {
      "node_id": "node-1",
      "status": "success",
      "outputs": {"key": "value"},
      "execution_time": 12.5
    }
  ],
  "final_context": {
    "all": "accumulated context"
  }
}
```
