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

### Python (SDK - Recommended)

```python
from htmlgraph import SDK

# Initialize (auto-discovers .htmlgraph directory)
sdk = SDK(agent="claude")

# Create and configure a feature with fluent API
feature = sdk.features.create("User Authentication") \
    .set_priority("high") \
    .set_description("Implement OAuth 2.0 login") \
    .add_steps([
        "Create login endpoint",
        "Add JWT middleware",
        "Write integration tests"
    ]) \
    .save()

print(f"Created: {feature.id}")

# Work on features
with sdk.features.edit(feature.id) as f:
    f.status = "in-progress"
    f.agent_assigned = "claude"
    f.steps[0].completed = True

# Query features
high_priority_todos = sdk.features.where(status="todo", priority="high")
for feat in high_priority_todos:
    print(f"- {feat.id}: {feat.title}")

# Create and configure a track with TrackBuilder
track = sdk.tracks.builder() \
    .title("Q1 Security Initiative") \
    .priority("high") \
    .add_feature("feature-001") \
    .add_feature("feature-002") \
    .create()

print(f"Created track: {track.id}")
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
- **Unified Backend** - Operations layer shared by CLI and SDK for consistency

## Orchestrator Architecture: Flexible Multi-Agent Coordination

HtmlGraph implements an orchestrator pattern that coordinates multiple AI agents in parallel, preserving context efficiency while maintaining complete flexibility in model selection. Instead of rigid rules, the pattern uses **capability-first thinking** to choose the right tool (and model) for each task.

**Key Principles:**
- ✅ **Flexible model selection** - Any model can do any work; choose based on task fit and cost
- ✅ **Dynamic spawner composition** - Mix and match spawner types (Gemini, Copilot, Codex, Claude) within the same workflow
- ✅ **Cost optimization** - Use cheaper models for exploratory work, expensive models only for reasoning
- ✅ **Parallel execution** - Independent tasks run simultaneously, reducing total time

**Example: Parallel Exploration with Multiple Spawners**

```python
# All run in parallel - each uses the best tool for the job
Task(subagent_type="gemini-spawner",    # FREE exploration
     prompt="Find all authentication patterns in src/auth/")

Task(subagent_type="copilot-spawner",   # GitHub integration
     prompt="Check GitHub issues related to auth",
     allow_tools=["github(*)"])

Task(subagent_type="claude-spawner",    # Deep reasoning
     prompt="Analyze auth patterns for security issues")

# Orchestrator coordinates, subagents work in parallel
# Total time = slowest task (not sum of all)
# Cost = optimized (cheap exploration + expensive reasoning only)
```

**Spawner Types:**
- **Gemini Spawner** - FREE exploratory research, batch analysis (2M tokens/min)
- **Copilot Spawner** - GitHub-integrated workflows, git operations
- **Codex Spawner** - Code generation, coding completions
- **Claude Spawner** - Deep reasoning, analysis, strategic planning (any Claude model)

→ [Complete Orchestrator Architecture Guide](docs/orchestrator-architecture.md) - Detailed patterns, cost optimization, decision framework, and advanced examples

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

## System Prompt & Delegation Documentation

For Claude Code users and teams using HtmlGraph for AI agent coordination:

- **[System Prompt Quick Start](docs/SYSTEM_PROMPT_QUICK_START.md)** - Setup your system prompt in 5 minutes (start here!)
- **[System Prompt Architecture](docs/SYSTEM_PROMPT_ARCHITECTURE.md)** - Technical deep dive + troubleshooting
- **[Delegation Enforcement Admin Guide](docs/DELEGATION_ENFORCEMENT_ADMIN_GUIDE.md)** - Setup cost-optimal delegation for your team
- **[System Prompt Developer Guide](docs/SYSTEM_PROMPT_DEVELOPER_GUIDE.md)** - Extend with custom layers, hooks, and skills

## Links

- [GitHub](https://github.com/Shakes-tzd/htmlgraph)
- [API Reference](docs/API_REFERENCE.md) - Complete SDK API documentation
- [Documentation](docs/) - SDK guide, workflows, development principles
- [Examples](examples/) - Real-world usage examples
- [PyPI](https://pypi.org/project/htmlgraph/)
