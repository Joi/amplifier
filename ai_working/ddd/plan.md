# Knowledge Graph Phase 1: Implementation Plan

**Project**: Knowledge Graph System - Phase 1 Foundation
**Repository**: obs-dailynotes
**Timeline**: 2 weeks
**Status**: Planning Complete → Ready for Implementation
**Created**: 2025-11-13

---

## Executive Summary

**What We're Building:**
A minimal file-based knowledge graph that transforms Switchboard's 880 person markdown files into a queryable network enabling basic relationship discovery and path finding.

**Why Minimal Approach:**
Phase 1 only requires node extraction and basic graph traversal (BFS). Implementing this directly in ~200 lines of JavaScript is simpler, faster, and more maintainable than adopting a graph library. The modular design allows upgrading to graphology/NetworkX later if Phase 3 requirements demand it.

**Success Criteria:**
- ✅ 880+ person nodes extracted from frontmatter
- ✅ Graph stored as JSON at `~/switchboard/.data/knowledge_graph.json`
- ✅ CLI commands: `kg:build`, `kg:query`
- ✅ Working queries: `find-path`, `ego-network`
- ✅ Complete in 2 weeks

---

## Architecture Decision: Approach C (Minimal File-Based)

### Chosen Approach

**Minimal File-Based Implementation** - No graph library, pure JavaScript data structures.

**Rationale:**
1. **Ruthless Simplicity**: Phase 1 scope doesn't justify library complexity
2. **Fast Implementation**: ~200 lines total, 1 week to implement + test
3. **Clear Code**: Arrays and objects, no library API to learn
4. **Future-Proof**: Can upgrade to graph library in Phase 3 without breaking contract

**Rejected Alternatives:**
- **Approach A (graphology)**: Over-engineered for Phase 1, would use <5% of API
- **Approach B (NetworkX)**: Cross-repo complexity, Python dependency in Node.js workflow

### Philosophy Alignment

✅ **Ruthless Simplicity**: No dependencies beyond gray-matter (already used)
✅ **Start Minimal**: Only Phase 1 scope, defer everything else
✅ **Modular Design**: Self-contained brick with clear public contract
✅ **Regenerate Don't Patch**: Can swap internals later without breaking contract

---

## Implementation Structure

### File Organization

```
obs-dailynotes/
├── lib/knowledgeGraph/
│   ├── README.md           # Contract: purpose, inputs, outputs, dependencies
│   ├── index.js            # Public API (exports buildGraph, queryGraph)
│   ├── extractors.js       # Parse person frontmatter → node objects
│   ├── graphBuilder.js     # Build graph from 880 person files
│   ├── queries.js          # BFS path finding, ego network filtering
│   ├── models.js           # Node/edge type definitions and schemas
│   └── __tests__/
│       ├── extractors.test.js
│       ├── graphBuilder.test.js
│       └── queries.test.js
├── bin/
│   └── kg.js               # CLI entry point
└── package.json            # Scripts: kg:build, kg:query

~/switchboard/.data/
└── knowledge_graph.json    # Generated graph storage
```

### Data Model

**Node Structure:**
```javascript
{
  id: "adam-back",           // From frontmatter.slug
  type: "person",             // Fixed for Phase 1
  name: "Adam Back",          // From filename
  emails: ["adam@..."],       // From frontmatter.emails
  aliases: ["aback"]          // From frontmatter.aliases
}
```

**Graph Structure:**
```javascript
{
  nodes: [
    { id, type, name, emails, aliases },
    ...
  ],
  edges: [],  // Phase 1: empty, populated in Phase 2
  metadata: {
    version: "1.0",
    created: "2025-11-13T...",
    nodeCount: 880,
    edgeCount: 0
  }
}
```

### Public Contract (The "Stud")

**CLI Commands:**
```bash
# Build graph from person files
npm run kg:build

# Query: find path between two people
npm run kg:query -- find-path "Joi Ito" "Adam Back"

# Query: get ego network (people within N connections)
npm run kg:query -- ego-network "Joi Ito" --depth 1
```

