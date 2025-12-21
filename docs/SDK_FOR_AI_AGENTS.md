# HtmlGraph SDK for AI Agents

## Overview

The HtmlGraph SDK provides an AI-friendly interface for interacting with the HtmlGraph system. It's designed to minimize boilerplate, maximize readability, and make AI agents more productive.

## Key Improvements

| Feature | Old API | New SDK |
|---------|---------|---------|
| **Initialization** | `AgentInterface('.htmlgraph/features', agent_id='claude')` | `SDK(agent='claude')` ✅ Auto-discovers |
| **Create Feature** | 8 lines of `Node(...)` boilerplate | Fluent `.create().add_steps().save()` |
| **Edit Feature** | Manual `get()`, modify, `update()` | Context manager with auto-save |
| **Query** | Manual list comprehension | `sdk.features.where(status='todo')` |
| **Batch Ops** | Loop with manual updates | `sdk.features.mark_done([ids])` |
| **Agent ID** | Pass to every method | Set once at initialization |
| **Method Chaining** | ❌ No | ✅ Yes |
| **Auto-save** | ❌ Manual | ✅ Context manager |

## Quick Start

```python
from htmlgraph import SDK

# Initialize (auto-discovers .htmlgraph directory)
sdk = SDK(agent="claude")

# Create a feature with fluent interface
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
```

## Common Workflows

### 1. Get Orientation

```python
sdk = SDK(agent="claude")

# Get project summary
summary = sdk.summary(max_items=10)
print(summary)

# Check my current workload
workload = sdk.my_work()
print(f"In progress: {workload['in_progress']}")
print(f"Completed: {workload['completed']}")
```

### 2. Get Next Task

```python
# Get next high-priority task (auto-claims it)
task = sdk.next_task(priority="high", auto_claim=True)

if task:
    print(f"Working on: {task.title}")
```

### 3. Edit a Feature (Auto-Save)

```python
# Context manager auto-saves on exit
with sdk.features.edit("feature-001") as feature:
    feature.status = "in-progress"
    feature.steps[0].completed = True
    feature.steps[0].agent = "claude"
```

### 4. Query Features

```python
# Declarative queries
high_priority_todos = sdk.features.where(
    status="todo",
    priority="high"
)

# By track
auth_features = sdk.features.where(
    track="auth-track"
)

# By assignee
my_features = sdk.features.where(
    assigned_to="claude"
)
```

### 5. Batch Operations

```python
# Mark multiple features as done
sdk.features.mark_done([
    "feature-001",
    "feature-002",
    "feature-003"
])

# Assign multiple features to an agent
sdk.features.assign(
    ["feature-004", "feature-005"],
    agent="claude"
)
```

## Comparison: Old vs New

### Old API (Verbose)

```python
from htmlgraph import AgentInterface, Node, Step

# Initialization
agent = AgentInterface(".htmlgraph/features", agent_id="claude")

# Create feature
feature = Node(
    id="feature-001",
    title="User Auth",
    type="feature",
    status="todo",
    priority="high",
    content="<p>Implement OAuth</p>",
    steps=[
        Step(description="Create login"),
        Step(description="Add middleware"),
        Step(description="Write tests")
    ]
)
agent.graph.add(feature)

# Claim task
agent.claim_task("feature-001", agent_id="claude")

# Complete step
agent.complete_step("feature-001", 0, agent_id="claude")

# Get context
context = agent.get_context("feature-001")

# Query
high_priority = [
    n for n in agent.graph
    if n.type == "feature" and n.priority == "high" and n.status == "todo"
]
```

### New SDK (Fluent)

```python
from htmlgraph import SDK

# Initialization (auto-discovers .htmlgraph)
sdk = SDK(agent="claude")

# Create feature (fluent)
feature = sdk.features.create("User Auth") \
    .set_priority("high") \
    .set_description("Implement OAuth") \
    .add_steps([
        "Create login",
        "Add middleware",
        "Write tests"
    ]) \
    .save()

# Edit feature (auto-saves)
with sdk.features.edit(feature.id) as f:
    f.status = "in-progress"
    f.agent_assigned = "claude"
    f.steps[0].completed = True

# Get context
context = sdk.features.get(feature.id).to_context()

# Query (declarative)
high_priority = sdk.features.where(status="todo", priority="high")
```

## Real-World AI Agent Workflow

```python
from htmlgraph import SDK

def ai_agent_main():
    """Typical AI agent workflow."""
    sdk = SDK(agent="claude")

    # Step 1: Get oriented
    print("Project Summary:")
    print(sdk.summary())

    # Step 2: Check workload
    workload = sdk.my_work()
    if workload['in_progress'] > 5:
        print("Already at capacity!")
        return

    # Step 3: Get next task
    task = sdk.next_task(priority="high", auto_claim=True)
    if not task:
        print("No high-priority tasks available")
        return

    print(f"Working on: {task.title}")

    # Step 4: Work on task
    with sdk.features.edit(task.id) as feature:
        for i, step in enumerate(feature.steps):
            if not step.completed:
                # Do the work...
                step.completed = True
                step.agent = "claude"
                print(f"✓ Completed: {step.description}")
                break

        # Check if all steps done
        if all(s.completed for s in feature.steps):
            feature.status = "done"
            print("✓ Feature complete!")

if __name__ == "__main__":
    ai_agent_main()
```

