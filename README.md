# HtmlGraph

**"HTML is All You Need"**

A lightweight graph database framework built entirely on web standards. Use HTML files as nodes, hyperlinks as edges, and CSS selectors as the query language.

## Why HtmlGraph?

Modern AI agent systems are drowning in complexity:
- Neo4j/Memgraph → Docker, JVM, learn Cypher
- Redis/PostgreSQL → More infrastructure
- Custom protocols → More learning curves

**HtmlGraph uses what you already know:**
- ✅ HTML files = Graph nodes
- ✅ `<a href>` = Graph edges
- ✅ CSS selectors = Query language
- ✅ Any browser = Visual interface
- ✅ Git = Version control (diffs work!)

## Installation

```bash
pip install htmlgraph
```

## Quick Start

### CLI (recommended for new projects)

```bash
htmlgraph init --install-hooks
htmlgraph serve
```

This bootstraps:
- `index.html` dashboard at the project root
- `.htmlgraph/events/` append-only JSONL event stream (Git-friendly)
- `.htmlgraph/index.sqlite` analytics cache (rebuildable; gitignored via `.gitignore`)
- versioned hook scripts under `.htmlgraph/hooks/` (installed into `.git/hooks/` with `--install-hooks`)

### Python

```python
from htmlgraph import HtmlGraph, Node, Edge, Step

# Initialize graph from directory
graph = HtmlGraph("features/")

# Create a node
node = Node(
    id="feature-001",
    title="User Authentication",
    type="feature",
    status="in-progress",
    priority="high",
    steps=[
        Step(description="Create auth routes"),
        Step(description="Add middleware"),
        Step(description="Implement OAuth"),
    ],
    edges={
        "blocked_by": [Edge(target_id="feature-002", title="Database Schema")]
    }
)

# Add to graph (creates HTML file)
graph.add(node)

# Query with CSS selectors
blocked = graph.query("[data-status='blocked']")
high_priority = graph.query("[data-priority='high']")

# Graph traversal
path = graph.shortest_path("feature-001", "feature-010")
deps = graph.transitive_deps("feature-001")
bottlenecks = graph.find_bottlenecks()

# Get lightweight context for AI agents (~50 tokens)
print(node.to_context())
# Output:
# # feature-001: User Authentication
# Status: in-progress | Priority: high
# Progress: 0/3 steps (0%)
# ⚠️  Blocked by: Database Schema
# Next: Create auth routes
```

### Agent Interface

```python
from htmlgraph.agents import AgentInterface

agent = AgentInterface("features/", agent_id="claude")

# Get next available task
task = agent.get_next_task(priority="high")

# Get lightweight context
context = agent.get_context(task.id)

# Update progress
agent.complete_step(task.id, step_index=0)

# Complete task
agent.complete_task(task.id)
```

### HTML File Format

HtmlGraph nodes are standard HTML files:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>User Authentication</title>
</head>
<body>
    <article id="feature-001"
             data-type="feature"
             data-status="in-progress"
             data-priority="high">

        <header>
            <h1>User Authentication</h1>
        </header>

        <nav data-graph-edges>
            <section data-edge-type="blocked_by">
                <h3>Blocked By:</h3>
                <ul>
                    <li><a href="feature-002.html">Database Schema</a></li>
                </ul>
            </section>
        </nav>

        <section data-steps>
            <h3>Steps</h3>
            <ol>
                <li data-completed="true">✅ Create auth routes</li>
                <li data-completed="false">⏳ Add middleware</li>
            </ol>
        </section>
    </article>
</body>
</html>
```

## Features

- **Zero dependencies** beyond `justhtml` and `pydantic`
- **CSS selector queries** - no new query language to learn
- **Version control friendly** - git diff works perfectly
- **Human readable** - open in any browser
- **AI agent optimized** - lightweight context generation
- **Graph algorithms** - BFS, shortest path, cycle detection, topological sort
- **Agent Handoff** - Context-preserving task transfers between agents
- **Capability Routing** - Automatic task assignment based on agent skills
- **Deployment Automation** - One-command releases with version management

## Comparison

| Feature | Neo4j | JSON | HtmlGraph |
|---------|-------|------|-----------|
| Setup | Docker + JVM | None | None |
| Query Language | Cypher | jq | CSS selectors |
| Human Readable | ❌ Browser needed | 🟡 Text editor | ✅ Any browser |
| Version Control | ❌ Binary | ✅ JSON diff | ✅ HTML diff |
| Visual UI | ❌ Separate tool | ❌ Build it | ✅ Built-in |
| Graph Native | ✅ | ❌ | ✅ |

## Use Cases

1. **AI Agent Coordination** - Task tracking, dependencies, progress
2. **Knowledge Bases** - Linked notes with visual navigation
3. **Documentation** - Interconnected docs with search
4. **Task Management** - Todo lists with dependencies

## Contributing

HtmlGraph is developed using HtmlGraph itself (dogfooding). This means:

- ✅ Every development action is replicable by users through the package
- ✅ We use the SDK, CLI, and plugins - not custom scripts
- ✅ Our development workflow IS the documentation

**See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for:**
- Dogfooding principles
- Replicable workflows
- Environment setup (PyPI tokens, etc.)
- Development best practices

**Quick start for contributors:**
```bash
# Clone and setup
git clone https://github.com/Shakes-tzd/htmlgraph
cd htmlgraph
uv sync

# Start tracking your work (dogfooding!)
uv run htmlgraph init --install-hooks
uv run htmlgraph serve  # View dashboard

# Use SDK for development
uv run python
>>> from htmlgraph import SDK
>>> sdk = SDK(agent="your-name")
>>> sdk.features.where(status="todo")
```

## License

MIT

## Links

- [GitHub](https://github.com/Shakes-tzd/htmlgraph)
- [Documentation](docs/) - SDK guide, workflows, development principles
- [Examples](examples/) - Real-world usage examples
- [PyPI](https://pypi.org/project/htmlgraph/)