**API Interface (for programmatic use):**
```javascript
import { buildGraph, queryGraph } from './lib/knowledgeGraph/index.js';

// Build
const graph = await buildGraph('~/switchboard/Private/People');

// Query
const path = queryGraph(graph, 'find-path', { start: 'joi-ito', end: 'adam-back' });
const network = queryGraph(graph, 'ego-network', { person: 'joi-ito', depth: 1 });
```

---

## Implementation Tasks

### Week 1: Core Implementation

#### Task 1.1: Set Up Module Structure (1 hour)
- [ ] Create `lib/knowledgeGraph/` directory
- [ ] Create stub files: `index.js`, `extractors.js`, `graphBuilder.js`, `queries.js`, `models.js`
- [ ] Create `__tests__/` directory
- [ ] Update `package.json` with `kg:*` scripts

**Acceptance Criteria:**
- Directory structure matches plan
- `npm run kg:build` executes (even if stubbed)

---

#### Task 1.2: Implement Node Extraction (3 hours)
**File:** `extractors.js`

```javascript
import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';

export function extractPersonNode(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const { data } = matter(content);

  return {
    id: data.slug || path.basename(filePath, '.md').toLowerCase(),
    type: 'person',
    name: path.basename(filePath, '.md').replace(/-/g, ' ')
      .split(' ')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' '),
    emails: data.emails || [],
    aliases: data.aliases || []
  };
}

export function extractAllPersons(peopleDir) {
  const files = glob.sync(`${peopleDir}/**/*.md`);
  return files.map(extractPersonNode);
}
```

**Tests:**
```javascript
// extractors.test.js
test('extracts node from frontmatter', () => {
  const node = extractPersonNode('test-fixtures/adam-back.md');
  expect(node.id).toBe('adam-back');
  expect(node.name).toBe('Adam Back');
  expect(node.emails).toContain('adam@blockstream.com');
});

test('handles missing frontmatter fields', () => {
  const node = extractPersonNode('test-fixtures/minimal.md');
  expect(node.emails).toEqual([]);
  expect(node.aliases).toEqual([]);
});
```

**Acceptance Criteria:**
- Extracts all frontmatter fields correctly
- Handles missing fields gracefully
- Tests pass (100% coverage)

---

#### Task 1.3: Implement Graph Builder (2 hours)
**File:** `graphBuilder.js`

```javascript
import { extractAllPersons } from './extractors.js';

export function buildGraph(peopleDir) {
  const nodes = extractAllPersons(peopleDir);

  return {
    nodes,
    edges: [],  // Phase 1: no edges yet
    metadata: {
      version: '1.0',
      created: new Date().toISOString(),
      nodeCount: nodes.length,
      edgeCount: 0
    }
  };
}

export function saveGraph(graph, outputPath) {
  fs.writeFileSync(
    outputPath,
    JSON.stringify(graph, null, 2),
    'utf-8'
  );
}
```

**Tests:**
```javascript
test('builds graph from person directory', () => {
  const graph = buildGraph('test-fixtures/people');
  expect(graph.nodes.length).toBeGreaterThan(0);
  expect(graph.metadata.nodeCount).toBe(graph.nodes.length);
});

test('saves graph to JSON', () => {
  const graph = buildGraph('test-fixtures/people');
  saveGraph(graph, 'test-output/graph.json');

  const loaded = JSON.parse(fs.readFileSync('test-output/graph.json', 'utf-8'));
  expect(loaded.nodes).toEqual(graph.nodes);
});
```

**Acceptance Criteria:**
- Builds graph from 880 person files
- Saves to `~/switchboard/.data/knowledge_graph.json`
- Tests pass

---

#### Task 1.4: Implement BFS Path Finding (4 hours)
**File:** `queries.js`

