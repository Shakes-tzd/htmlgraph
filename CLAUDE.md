# HtmlGraph - "HTML is All You Need"

---

## 🤖 For AI Agents

**→ See [AGENTS.md](./AGENTS.md) for complete AI agent documentation**

This file (CLAUDE.md) contains project vision, architecture, and roadmap.

For SDK usage, deployment instructions, and agent workflows, see:
- **[AGENTS.md](./AGENTS.md)** - Python SDK, API, CLI, deployment, best practices
- **[GEMINI.md](./GEMINI.md)** - Gemini-specific integration notes

---

## Project Vision

HtmlGraph is a lightweight graph database framework built entirely on web standards (HTML, CSS, JavaScript) for AI agent coordination and human observability. It eliminates the need for external graph databases (Neo4j, Memgraph) by using HTML files as nodes, hyperlinks as edges, and CSS selectors as the query language.

**Tagline**: "HTML is All You Need"

**Core Philosophy**: The web is already a giant graph database. AI agents should use web standards, not reinvent them.

## Why This Exists

### The Problem
Modern AI agent systems are drowning in complexity:
- Neo4j/Memgraph for graph databases (Docker, JVM, learn Cypher)
- Redis for caching and state management
- PostgreSQL for persistent storage
- Custom protocols for agent coordination
- Proprietary formats for agent memory (JSON, YAML with manual references)
- Separate UIs for human observability

### The Solution
HTML already provides everything needed:
- ✅ **Graph structure** - Hyperlinks are native edges
- ✅ **Human readability** - Browsers render it beautifully
- ✅ **Machine parsability** - justhtml, DOMParser built-in
- ✅ **Query language** - CSS selectors (everyone knows them)
- ✅ **Version control** - Text diffs work perfectly
- ✅ **Presentation layer** - CSS styling included
- ✅ **Zero dependencies** - No Docker, no JVM, no build tools
- ✅ **Ubiquity** - Works everywhere, offline-first

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  Browser renders HTML + CSS (human view)                    │
│  Vanilla JS queries/aggregates (dashboard)                  │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────┴────────────────────────────────────────────┐
│                      DATA LAYER                              │
│  HTML Files = Graph Nodes                                   │
│  <a href> = Graph Edges                                     │
│  data-* attributes = Node Properties                        │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────┴────────────────────────────────────────────┐
│                   PROCESSING LAYER                           │
│  Python + justhtml = Parse/Update                           │
│  Pydantic = Schema/Validation                               │
│  JSON = Interchange Format (optional)                       │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────┴────────────────────────────────────────────┐
│                   OPTIONAL: INDEX LAYER                      │
│  SQLite = Full-text search, complex queries                 │
│  Sync from HTML files for performance                       │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
htmlgraph/
├── README.md                    # "HTML is All You Need" manifesto
├── LICENSE                      # MIT
├── pyproject.toml              # Python package config
├── package.json                # JS package config (optional)
│
├── src/
│   ├── python/
│   │   └── htmlgraph/
│   │       ├── __init__.py
│   │       ├── parser.py       # justhtml wrapper
│   │       ├── models.py       # Pydantic schemas
│   │       ├── graph.py        # Graph operations
│   │       ├── converter.py    # HTML ↔ Pydantic converters
│   │       ├── agents.py       # Agent interface
│   │       └── index.py        # Optional SQLite indexer
│   │
│   └── js/
│       ├── htmlgraph.js        # Vanilla JS library
│       ├── htmlgraph.min.js    # Minified version
│       └── types.d.ts          # TypeScript definitions
│
├── dashboard/
│   ├── index.html              # Demo dashboard
│   ├── styles.css              # Dashboard styles
│   └── app.js                  # Dashboard logic
│
├── examples/
│   ├── todo-list/              # Simple example
│   │   ├── index.html
│   │   ├── task-001.html
│   │   └── task-002.html
│   │
│   ├── agent-coordination/     # Ijoka use case
│   │   ├── features/
│   │   │   ├── manifest.json
│   │   │   ├── feature-001-auth.html
│   │   │   └── feature-002-db.html
│   │   ├── sessions/
│   │   │   └── session-abc-123.html
│   │   └── dashboard.html
│   │
│   └── knowledge-base/         # Documentation system
│       ├── index.html
│       └── notes/
│
├── docs/
│   ├── philosophy.md           # Why HTML?
│   ├── comparison.md           # vs Neo4j, vs JSON, etc.
│   ├── quickstart.md           # Getting started guide
│   ├── cookbook.md             # Common recipes
│   ├── api-reference.md        # API documentation
│   └── architecture.md         # Technical deep-dive
│
└── tests/
    ├── python/
    │   ├── test_parser.py
    │   ├── test_graph.py
    │   └── test_agents.py
    └── js/
        └── test_htmlgraph.js
