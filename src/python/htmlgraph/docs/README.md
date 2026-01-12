# HtmlGraph API Documentation

Complete developer documentation for HtmlGraph SDK, HTTP API, and orchestration patterns.

## Quick Navigation

### For First-Time Users
Start here for a quick introduction and working examples.

**→ [Integration Guide](INTEGRATION_GUIDE.md)** - 5-minute quick start
- Installation and setup
- Common patterns (5 minutes to first feature)
- Complete example applications
- Troubleshooting guide

### For SDK Developers
Complete reference for Python SDK with code examples for every method.

**→ [SDK API Reference](API_REFERENCE.md)** - Comprehensive Python API
- SDK initialization
- All collection methods (create, get, all, where, edit, delete)
- Builder pattern for fluent API
- Query builder for complex searches
- Analytics and dependency analysis
- System prompt management
- Task delegation
- Error handling patterns
- 800+ lines of examples

### For HTTP Integration
REST API documentation for external service integration.

**→ [HTTP API Reference](HTTP_API.md)** - REST endpoint documentation
- Server startup
- All endpoints (/api/features, /api/bugs, /api/tasks, etc.)
- Request/response formats with examples
- Query parameters and filtering
- Status codes and error responses
- Pagination
- Complete curl examples

### For Multi-Agent Workflows
Guide to spawning agents, delegating tasks, and coordinating work.

**→ [Orchestration Patterns](ORCHESTRATION_PATTERNS.md)** - Agent coordination guide
- Agent spawning (Claude, Gemini, Codex, Copilot)
- Task delegation and tracking
- Model selection strategy
- Cost optimization
- Advanced patterns (chain-of-thought, feedback loops, consensus)
- Error recovery and fallback patterns

---

## Documentation Overview

| Document | Purpose | Audience | Time |
|----------|---------|----------|------|
| [Integration Guide](INTEGRATION_GUIDE.md) | Quick start and common patterns | All developers | 5 min |
| [SDK API Reference](API_REFERENCE.md) | Complete Python SDK documentation | Python developers | 30 min |
| [HTTP API Reference](HTTP_API.md) | REST endpoint reference | Integration engineers | 20 min |
| [Orchestration Patterns](ORCHESTRATION_PATTERNS.md) | Multi-agent workflows | Advanced users | 30 min |

**Total Documentation:** ~3,000 lines of comprehensive guides with 150+ code examples

---

## Key Features Documented

### SDK Features
- Auto-discovery of .htmlgraph directory
- Fluent builder interface for all work items
- Collections: Features, Bugs, Spikes, Chores, Epics, Phases, Sessions, Tracks
- Query builder for complex searches
- Analytics: Work distribution, bottleneck analysis, parallelizable work
- Dependency analysis: Blocking relationships, impact analysis
- Task delegation and result tracking
- System prompt management
- Context analytics and efficiency scoring

### HTTP API
- REST endpoints for all work items
- Advanced query API
- Agent statistics and analytics endpoints
- Task delegation tracking
- Status endpoint with collection counts

### Orchestration
- Agent spawning: Claude, Gemini, Codex, Copilot
- Task delegation with result tracking
- Model selection based on task type and complexity
- Cost optimization strategies
- Parallel task coordination
- Error recovery and fallback patterns
- Advanced patterns: chain-of-thought, feedback loops, multi-agent consensus

---

## Common Tasks

### Create Work Items

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Create feature with builder
feature = sdk.features.create("User Auth") \
    .set_priority("high") \
    .add_steps(["Design", "Implement", "Test"]) \
    .save()

# Create bug
bug = sdk.bugs.create("Login bug").save()

# Create spike
spike = sdk.spikes.create("Investigate caching").save()
```

See: [Integration Guide - Creating Work Items](INTEGRATION_GUIDE.md#creating-work-items)

---

### Query and Filter

```python
# Get all features
all_features = sdk.features.all()

# Filter by status and priority
high_priority = sdk.features.where(
    status="todo",
    priority="high"
)

# Complex query
results = graph.query_builder() \
    .where("status", "todo") \
    .and_("priority").in_(["high", "critical"]) \
    .execute()
```

See: [SDK API Reference - Collections](API_REFERENCE.md#collections)

---

### Analytics and Insights

```python
# Work distribution
distribution = sdk.analytics.get_work_type_distribution()

# Find bottlenecks
bottlenecks = sdk.dep_analytics.find_bottlenecks(top_n=5)