```javascript
export function findPath(graph, startId, endId) {
  // BFS implementation
  const queue = [[startId]];
  const visited = new Set([startId]);

  while (queue.length > 0) {
    const path = queue.shift();
    const node = path[path.length - 1];

    if (node === endId) {
      return path;  // Found path
    }

    // Get neighbors (Phase 1: based on edges, empty for now)
    const neighbors = getNeighbors(graph, node);

    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push([...path, neighbor]);
      }
    }
  }

  return null;  // No path found
}

function getNeighbors(graph, nodeId) {
  // Phase 1: Return empty (no edges yet)
  // Phase 2: Will filter graph.edges for this node
  return [];
}
```

**Tests:**
```javascript
test('finds shortest path between nodes', () => {
  const graph = {
    nodes: [
      { id: 'a' }, { id: 'b' }, { id: 'c' }
    ],
    edges: [
      { from: 'a', to: 'b' },
      { from: 'b', to: 'c' }
    ]
  };

  const path = findPath(graph, 'a', 'c');
  expect(path).toEqual(['a', 'b', 'c']);
});

test('returns null when no path exists', () => {
  const graph = {
    nodes: [{ id: 'a' }, { id: 'b' }],
    edges: []
  };

  const path = findPath(graph, 'a', 'b');
  expect(path).toBeNull();
});
```

**Acceptance Criteria:**
- BFS correctly finds shortest path
- Returns null when no path exists
- Tests pass (including edge cases)

---

#### Task 1.5: Implement Ego Network Query (2 hours)
**File:** `queries.js`

```javascript
export function egoNetwork(graph, personId, depth = 1) {
  const visited = new Set([personId]);
  const currentLayer = [personId];

  for (let d = 0; d < depth; d++) {
    const nextLayer = [];

    for (const nodeId of currentLayer) {
      const neighbors = getNeighbors(graph, nodeId);

      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          nextLayer.push(neighbor);
        }
      }
    }

    currentLayer = nextLayer;
  }

  // Return subgraph of visited nodes
  return {
    nodes: graph.nodes.filter(n => visited.has(n.id)),
    edges: graph.edges.filter(e =>
      visited.has(e.from) && visited.has(e.to)
    )
  };
}
```

**Tests:**
```javascript
test('returns nodes within depth', () => {
  const graph = {
    nodes: [
      { id: 'a' }, { id: 'b' }, { id: 'c' }, { id: 'd' }
    ],
    edges: [
      { from: 'a', to: 'b' },
      { from: 'b', to: 'c' },
      { from: 'c', to: 'd' }
    ]
  };

  const network = egoNetwork(graph, 'a', 1);
  expect(network.nodes.map(n => n.id)).toEqual(['a', 'b']);
});
```

**Acceptance Criteria:**
- Returns correct subgraph within depth
- Handles depth = 0 (just the node itself)
- Tests pass

---

#### Task 1.6: Implement CLI (2 hours)
**File:** `bin/kg.js`

```javascript
#!/usr/bin/env node
import { Command } from 'commander';
import { buildGraph, saveGraph } from '../lib/knowledgeGraph/graphBuilder.js';
import { findPath, egoNetwork } from '../lib/knowledgeGraph/queries.js';

const program = new Command();

program
  .name('kg')
  .description('Knowledge Graph CLI')
  .version('1.0.0');

program
  .command('build')
  .description('Build graph from person files')
  .action(async () => {
    console.log('Building knowledge graph...');
    const graph = await buildGraph(process.env.HOME + '/switchboard/Private/People');
    saveGraph(graph, process.env.HOME + '/switchboard/.data/knowledge_graph.json');
    console.log(`✓ Built graph: ${graph.metadata.nodeCount} nodes`);
  });

program
  .command('query <type> [args...]')
  .description('Query the knowledge graph')
  .action(async (type, args) => {
    const graphPath = process.env.HOME + '/switchboard/.data/knowledge_graph.json';
    const graph = JSON.parse(fs.readFileSync(graphPath, 'utf-8'));

    if (type === 'find-path') {
      const [start, end] = args;
      const path = findPath(graph, start, end);
      if (path) {
        console.log('Path found:');
        console.log(path.join(' → '));
      } else {
        console.log('No path found');
      }
    } else if (type === 'ego-network') {
      const [person, depthStr] = args;
      const depth = parseInt(depthStr || '1');
      const network = egoNetwork(graph, person, depth);
      console.log(`Ego network (depth ${depth}):`);
      console.log(`${network.nodes.length} nodes`);
    }
  });

program.parse();
```