```

## HTML File Format Specification

### Node Structure
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feature: User Authentication</title>
    <link rel="stylesheet" href="../styles.css">
</head>
<body>
    <article id="feature-001" 
             data-type="feature"
             data-status="in-progress"
             data-priority="high"
             data-created="2024-12-16T10:30:00Z"
             data-updated="2024-12-16T14:22:00Z"
             data-agent-assigned="claude">
        
        <header>
            <h1>User Authentication</h1>
            <div class="metadata">
                <span class="badge status-in-progress">In Progress</span>
                <span class="badge priority-high">High Priority</span>
            </div>
        </header>
        
        <!-- Graph Edges -->
        <nav data-graph-edges>
            <section data-edge-type="blocks">
                <h3>⚠️ Blocked By:</h3>
                <ul>
                    <li>
                        <a href="feature-005-database.html" 
                           data-relationship="blocks"
                           data-since="2024-12-10">Database Schema</a>
                    </li>
                </ul>
            </section>
            
            <section data-edge-type="related">
                <h3>🔗 Related:</h3>
                <ul>
                    <li><a href="feature-012-sessions.html">Session Management</a></li>
                    <li><a href="feature-034-oauth.html">OAuth Provider</a></li>
                </ul>
            </section>
            
            <section data-edge-type="implemented-in">
                <h3>📝 Sessions:</h3>
                <ul>
                    <li><a href="../sessions/session-abc-123.html">Session ABC-123</a></li>
                </ul>
            </section>
        </nav>
        
        <!-- Node Properties -->
        <section data-properties>
            <h3>Properties</h3>
            <dl>
                <dt>Estimated Effort</dt>
                <dd data-key="effort" data-value="8" data-unit="hours">8 hours</dd>
                
                <dt>Completion</dt>
                <dd data-key="completion" data-value="40" data-unit="percent">40%</dd>
                
                <dt>Owner</dt>
                <dd data-key="owner">Claude</dd>
            </dl>
        </section>
        
        <!-- Implementation Steps -->
        <section data-steps>
            <h3>Implementation Steps</h3>
            <ol>
                <li data-completed="true" data-agent="claude">
                    ✅ Create auth route
                </li>
                <li data-completed="true" data-agent="claude">
                    ✅ Set up middleware
                </li>
                <li data-completed="false">
                    ⏳ Implement OAuth flow
                </li>
                <li data-completed="false">
                    ⏳ Add session management
                </li>
                <li data-completed="false">
                    ⏳ Create user profile endpoint
                </li>
            </ol>
        </section>
        
        <!-- Content -->
        <section data-content>
            <h3>Description</h3>
            <p>Implement user authentication system with OAuth 2.0 support.</p>
            
            <h4>Requirements:</h4>
            <ul>
                <li>Support Google and GitHub OAuth</li>
                <li>JWT-based session management</li>
                <li>Refresh token rotation</li>
            </ul>
        </section>
        
        <!-- Activity Log -->
        <section data-activity-log>
            <h3>Activity Log</h3>
            <ol reversed>
                <li data-timestamp="2024-12-16T14:22:00Z" data-agent="claude">
                    Completed middleware setup
                </li>
                <li data-timestamp="2024-12-16T10:30:00Z" data-agent="claude">
                    Started implementation
                </li>
            </ol>
        </section>
    </article>
</body>
</html>
```