## API Reference

### SDK Class

```python
class SDK:
    def __init__(
        self,
        directory: Path | str | None = None,  # Auto-discovered if None
        agent: str | None = None
    ):
        """Initialize SDK."""

    def reload(self) -> None:
        """Reload all data from disk."""

    def summary(self, max_items: int = 10) -> str:
        """Get project summary."""

    def my_work(self) -> dict[str, Any]:
        """Get current agent's workload."""

    def next_task(
        self,
        priority: str | None = None,
        auto_claim: bool = True
    ) -> Node | None:
        """Get next available task."""

    # Collection interfaces
    features: FeatureCollection
```

### FeatureCollection

```python
class FeatureCollection:
    def create(self, title: str, **kwargs) -> FeatureBuilder:
        """Create a new feature with fluent interface."""

    def get(self, feature_id: str) -> Node | None:
        """Get a feature by ID."""

    def edit(self, feature_id: str) -> ContextManager[Node]:
        """Context manager for editing (auto-saves)."""

    def where(
        self,
        status: str | None = None,
        priority: str | None = None,
        track: str | None = None,
        assigned_to: str | None = None
    ) -> list[Node]:
        """Query features."""

    def all(self) -> list[Node]:
        """Get all features."""

    def mark_done(self, feature_ids: list[str]) -> int:
        """Batch mark as done."""

    def assign(self, feature_ids: list[str], agent: str) -> int:
        """Batch assign to agent."""
```

### FeatureBuilder

```python
class FeatureBuilder:
    def set_priority(self, priority: Literal["low", "medium", "high", "critical"]) -> FeatureBuilder:
        """Set priority."""

    def set_status(self, status: str) -> FeatureBuilder:
        """Set status."""

    def add_step(self, description: str) -> FeatureBuilder:
        """Add a single step."""

    def add_steps(self, descriptions: list[str]) -> FeatureBuilder:
        """Add multiple steps."""

    def set_track(self, track_id: str) -> FeatureBuilder:
        """Link to a track."""

    def set_description(self, description: str) -> FeatureBuilder:
        """Set description."""

    def blocks(self, feature_id: str) -> FeatureBuilder:
        """Add blocking relationship."""

    def blocked_by(self, feature_id: str) -> FeatureBuilder:
        """Add blocked-by relationship."""

    def save(self) -> Node:
        """Save and return Node."""
```

## Design Principles

1. **Auto-Discovery** - Find `.htmlgraph` directory automatically
2. **Fluent Interface** - Method chaining for readability
3. **Context Managers** - Auto-save to prevent forgetting
4. **Batch Operations** - Operate on multiple items efficiently
5. **Minimal Boilerplate** - Less code = fewer errors
6. **Type Hints** - AI can infer types
7. **Rich Docstrings** - AI understands usage
8. **Sensible Defaults** - Works out of the box

## Why This Matters for AI Agents

### Before (Old API)
```python
# AI agent has to remember to:
# 1. Pass agent_id everywhere
# 2. Manually save after updates
# 3. Handle initialization boilerplate
# 4. Write list comprehensions for queries

agent = AgentInterface(".htmlgraph/features", agent_id="claude")
node = agent.graph.get("feat-001")
node.status = "done"
agent.graph.update(node)  # ❌ Easy to forget!
```

### After (New SDK)
```python
# AI agent just needs to:
# 1. Initialize once
# 2. Use fluent interface
# 3. Let context manager handle saving

sdk = SDK(agent="claude")
with sdk.features.edit("feat-001") as f:
    f.status = "done"  # ✅ Auto-saves!
```

## Migration Guide

### Existing Code Using AgentInterface

```python
# Old
from htmlgraph import AgentInterface
agent = AgentInterface(".htmlgraph/features", agent_id="claude")

# New
from htmlgraph import SDK
sdk = SDK(agent="claude")
# AgentInterface still available via sdk._agent_interface if needed
```

### Existing Code Using HtmlGraph Directly

```python
# Old
from htmlgraph import HtmlGraph
graph = HtmlGraph(".htmlgraph/features")

# New
from htmlgraph import SDK
sdk = SDK()
# HtmlGraph still available via sdk._graph if needed
```

## Next Steps

- Add `TrackCollection` for track operations
- Add `SessionCollection` for session operations
- Expand batch operations
- Add transaction support
- Add caching layer

## Examples

See `examples/sdk_demo.py` for a complete demonstration of the SDK.

```bash
uv run python examples/sdk_demo.py
```