**Package.json scripts:**
```json
{
  "scripts": {
    "kg:build": "node bin/kg.js build",
    "kg:query": "node bin/kg.js query"
  }
}
```

**Acceptance Criteria:**
- `npm run kg:build` builds and saves graph
- `npm run kg:query -- find-path A B` returns path
- `npm run kg:query -- ego-network X 1` returns network
- Clear user output

---

### Week 2: Testing & Documentation

#### Task 2.1: Integration Tests (4 hours)
- [ ] Test full workflow: build → save → load → query
- [ ] Test with real person files (sample of 10 from ~/switchboard)
- [ ] Verify JSON schema matches documentation
- [ ] Test error cases (missing files, invalid frontmatter)

**Acceptance Criteria:**
- All integration tests pass
- Works with real Switchboard data
- Handles errors gracefully

---

#### Task 2.2: Performance Validation (2 hours)
- [ ] Benchmark: Build graph from 880 files
- [ ] Benchmark: Query performance (find-path, ego-network)
- [ ] Ensure build completes in <10 seconds
- [ ] Ensure queries complete in <100ms

**Acceptance Criteria:**
- Build time: <10 seconds for 880 files
- Query time: <100ms per query
- No memory leaks

---

#### Task 2.3: Documentation Updates (3 hours)
- [ ] Update `lib/knowledgeGraph/README.md` with actual implementation
- [ ] Add usage examples to Knowledge-Graph.md
- [ ] Document CLI commands in package.json
- [ ] Create troubleshooting guide

**Acceptance Criteria:**
- README accurately describes implementation
- Examples work when copy-pasted
- Users can self-serve common issues

---

#### Task 2.4: End-to-End Validation (3 hours)
- [ ] Run `kg:build` on full 880 person dataset
- [ ] Verify all nodes extracted correctly
- [ ] Test queries with real person IDs
- [ ] Compare results with manual verification

**Acceptance Criteria:**
- 880+ nodes in graph
- All frontmatter fields populated
- Queries return sensible results

---

## Success Criteria (Phase 1)

### Functional Requirements
- ✅ Extracts 880+ person nodes from frontmatter
- ✅ Stores graph as JSON at `~/switchboard/.data/knowledge_graph.json`
- ✅ CLI command: `npm run kg:build` (builds in <10s)
- ✅ CLI command: `npm run kg:query -- find-path A B` (returns path or null)
- ✅ CLI command: `npm run kg:query -- ego-network X` (returns subgraph)

### Non-Functional Requirements
- ✅ Code: ~200 lines total (excluding tests)
- ✅ No external dependencies beyond gray-matter
- ✅ Test coverage: >80%
- ✅ Documentation: Complete and accurate
- ✅ Philosophy aligned: Ruthless simplicity

### Ready for Phase 2 When:
- ✅ All Phase 1 tests pass
- ✅ Works with real Switchboard data
- ✅ User can build and query graph via CLI
- ✅ Code is clean, documented, and modular

---

## Testing Strategy

### Unit Tests (60%)
- `extractors.test.js`: Node extraction logic
- `graphBuilder.test.js`: Graph construction
- `queries.test.js`: BFS, ego network algorithms

### Integration Tests (30%)
- Build → Save → Load → Query workflow
- Real data validation (sample files)
- Error handling (missing files, bad frontmatter)