# Get parallelizable work
parallel = sdk.dep_analytics.get_parallel_work(max_agents=3)
```

See: [SDK API Reference - Analytics](API_REFERENCE.md#analytics)

---

### Delegate Tasks

```python
from htmlgraph import delegate_with_id, parallel_delegate

# Single task
task_id = delegate_with_id(
    prompt="Implement feature",
    agent="coder",
    task_id="task-001"
)

# Multiple parallel tasks
results = parallel_delegate([
    {"prompt": "Task 1", "agent": "coder", "task_id": "t1"},
    {"prompt": "Task 2", "agent": "tester", "task_id": "t2"}
])
```

See: [Orchestration Patterns - Task Delegation](ORCHESTRATION_PATTERNS.md#task-delegation)

---

### Spawn Agents

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# Spawn Claude
result = spawner.spawn_claude(
    prompt="Write authentication code",
    approval="auto"
)

# Spawn Gemini (model=None uses latest models including Gemini 3 preview)
result = spawner.spawn_gemini(
    prompt="Analyze performance"
)

# Spawn Codex
result = spawner.spawn_codex(
    prompt="Generate API",
    sandbox="workspace-write"
)
```

See: [Orchestration Patterns - Agent Selection](ORCHESTRATION_PATTERNS.md#agent-selection)

---

### Start HTTP Server

```bash
# CLI
htmlgraph serve --port 8080

# Python
from htmlgraph import serve
serve(port=8080, directory=".htmlgraph")
```

Then access API:
```bash
curl http://localhost:8080/api/status
curl http://localhost:8080/api/features
```

See: [HTTP API Reference](HTTP_API.md)

---

## Error Handling

HtmlGraph uses consistent error handling patterns:

| Operation | Error Behavior | Example |
|-----------|----------------|---------|
| Lookup (`get`) | Returns `None` | `feature = sdk.features.get("id")` |
| Query (`where`, `all`) | Returns `[]` | `items = sdk.features.where(...)` |
| Edit | Raises `NodeNotFoundError` | `with sdk.features.edit("id")` |
| Create | Raises `ValidationError` | `sdk.features.create(title)` |
| Batch | Returns results dict | `sdk.features.mark_done([ids])` |

See: [SDK API Reference - Error Handling](API_REFERENCE.md#error-handling)

---

## Installation

### Quick Install

```bash
pip install htmlgraph
```

### With uv (Recommended)

```bash
uv pip install htmlgraph
```

### Development

```bash
git clone https://github.com/anthropics/htmlgraph.git
cd htmlgraph
uv pip install -e .
```

---

## Project Structure

```
.htmlgraph/
├── features/          # Feature work items
├── bugs/              # Bug reports
├── spikes/            # Investigation spikes
├── chores/            # Maintenance tasks
├── epics/             # Large work bodies
├── phases/            # Project phases
├── sessions/          # Agent sessions
├── tracks/            # Work tracks
├── task-delegations/  # Delegated task tracking
├── patterns/          # Learned patterns
├── insights/          # Session insights
└── metrics/           # Aggregated metrics
```

---

## API Overview

### SDK Collections

```python
sdk.features        # Feature work items
sdk.bugs            # Bug reports
sdk.spikes          # Investigation spikes
sdk.chores          # Maintenance tasks
sdk.epics           # Large work bodies
sdk.phases          # Project phases
sdk.sessions        # Agent sessions
sdk.tracks          # Work tracks
sdk.todos           # Persistent task tracking
sdk.patterns        # Learned patterns
sdk.insights        # Session insights
sdk.metrics         # Aggregated metrics
sdk.task_delegations  # Task delegation tracking
sdk.agents          # Agent information
```

### HTTP Endpoints

```
GET    /api/status               - Server status
GET    /api/features             - List features
POST   /api/features             - Create feature
GET    /api/features/{id}        - Get feature
PUT    /api/features/{id}        - Update feature
DELETE /api/features/{id}        - Delete feature

GET    /api/bugs                 - List bugs (same pattern as features)
GET    /api/spikes               - List spikes
GET    /api/tasks                - List delegations
GET    /api/analytics/*          - Analytics endpoints
GET    /api/query                - Advanced query
```

---

## Version Information

- **Current Version:** 0.24.1
- **Documentation Updated:** 2025-01-06
- **Tested with:** Python 3.8+
- **Dependencies:** Zero (standard library only)

---

## Common Patterns

### Pattern 1: Create and Update

```python
feature = sdk.features.create("My Feature") \
    .set_priority("high") \
    .add_steps(["Step 1", "Step 2"]) \
    .save()

with sdk.features.edit(feature.id) as f:
    f.status = "done"
```

### Pattern 2: Query and Analyze

```python
todos = sdk.features.where(status="todo")
bottlenecks = sdk.dep_analytics.find_bottlenecks()
distribution = sdk.analytics.get_work_type_distribution()
```

### Pattern 3: Delegate Work

```python
task_id = delegate_with_id(
    prompt="Your task",
    agent="coder",
    task_id="task-001"
)

# Check results later
results = get_results_by_task_id("task-001")
```

### Pattern 4: Batch Operations

```python
# Create multiple
items = [sdk.features.create(title).save() for title in titles]

# Update multiple
sdk.features.batch_update({
    "feat-1": {"status": "done"},
    "feat-2": {"priority": "high"}
})

# Mark multiple done
sdk.features.mark_done([id1, id2, id3])
```

---

## Troubleshooting

### SDK Issues

**"Agent identifier is required"**
```python
# Fix: Always provide agent
sdk = SDK(agent="claude")  # ✓ Correct
```

**".htmlgraph directory not found"**
```python
# Fix: Create directory structure
from pathlib import Path
Path(".htmlgraph/features").mkdir(parents=True, exist_ok=True)
```

**"NodeNotFoundError"**
```python
# Fix: Check if exists or handle exception
try:
    with sdk.features.edit("id") as f:
        f.status = "done"
except NodeNotFoundError:
    print("Not found")
```

See: [Integration Guide - Troubleshooting](INTEGRATION_GUIDE.md#troubleshooting)

---

### HTTP API Issues

**"Connection refused"**
```bash
# Start server
htmlgraph serve --port 8080

# Verify it's running
curl http://localhost:8080/api/status
```

**"404 Not Found"**
```bash
# Verify item exists
curl http://localhost:8080/api/features

# Check specific item
curl http://localhost:8080/api/features/feat-abc123
```

See: [HTTP API Reference - Error Responses](HTTP_API.md#error-responses)

---

### Orchestration Issues

**"Agent spawn failed"**
```python
# Check API key
import os
if not os.getenv("ANTHROPIC_API_KEY"):
    print("Set ANTHROPIC_API_KEY")

# Use fallback
try:
    result = spawner.spawn_claude(prompt="...")
except Exception as e:
    print(f"Claude failed: {e}")
    result = spawner.spawn_gemini(prompt="...")
```

See: [Orchestration Patterns - Troubleshooting](ORCHESTRATION_PATTERNS.md#troubleshooting)

---

## Learning Paths

### Path 1: Quick Start (15 minutes)
1. Read [Integration Guide](INTEGRATION_GUIDE.md) intro
2. Run the quick start examples
3. Create first feature
4. Done!

### Path 2: Python Developer (1 hour)
1. [Integration Guide](INTEGRATION_GUIDE.md) - Patterns
2. [SDK API Reference](API_REFERENCE.md) - All methods
3. Try common patterns from your project
4. Explore analytics

### Path 3: Integration Engineer (1 hour)
1. [Integration Guide](INTEGRATION_GUIDE.md) - Basics
2. [HTTP API Reference](HTTP_API.md) - All endpoints
3. Set up HTTP server
4. Integrate with external services

### Path 4: Multi-Agent Workflows (2 hours)
1. [Integration Guide](INTEGRATION_GUIDE.md) - Task delegation
2. [Orchestration Patterns](ORCHESTRATION_PATTERNS.md) - All patterns
3. Explore agent spawning
4. Build multi-agent workflows

---

## Next Steps

1. **Get started** - Read [Integration Guide](INTEGRATION_GUIDE.md)
2. **Deep dive** - Explore [SDK API Reference](API_REFERENCE.md)
3. **Build APIs** - Check [HTTP API Reference](HTTP_API.md)
4. **Multi-agent** - Learn [Orchestration Patterns](ORCHESTRATION_PATTERNS.md)
5. **Get help** - Check troubleshooting sections
6. **See examples** - Look for `examples/` directory in repo

---

## Contributing

Found a documentation issue? Have a great example? Contribute!

- Report issues on GitHub
- Submit documentation PRs
- Share your patterns

---

## License

HtmlGraph documentation is part of the HtmlGraph project.
See LICENSE file in repository for details.

---

**Version:** 0.24.1 | **Last Updated:** 2025-01-06 | **Maintainer:** HtmlGraph Team
