# HtmlGraph - "HTML is All You Need"

---

## 🤖 For AI Agents

**→ See [AGENTS.md](./AGENTS.md) for complete AI agent documentation**

This file (CLAUDE.md) contains project vision, architecture, and roadmap.

For SDK usage, deployment instructions, and agent workflows, see:
- **[AGENTS.md](./AGENTS.md)** - Python SDK, API, CLI, deployment, best practices
- **[GEMINI.md](./GEMINI.md)** - Gemini-specific integration notes

---

## 🔄 DOGFOODING CONTEXT - CRITICAL

**THIS PROJECT USES HTMLGRAPH TO DEVELOP HTMLGRAPH.**

We are dogfooding our own tool. The `.htmlgraph/` directory in this repo tracks:
- ✅ **Features** - New capabilities we're building (e.g., strategic analytics, track planning)
- ✅ **Sessions** - Our development work (tracked automatically via hooks)
- ✅ **Tracks** - Multi-feature initiatives (e.g., "Planning Workflow")
- ✅ **Development progress** - What's done, in-progress, and planned

**What This Means for AI Agents:**

### 1. **Dual Purpose - Examples ARE Real Usage**

When you see workflows in this project:
- ✅ They're **real examples** of HtmlGraph usage
- ✅ They're **actual tracking** of HtmlGraph development
- ✅ Learn from them for YOUR projects

```python
# This IS real - we use this to track HtmlGraph development
sdk = SDK(agent="claude")
feature = sdk.features.create("Add deployment automation")  # Real feature!
```

### 2. **General vs Project-Specific**

**GENERAL WORKFLOWS** (package these for all users):
- ✅ Feature creation and tracking → SDK already provides this
- ✅ Track planning with TrackBuilder → SDK provides this
- ✅ Strategic analytics (recommend_next_work, find_bottlenecks) → SDK provides this
- ✅ Session management → Hooks provide this
- ⚠️ **Deployment automation** → Should package `deploy-all.sh` pattern
- ⚠️ **Memory file sync** → Should package `sync_memory_files.py` pattern

**PROJECT-SPECIFIC** (only for HtmlGraph development):
- ❌ Publishing to PyPI (specific to HtmlGraph package)
- ❌ The specific features in `.htmlgraph/features/` (our roadmap)
- ❌ Phase 1-6 implementation plan (our project structure)

### 3. **Workflows to Package for Users**

**TODO - Extract these into the package:**
1. **Deployment Script Pattern** - Generalize `deploy-all.sh` for any Python package
2. **Memory File Sync** - Include `sync_memory_files.py` in the package
3. **Project Initialization** - `htmlgraph init` should set up `.htmlgraph/`
4. **Pre-commit Hooks** - Package the git hooks for automatic tracking

**Current Status:**
- ✅ SDK provides feature/track/analytics workflows
- ⚠️ Deployment scripts are project-specific (need to generalize)
- ⚠️ Memory sync is project-specific (need to package)

### 4. **How to Read This Codebase**

When you see `.htmlgraph/` in this repo:
- **It's a live example** - This is real usage, not a demo
- **It's our roadmap** - Features here are what we're building
- **Learn from it** - Use these patterns in your projects

**Example:**
```bash
# In THIS repo
ls .htmlgraph/features/
# → feature-20251221-211348.html  # Real feature we're tracking
# → feat-5f0fca41.html            # Another real feature

# In YOUR project (after using HtmlGraph)
ls .htmlgraph/features/
# → Your features will look the same!
```

---

## 🧹 Code Hygiene - MANDATORY

**CRITICAL: Always fix ALL errors with every commit, regardless of when they were introduced.**

### Philosophy

Maintaining clean, error-free code is non-negotiable. Every commit should reduce technical debt, not accumulate it.

### Rules

1. **Fix All Errors Before Committing**
   - Run all linters (ruff, mypy) before every commit
   - Fix ALL errors, even pre-existing ones from previous sessions
   - Never commit with unresolved type errors, lint warnings, or test failures