### End-to-End Tests (10%)
- Full 880 person dataset
- Performance benchmarks
- CLI usability

### Test Fixtures
```
lib/knowledgeGraph/__tests__/fixtures/
├── people/
│   ├── adam-back.md
│   ├── minimal.md
│   └── missing-fields.md
└── expected-outputs/
    ├── basic-graph.json
    └── path-example.json
```

---

## Future Considerations (Out of Scope for Phase 1)

**Deferred to Phase 2:**
- Edge extraction (from "Connected People" sections)
- Relationship strength calculation
- Organization inference

**Deferred to Phase 3:**
- Expert finder (requires topic data)
- Introduction suggestions (requires inference)
- Community detection (requires graph algorithms)

**Deferred to Phase 4:**
- Visualization (HTML viewer)
- Temporal evolution
- Interactive exploration

**Why deferred?**
Phase 1 proves the concept with minimal scope. If it succeeds, we expand. If it fails, we learned cheaply.

---

## Risk Mitigation

### Risk 1: Frontmatter Inconsistency
**Probability:** Medium
**Impact:** High (can't extract nodes)
**Mitigation:**
- Test with sample of 50 random files first
- Handle missing fields gracefully
- Log warnings for malformed frontmatter

### Risk 2: Performance at Scale
**Probability:** Low
**Impact:** Medium (slow builds)
**Mitigation:**
- Benchmark early with full 880 files
- Optimize if build time >10 seconds
- Consider streaming/incremental builds if needed

### Risk 3: Scope Creep
**Probability:** High
**Impact:** Medium (timeline slips)
**Mitigation:**
- Strictly limit to Phase 1 scope
- Document deferred features prominently
- Resist adding "just one more thing"

---

## Definition of Done

Phase 1 is complete when:

1. **Code Complete:**
   - [ ] All 6 implementation tasks done
   - [ ] Tests pass (>80% coverage)
   - [ ] No linter errors

2. **Documentation Complete:**
   - [ ] README.md updated with actual implementation
   - [ ] CLI usage documented
   - [ ] Examples work when copy-pasted

3. **Validation Complete:**
   - [ ] Works with full 880 person dataset
   - [ ] Performance meets benchmarks (<10s build, <100ms query)
   - [ ] User can successfully build and query graph

4. **Philosophy Aligned:**
   - [ ] Code is simple and direct (~200 lines)
   - [ ] No unnecessary abstractions
   - [ ] Modular design maintained

5. **Ready for Phase 2:**
   - [ ] Contract (CLI commands) is stable
   - [ ] Can add edge extraction without breaking changes
   - [ ] Foundation is solid

---

## Timeline Summary

**Week 1: Implementation**
- Day 1: Setup + Node Extraction (Tasks 1.1, 1.2)
- Day 2-3: Graph Builder + BFS (Tasks 1.3, 1.4)
- Day 4: Ego Network + CLI (Tasks 1.5, 1.6)
- Day 5: Buffer for blockers

**Week 2: Validation**
- Day 6-7: Integration tests + Performance (Tasks 2.1, 2.2)
- Day 8: Documentation updates (Task 2.3)
- Day 9: End-to-end validation (Task 2.4)
- Day 10: Buffer + final review

**Total: 10 business days (2 weeks)**

---

## Approval Checklist

Before proceeding to Phase 2 (Docs), verify:

- [ ] This plan aligns with Knowledge-Graph-Design.md vision
- [ ] Minimal approach is appropriate for Phase 1 scope
- [ ] Success criteria are clear and measurable
- [ ] Timeline is realistic (2 weeks)
- [ ] Risks are identified and mitigated
- [ ] Philosophy alignment is verified

**If all checked: Proceed to /ddd:2-docs (Documentation Phase)**

---

**Plan Status:** ✅ Complete - Ready for User Review
**Next Step:** Present plan to user for feedback and approval
**After Approval:** Begin Phase 2 - Documentation