### Key Conventions

1. **Node ID**: Always use `id` attribute on the root `<article>` element
2. **Node Type**: Use `data-type` attribute (e.g., "feature", "task", "session", "note")
3. **Status**: Use `data-status` attribute with consistent values
4. **Timestamps**: ISO 8601 format in `data-created`, `data-updated`, etc.
5. **Edges**: Links inside `<nav data-graph-edges>` are graph edges
6. **Properties**: Use `data-*` attributes for queryable properties
7. **Relationships**: Use `data-relationship` on `<a>` tags to specify edge type

## Python API Design

### Core Classes

```python
from htmlgraph import HtmlGraph, Node, Edge

# Initialize graph
graph = HtmlGraph('features/')

# Create a node
node = Node(
    id='feature-001',
    title='User Authentication',
    type='feature',
    status='in-progress',
    priority='high',
    properties={
        'effort': 8,
        'completion': 40
    },
    edges={
        'blocks': [],
        'blocked_by': ['feature-005'],
        'related': ['feature-012', 'feature-034']
    }
)

# Add to graph (creates HTML file)
graph.add(node)

# Query with CSS selectors
blocked = graph.query("[data-status='blocked'][data-priority='high']")

# Graph traversal
path = graph.shortest_path('feature-001', 'feature-045')
dependencies = graph.transitive_deps('feature-001')
bottlenecks = graph.find_bottlenecks()

# Update a node
node.status = 'done'
graph.update(node)

# Agent-friendly representation
context = node.to_context()
# Returns lightweight string for LLM context
```

### Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class Step(BaseModel):
    description: str
    completed: bool = False
    agent: Optional[str] = None
    timestamp: Optional[datetime] = None

class Node(BaseModel):
    id: str
    title: str
    type: str = 'node'
    status: str = 'todo'
    priority: str = 'medium'
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    
    properties: dict = Field(default_factory=dict)
    edges: dict[str, list[str]] = Field(default_factory=dict)
    steps: list[Step] = Field(default_factory=list)
    
    def to_html(self) -> str:
        """Convert to HTML file content"""
        pass
    
    def to_context(self) -> str:
        """Lightweight representation for AI agents"""
        pass
    
    @classmethod
    def from_html(cls, filepath: str) -> 'Node':
        """Parse HTML file into Node"""
        pass
```

## JavaScript API Design

```javascript
// Load library
import HtmlGraph from './htmlgraph.js';
// or <script src="htmlgraph.js"></script>

// Initialize
const graph = new HtmlGraph();

// Load from directory
await graph.loadFrom('features/');

// Query with CSS selectors
const blocked = graph.query('[data-status="blocked"]');
const highPriority = graph.query('[data-priority="high"]');

// Graph algorithms
const path = graph.findPath('feature-001', 'feature-045');
const dependencies = graph.getDependencies('feature-001');
const bottlenecks = graph.findBottlenecks();

// Get node details
const node = graph.getNode('feature-001');
console.log(node.title, node.status, node.edges);

// Render dashboard
graph.renderDashboard('#app', {
    showStats: true,
    showGraph: true,
    showTimeline: true,
    layout: 'force-directed'
});

// Watch for changes (in Electron/Tauri apps)
graph.watch('features/', (changes) => {
    console.log('Graph updated:', changes);
    graph.refresh();
});

// Export
const json = graph.toJSON();
const svg = graph.toSVG();
```

## Agent Interface

Agents interact through a simplified API that provides token-efficient context:

```python
from htmlgraph.agents import AgentInterface

agent = AgentInterface('features/')

# Get next available task
task = agent.get_next_task(
    agent_id='claude',
    filters={'priority': 'high', 'status': 'todo'}
)

# Start working on it
agent.claim_task(task.id, agent_id='claude')

# Get lightweight context for LLM
context = agent.get_context(task.id)
"""
# feature-001: User Authentication
Status: in-progress | Priority: high
Assigned: claude
Progress: 2/5 steps
⚠️  Blocked by: feature-005 (Database Schema)

Next steps:
  - Implement OAuth flow
  - Add session management
  - Create user profile endpoint
"""