2. **No "I'll Fix It Later" Mentality**
   - Errors compound over time
   - Pre-existing errors are YOUR responsibility when you touch related code
   - Clean as you go - leave code better than you found it

3. **Deployment Blockers**
   - The `deploy-all.sh` script blocks on:
     - Mypy type errors
     - Ruff lint errors
     - Test failures
   - This is intentional - maintain quality gates

4. **Why This Matters**
   - **Prevents Error Accumulation** - Small issues don't become large problems
   - **Better Code Hygiene** - Clean code is easier to maintain
   - **Faster Development** - No time wasted debugging old errors
   - **Professional Standards** - Production-grade code quality

### Workflow

```bash
# Before every commit:
1. uv run ruff check --fix
2. uv run ruff format
3. uv run mypy src/
4. uv run pytest

# Only commit when ALL checks pass
git commit -m "..."
```

**Remember: Fixing errors immediately is faster than letting them accumulate.**

---

## 🔍 Debugging Workflow - RESEARCH FIRST

**CRITICAL: HtmlGraph enforces a research-first debugging philosophy.**

### Core Principle

**NEVER implement solutions based on assumptions. ALWAYS research documentation first.**

This principle emerged from dogfooding HtmlGraph development. We repeatedly violated it by:
- ❌ Making multiple trial-and-error attempts before researching
- ❌ Implementing "fixes" based on guesses instead of documentation
- ❌ Not using available debugging tools and agents

**The correct approach:**
1. ✅ **Research** - Use claude-code-guide agent, read documentation
2. ✅ **Understand** - Identify root cause through evidence
3. ✅ **Implement** - Apply fix based on understanding
4. ✅ **Validate** - Test to confirm fix works
5. ✅ **Document** - Capture learning in HtmlGraph spike

### Debugging Agents (Plugin-Provided)

HtmlGraph plugin includes three specialized agents for systematic debugging:

#### 1. Researcher Agent
**Purpose**: Research documentation BEFORE implementing solutions

**Use when**:
- Encountering unfamiliar errors or behaviors
- Working with Claude Code hooks, plugins, or configuration
- Before implementing solutions based on assumptions
- When multiple attempted fixes have failed

**Workflow**:
```bash
# Activate researcher agent
# Use claude-code-guide for Claude-specific questions
# Document findings in HtmlGraph spike
```

**Key resources**:
- Claude Code docs: https://code.claude.com/docs
- GitHub issues: https://github.com/anthropics/claude-code/issues
- Hook documentation: https://code.claude.com/docs/en/hooks.md

#### 2. Debugger Agent
**Purpose**: Systematically analyze and resolve errors

**Use when**:
- Error messages appear but root cause is unclear
- Behavior doesn't match expectations
- Tests are failing
- Hooks or plugins aren't working as expected

**Built-in debug tools**:
```bash
claude --debug <command>        # Verbose output
/hooks                          # List all active hooks
/hooks PreToolUse              # Show specific hook type
/doctor                         # System diagnostics
claude --verbose               # More detailed logging
```

**Methodology**:
1. Gather evidence (logs, error messages, stack traces)
2. Reproduce consistently (exact steps, minimal case)
3. Isolate variables (test one change at a time)
4. Analyze context (what changed recently?)
5. Form hypothesis (root cause theory)
6. Test hypothesis (validate or refute)
7. Implement fix (minimal change to fix root cause)

#### 3. Test Runner Agent
**Purpose**: Automatically test changes, enforce quality gates

**Use when**:
- After implementing code changes
- Before marking features/tasks complete
- After fixing bugs
- Before committing code

**Test commands**:
```bash
# Run all tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check --fix
uv run ruff format

# Full quality gate (pre-commit)
uv run ruff check --fix && \
uv run ruff format && \
uv run mypy src/ && \
uv run pytest
```

### Debugging Workflow Pattern

**Example: Duplicate Hooks Issue**

**❌ What we did initially (wrong)**:
1. Removed .claude/hooks/hooks.json - Still broken
2. Cleared plugin cache - Still broken
3. Removed old plugin versions - Still broken
4. Removed marketplaces symlink - Still broken
5. Finally researched documentation
6. Found root cause: Hook merging behavior