# Update progress
agent.complete_step(task.id, step_index=2, agent_id='claude')

# Mark complete
agent.complete_task(task.id, agent_id='claude')
```

## Use Cases

### 1. Agent Coordination (Ijoka)
```
features/
├── feature-001-auth.html
├── feature-002-database.html
└── feature-003-api.html

Agents read HTML files, pick tasks, update status, hyperlink dependencies
Dashboard shows real-time progress with vanilla JS
```

### 2. Personal Knowledge Base
```
notes/
├── index.html              # Dashboard with search
├── 2024-12-16-idea.html    # Daily notes
├── projects/
│   └── htmlgraph.html      # Project notes with links
└── research/
    └── ai-agents.html      # Research notes
```

### 3. Documentation System
```
docs/
├── index.html              # TOC with search
├── getting-started.html    # Links to guides
├── api/
│   ├── overview.html
│   └── reference.html      # Links to examples
└── examples/
```

### 4. Task Management
```
tasks/
├── dashboard.html          # Kanban board (vanilla JS)
├── todo/
│   └── task-001.html
├── in-progress/
│   └── task-002.html       # Links to dependencies
└── done/
```

## Comparison to Alternatives

### vs Neo4j
| Feature | Neo4j | HtmlGraph |
|---------|-------|-----------|
| Setup | Docker, JVM, learn Cypher | Zero dependencies |
| Human readable | ❌ Neo4j Browser required | ✅ Any web browser |
| Version control | ❌ Binary dumps | ✅ Git diff works |
| Query language | Cypher (learn it) | CSS selectors (know it) |
| Cost | $$$ Enterprise license | Free, MIT license |

### vs JSON/YAML
| Feature | JSON | HtmlGraph |
|---------|------|-----------|
| Human readable | 🟡 Text editor | ✅ Browser with styling |
| Graph structure | ❌ Manual references | ✅ Native hyperlinks |
| Query | ❌ jq or custom | ✅ CSS selectors |
| Presentation | ❌ Needs separate UI | ✅ Built-in rendering |

### vs Custom Agent Protocols
| Feature | LangGraph | HtmlGraph |
|---------|-----------|-----------|
| Learning curve | High (new abstractions) | Low (web standards) |
| Portability | Python/JS specific | Any language |
| Debugging | Complex state machines | View source in browser |
| Standards-based | ❌ Proprietary | ✅ W3C standards |

## Implementation Phases

### Phase 1: Core Library (Week 1)
- [ ] Python package structure
- [ ] HTML parser using justhtml
- [ ] Pydantic models for Node/Edge
- [ ] Basic graph operations (add, query, traverse)
- [ ] HTML ↔ Pydantic converters
- [ ] Unit tests

### Phase 2: JavaScript Library (Week 1)
- [ ] Vanilla JS implementation
- [ ] DOMParser-based HTML loading
- [ ] CSS selector queries
- [ ] Graph algorithms (BFS, DFS, shortest path)
- [ ] Basic dashboard rendering
- [ ] Unit tests

### Phase 3: Examples (Week 2)
- [ ] Todo list example
- [ ] Agent coordination example (Ijoka migration)
- [ ] Knowledge base example
- [ ] Documentation site

### Phase 4: Documentation (Week 2)
- [ ] README.md with manifesto
- [ ] Philosophy.md - Why HTML?
- [ ] Comparison.md - vs alternatives
- [ ] Quickstart guide
- [ ] API reference
- [ ] Cookbook with recipes

### Phase 5: Polish (Week 3)
- [ ] Dashboard improvements
- [ ] Performance optimization
- [ ] Optional SQLite indexer
- [ ] TypeScript definitions
- [ ] CI/CD pipeline

### Phase 6: Launch (Week 3)
- [ ] GitHub repo public
- [ ] PyPI package
- [ ] npm package (optional)
- [ ] Blog post
- [ ] Social media (HN, Reddit, Twitter)
- [ ] Documentation site

---

## Release & Publishing Workflow

### Version Numbering

HtmlGraph follows [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 0.3.0)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

**Version Files to Update:**
1. `pyproject.toml` - Package version
2. `src/python/htmlgraph/__init__.py` - `__version__` variable
3. `packages/claude-plugin/.claude-plugin/plugin.json` - Claude plugin version
4. `packages/gemini-extension/gemini-extension.json` - Gemini extension version

### Publishing Checklist

**Pre-Release:**
- [ ] All tests pass: `uv run pytest`
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if exists)
- [ ] Version bumped in all files
- [ ] Changes committed to git
- [ ] Create git tag: `git tag v0.3.0`

**Build & Publish:**
```bash
# 1. Update versions (example for 0.3.0)
# Edit: pyproject.toml, __init__.py, plugin.json, gemini-extension.json