**✅ What we should have done (correct)**:
1. Research Claude Code hook loading behavior first
2. Use claude-code-guide agent to understand hook merging
3. Identify that hooks from multiple sources MERGE, not replace
4. Check all hook sources (.claude/settings.json, plugin hooks)
5. Remove duplicates based on understanding
6. Verify fix works
7. Document learning in spike

### HtmlGraph Debug Commands

```bash
# Check orchestrator status
uv run htmlgraph orchestrator status

# List active features
uv run htmlgraph status

# View specific feature
uv run htmlgraph feature show <id>

# Check session state
uv run htmlgraph session list --active
```

### Integration with Orchestrator Mode

When orchestrator mode is enabled (strict), you'll receive reflections after direct tool execution:

```
ORCHESTRATOR REFLECTION: You executed code directly.

Ask yourself:
- Could this have been delegated to a subagent?
- Would parallel Task() calls have been faster?
- Is a work item tracking this effort?
```

This encourages delegation to specialized agents (researcher, debugger, test-runner) for systematic problem-solving.

### Documentation References

**For debugging agents**: See `packages/claude-plugin/agents/`
- `researcher.md` - Research-first methodology
- `debugger.md` - Systematic error analysis
- `test-runner.md` - Quality gates and testing

**For debugging workflows**: See `.htmlgraph/spikes/`
- Spikes document research findings and debugging processes
- Learn from past debugging sessions
- Avoid repeating the same mistakes

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

## Common Workflows & Scripts

### Quick Git Commit and Push

**IMPORTANT: Use `./scripts/git-commit-push.sh` to systematize the common git workflow.**

This script reduces 3 separate bash calls to 1:

```bash
# Instead of:
# git add -A
# git commit -m "message"
# git push origin main

# Use this:
./scripts/git-commit-push.sh "chore: update session tracking"

# With confirmation skip:
./scripts/git-commit-push.sh "fix: deployment issues" --no-confirm

# Preview changes:
./scripts/git-commit-push.sh "feat: new feature" --dry-run
```

**Features:**
- ✅ Shows files to be committed before proceeding
- ✅ Confirms action (unless `--no-confirm`)
- ✅ Stages all changes (`git add -A`)
- ✅ Commits with provided message
- ✅ Pushes to origin/main
- ✅ Supports `--dry-run` for preview

---

## Deployment & Release

### Using the Deployment Script (FLEXIBLE OPTIONS)

**CRITICAL: Use `./scripts/deploy-all.sh` for all deployment operations.**

**IMPORTANT PRE-DEPLOYMENT CHECKLIST:**
1. ✅ **MUST be in project root directory** - Script will fail if run from subdirectories like `dist/`
2. ~~✅ **Commit all changes first**~~ - **AUTOMATED!** Script auto-commits version changes in Step 0
3. ~~✅ **Verify version numbers**~~ - **AUTOMATED!** Script auto-updates all version numbers in Step 0
4. ✅ **Run tests** - `uv run pytest` must pass before deployment

**NEW STREAMLINED WORKFLOW (v0.9.4+):**
```bash
# 1. Run tests
uv run pytest

# 2. Deploy (one command, fully automated!)
./scripts/deploy-all.sh 0.9.4 --no-confirm

# That's it! The script now handles:
# ✅ Dashboard file sync (index.html ← dashboard.html)
# ✅ Version updates in all files (Step 0)
# ✅ Auto-commit of version changes
# ✅ Git push with tags
# ✅ Build, publish, install
# ✅ Plugin updates
# ✅ No interactive prompts with --no-confirm
```

**Session Tracking Files Excluded:**
```
.gitignore now excludes regenerable session tracking:
- .htmlgraph/sessions/*.jsonl
- .htmlgraph/events/*.jsonl
- .htmlgraph/parent-activity.json

This eliminates the multi-commit cycle problem.
```

**Quick Usage:**
```bash
# Full release (non-interactive, recommended)
./scripts/deploy-all.sh 0.9.4 --no-confirm

# Full release (with confirmations)
./scripts/deploy-all.sh 0.9.4

# Documentation changes only (commit + push)
./scripts/deploy-all.sh --docs-only

# Build package only (test builds)
./scripts/deploy-all.sh --build-only

# Skip PyPI publishing (build + install only)
./scripts/deploy-all.sh 0.9.4 --skip-pypi

# Preview what would happen (dry-run)
./scripts/deploy-all.sh --dry-run

# Show all options
./scripts/deploy-all.sh --help
```

**Available Flags:**
- `--no-confirm` - Skip all confirmation prompts (non-interactive mode) **[NEW]**
- `--docs-only` - Only commit and push to git (skip build/publish)
- `--build-only` - Only build package (skip git/publish/install)
- `--skip-pypi` - Skip PyPI publishing step
- `--skip-plugins` - Skip plugin update steps
- `--dry-run` - Show what would happen without executing

**What the Script Does (9 Steps):**
- **Pre-flight: Dashboard Sync** - Sync `src/python/htmlgraph/dashboard.html` → `index.html` **[NEW]**
- **Pre-flight: Code Quality** - Run linters (ruff, mypy) and tests
- **Pre-flight: Plugin Sync** - Verify packages/claude-plugin and .claude are synced
0. **Update & Commit Versions** - Auto-update version numbers in all files and commit
1. **Git Push** - Push commits and tags to origin/main
2. **Build Package** - Create wheel and source distributions
3. **Publish to PyPI** - Upload package to PyPI
4. **Local Install** - Install latest version locally
5. **Update Claude Plugin** - Run `claude plugin update htmlgraph`
6. **Update Gemini Extension** - Update version in gemini-extension.json
7. **Update Codex Skill** - Check for Codex and update if present
8. **Create GitHub Release** - Create release with distribution files

**See:** `scripts/README.md` for complete documentation

---

## Memory File Synchronization

**CRITICAL: Use `uv run htmlgraph sync-docs` to maintain documentation consistency.**

HtmlGraph uses a centralized documentation pattern:
- **AGENTS.md** - Single source of truth (SDK, API, CLI, workflows)
- **CLAUDE.md** - Platform-specific notes + references AGENTS.md
- **GEMINI.md** - Platform-specific notes + references AGENTS.md

**Quick Usage:**
```bash
# Check if files are synchronized
uv run htmlgraph sync-docs --check

# Generate platform-specific file
uv run htmlgraph sync-docs --generate gemini
uv run htmlgraph sync-docs --generate claude

# Synchronize all files (default)
uv run htmlgraph sync-docs
```

**Why This Matters:**
- ✅ Single source of truth in AGENTS.md
- ✅ Platform-specific notes in separate files
- ✅ Easy maintenance (update once, not 3+ times)
- ✅ Consistency across all platforms

**See:** `scripts/README.md` for complete documentation

---

## Dashboard File Synchronization

**AUTOMATIC: Dashboard sync happens automatically during deployment.**

HtmlGraph maintains two versions of the dashboard HTML file:
- **Source of Truth**: `src/python/htmlgraph/dashboard.html` (packaged with Python library)
- **Project Root**: `index.html` (for easy viewing in development)

**Automatic Sync Behavior:**
- ✅ **During Deployment**: `deploy-all.sh` automatically syncs dashboard files in pre-flight
- ✅ **Auto-Commit**: If changes detected, automatically commits with message "chore: sync index.html with dashboard.html"
- ✅ **Idempotent**: Safe to run multiple times, only commits when out of sync
- ✅ **Dry-Run Support**: `--dry-run` flag shows what would be synced without executing

**Manual Sync (if needed):**
```bash
# Sync manually (rare - deployment handles this)
cp src/python/htmlgraph/dashboard.html index.html

# Check if files are in sync
git diff --quiet index.html && echo "In sync" || echo "Out of sync"
```

**Why This Matters:**
- ✅ Ensures packaged dashboard matches development version
- ✅ Eliminates manual copy-paste errors
- ✅ Prevents deployment with stale dashboard
- ✅ Maintains consistency automatically

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