# 2. Commit version bump
git add pyproject.toml src/python/htmlgraph/__init__.py \
  packages/claude-plugin/.claude-plugin/plugin.json \
  packages/gemini-extension/gemini-extension.json
git commit -m "chore: bump version to 0.3.0"

# 3. Create git tag
git tag v0.3.0
git push origin main --tags

# 4. Build distributions
uv build
# Creates: dist/htmlgraph-0.3.0-py3-none-any.whl
#          dist/htmlgraph-0.3.0.tar.gz

# 5. Publish to PyPI
source .env  # Load PyPI_API_TOKEN
uv publish dist/htmlgraph-0.3.0* --token "$PyPI_API_TOKEN"

# Alternative: Set token as environment variable
export UV_PUBLISH_TOKEN="pypi-YOUR_TOKEN_HERE"
uv publish dist/htmlgraph-0.3.0*

# 6. Verify publication
open https://pypi.org/project/htmlgraph/
```

### PyPI Credentials Setup

**Option 1: API Token (Recommended)**
1. Create token at: https://pypi.org/manage/account/token/
2. Add to `.env` file:
   ```bash
   PyPI_API_TOKEN=pypi-YOUR_TOKEN_HERE
   ```
3. Use with: `source .env && uv publish dist/* --token "$PyPI_API_TOKEN"`

**Option 2: Environment Variable**
```bash
export UV_PUBLISH_TOKEN="pypi-YOUR_TOKEN_HERE"
uv publish dist/*
```

**Option 3: Command-line Arguments**
```bash
uv publish dist/* --username YOUR_USERNAME --password YOUR_PASSWORD
```

### Post-Release

**Update Claude Plugin:**
```bash
# Users update with:
claude plugin update htmlgraph

# Or fresh install:
claude plugin install htmlgraph@0.3.0
```

**Update Gemini Extension:**
```bash
# Distribution mechanism TBD
# Users may need to manually update or use extension marketplace
```

**Verify Installation:**
```bash
# Test PyPI package
pip install htmlgraph==0.3.0
python -c "import htmlgraph; print(htmlgraph.__version__)"

# Check PyPI page
curl -s https://pypi.org/pypi/htmlgraph/json | \
  python -c "import sys, json; print(json.load(sys.stdin)['info']['version'])"
```

### Common Release Commands

**Full Release Workflow:**
```bash
#!/bin/bash
# release.sh - Complete release workflow

VERSION="0.3.0"

# Update versions
sed -i '' "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml
sed -i '' "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" src/python/htmlgraph/__init__.py
sed -i '' "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" packages/claude-plugin/.claude-plugin/plugin.json
sed -i '' "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" packages/gemini-extension/gemini-extension.json

# Commit and tag
git add pyproject.toml src/python/htmlgraph/__init__.py \
  packages/claude-plugin/.claude-plugin/plugin.json \
  packages/gemini-extension/gemini-extension.json
git commit -m "chore: bump version to $VERSION"
git tag "v$VERSION"
git push origin main --tags

# Build and publish
uv build
source .env
uv publish dist/htmlgraph-$VERSION* --token "$PyPI_API_TOKEN"

echo "✅ Published htmlgraph $VERSION to PyPI"
echo "📦 https://pypi.org/project/htmlgraph/$VERSION/"
```

### Rollback / Unpublish

**⚠️ WARNING: PyPI does NOT allow unpublishing or replacing versions.**

Once published, a version is permanent. If you need to fix an issue:

1. **Patch Release:** Bump to next patch version (e.g., 0.3.0 → 0.3.1)
2. **Yank Release:** Mark as unavailable (doesn't delete):
   ```bash
   # Use twine to yank (uv doesn't support this yet)
   pip install twine
   twine yank htmlgraph 0.3.0 -r pypi
   ```
3. **Publish Fix:** Release corrected version

### Version History

Track major releases and their features:

- **0.3.0** (2025-12-22) - TrackBuilder fluent API, multi-pattern glob support
- **0.2.2** (2025-12-21) - Enhanced session tracking, drift detection
- **0.2.0** (2025-12-21) - Initial public release with SDK
- **0.1.x** - Development versions

---

## Key Design Decisions

### 1. Pure HTML, No Templating
- **Decision**: HTML files are hand-editable, no templating engine
- **Rationale**: Simplicity, no build step, works everywhere
- **Trade-off**: More verbose than templates

### 2. justhtml for Python, DOMParser for JS
- **Decision**: Use native parsers, no external dependencies
- **Rationale**: Zero install friction, works offline
- **Trade-off**: Slightly less performant than lxml

### 3. CSS Selectors, Not Custom Query Language
- **Decision**: Use CSS selectors for queries
- **Rationale**: Everyone knows CSS, powerful enough
- **Trade-off**: Not as expressive as Cypher for complex graph queries

### 4. Optional SQLite Index
- **Decision**: SQLite index is optional for large graphs
- **Rationale**: Start simple, add complexity only when needed
- **Trade-off**: Manual sync required

### 5. Vanilla JS, No Frameworks
- **Decision**: Pure JavaScript, no React/Vue/etc
- **Rationale**: No build step, easier to understand
- **Trade-off**: More verbose code

## Success Metrics

### Technical
- [ ] Parse 1000 HTML nodes in <1 second (Python)
- [ ] Query with CSS selectors in <100ms (JS)
- [ ] Zero external dependencies
- [ ] 100% test coverage for core library
- [ ] Works in Python 3.10+, modern browsers

### Adoption
- [ ] 100 GitHub stars in first month
- [ ] 10 example implementations
- [ ] 5 blog posts/tutorials from others
- [ ] Used in at least one production system

### Community
- [ ] HN front page
- [ ] r/programming discussion
- [ ] Twitter thread with 1000+ likes
- [ ] 10+ contributors

## Open Questions

1. **Concurrency**: How to handle multiple agents writing to same file?
   - Option A: File locking with retry logic
   - Option B: Optimistic locking with ETags
   - Option C: Document that it's append-mostly pattern
   
2. **Scalability**: At what graph size does this break?
   - Need benchmarks with 100, 1K, 10K, 100K nodes
   - When to recommend SQLite index?

3. **Schema Evolution**: How to version HTML format?
   - Use `<meta name="htmlgraph-version" content="1.0">`?
   - Migration scripts?

4. **Security**: XSS concerns with user-generated HTML?
   - Sanitization library recommendations?
   - Best practices document?

## Related Work

- **Roam Research**: Graph-based note-taking
- **Obsidian**: Markdown files with backlinks
- **TiddlyWiki**: Single-file wiki with internal links
- **Jekyll**: Static site generator with graph structure
- **Foam**: VSCode + Markdown knowledge base

HtmlGraph differs by:
1. Explicit graph semantics (edges, properties)
2. AI agent-first design
3. CSS selector queries
4. No build step or server required

## License

MIT - Free for commercial and non-commercial use

## Contact

- GitHub: @Shakes-tzd
- Project: github.com/Shakes-tzd/htmlgraph
- Discussions: github.com/Shakes-tzd/htmlgraph/discussions

---

*"HTML is All You Need" - Building AI agent infrastructure on web standards since 2024*
