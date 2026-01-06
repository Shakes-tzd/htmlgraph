# HtmlGraph Integration Guide

Quick start guide to integrate HtmlGraph into your project. Get up and running in 5 minutes.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Common Patterns](#common-patterns)
4. [Integration Patterns](#integration-patterns)
5. [Troubleshooting](#troubleshooting)

---

## Installation

### Via pip

```bash
pip install htmlgraph
```

### Via uv (Recommended)

```bash
uv pip install htmlgraph
```

### Development Installation

```bash
git clone https://github.com/anthropics/htmlgraph.git
cd htmlgraph
uv pip install -e .
```

### Verify Installation

```bash
python -c "from htmlgraph import SDK; print('Installation successful!')"
```

---

## Quick Start

### 5-Minute Setup

**Step 1: Initialize HtmlGraph**

```bash
# Create .htmlgraph directory
mkdir -p .htmlgraph/{features,bugs,spikes}
```

**Step 2: First Script**

```python
from htmlgraph import SDK

# Initialize SDK (auto-discovers .htmlgraph)
sdk = SDK(agent="claude")

# Create a feature
feature = sdk.features.create("User Authentication") \
    .set_priority("high") \
    .add_steps(["Design", "Implement", "Test"]) \
    .save()

print(f"Created feature: {feature.id}")

# Query features
features = sdk.features.all()
print(f"Total features: {len(features)}")

# Mark as done
sdk.features.mark_done([feature.id])
```

**Step 3: Start Server (Optional)**

```bash
htmlgraph serve --port 8080
```

Then visit: http://localhost:8080

---

## Common Patterns

### Creating Work Items

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Feature with full details
feature = sdk.features.create("User Authentication System") \
    .set_priority("high") \
    .set_status("todo") \
    .set_description("Implement JWT-based authentication") \
    .add_steps([
        "Design schema",
        "Implement API",
        "Add tests",
        "Deploy"
    ]) \
    .save()

# Bug report
bug = sdk.bugs.create("Login button not responsive") \
    .set_priority("high") \
    .set_description("Fix CSS media query for mobile") \
    .save()

# Investigation spike
spike = sdk.spikes.create("Investigate caching strategies") \
    .save()

# Maintenance chore
chore = sdk.chores.create("Update dependencies") \
    .save()
```

---

### Querying Work

```python
# Get single item
feature = sdk.features.get("feat-12345")

# Get all items
all_features = sdk.features.all()

# Filter by status
todos = sdk.features.where(status="todo")

# Multiple filters
high_priority_bugs = sdk.bugs.where(
    status="todo",
    priority="high"
)

# Complex queries
from htmlgraph import HtmlGraph, QueryBuilder

graph = HtmlGraph("features/")
results = graph.query_builder() \
    .where("status", "todo") \
    .and_("priority").in_(["high", "critical"]) \
    .execute()
```

---

### Updating Work

```python
# Update single item
with sdk.features.edit(feature.id) as f:
    f.status = "in-progress"
    f.priority = "critical"
    # Auto-saves on context exit

# Batch update
sdk.features.batch_update({
    feature.id: {"status": "done"},
    other_id: {"priority": "low"}
})

# Mark multiple as done
sdk.features.mark_done([feat1, feat2, feat3])
```

---

### Work Item Relationships

```python
# Create blocking relationships
feature_a = sdk.features.create("Feature A").save()
feature_b = sdk.features.create("Feature B") \
    .blocks(feature_a.id) \
    .save()

# Feature A is blocked by Feature B
feature_b = sdk.features.create("Feature B") \
    .blocked_by(feature_a.id) \
    .save()
```

---

### Analytics

```python
# Work distribution
distribution = sdk.analytics.get_work_type_distribution()
# Returns: {"feature": 25, "spike": 8, "bug": 12}

# Find bottlenecks
bottlenecks = sdk.dep_analytics.find_bottlenecks(top_n=5)
for item in bottlenecks:
    print(f"{item['title']} blocks {item['blocking_count']} items")

# Get parallelizable work
parallel = sdk.dep_analytics.get_parallel_work(max_agents=3)
for agent, tasks in parallel.items():
    print(f"{agent}: {len(tasks)} tasks")
```

---

## Integration Patterns

### Pattern 1: Project Initialization

Auto-initialize HtmlGraph in your project:

```python
# setup.py
from htmlgraph import SDK
from pathlib import Path

def initialize_htmlgraph():
    """Initialize HtmlGraph on project startup."""
    htmlgraph_dir = Path(".htmlgraph")

    if not htmlgraph_dir.exists():
        print("Initializing HtmlGraph...")
        (htmlgraph_dir / "features").mkdir(parents=True, exist_ok=True)
        (htmlgraph_dir / "bugs").mkdir(exist_ok=True)
        (htmlgraph_dir / "spikes").mkdir(exist_ok=True)
        print("HtmlGraph initialized!")

    return SDK(agent="system")

sdk = initialize_htmlgraph()
```

---

### Pattern 2: Context Manager for Sessions

```python
from htmlgraph import SDK
from contextlib import contextmanager

@contextmanager
def work_session(agent_name, feature_id):
    """Context manager for working on a feature."""
    sdk = SDK(agent=agent_name)

    feature = sdk.features.get(feature_id)
    if not feature:
        raise ValueError(f"Feature {feature_id} not found")

    # Start work
    with sdk.features.edit(feature_id) as f:
        f.status = "in-progress"
        yield f

        # Automatically save progress on exit
        f.status = "done"
        print(f"Completed: {f.title}")

# Usage
with work_session("claude", "feat-123") as feature:
    print(f"Working on: {feature.title}")
    # Your work here...
```

---

### Pattern 3: Logging & Auditing

```python
from htmlgraph import SDK
from datetime import datetime

sdk = SDK(agent="logger")

def log_action(action, item_id, details):
    """Log all actions to spikes for audit trail."""
    spike = sdk.spikes.create(f"{action}: {item_id}") \
        .set_description(f"""
Action: {action}
Item: {item_id}
Timestamp: {datetime.now().isoformat()}
Details: {details}
        """) \
        .save()

    return spike.id

# Usage
log_action("FEATURE_CREATED", "feat-123", "Created by deploy script")
log_action("BUG_FIXED", "bug-456", "Applied security patch")
```

---

### Pattern 4: Status Monitoring

```python
from htmlgraph import SDK

sdk = SDK(agent="monitor")

def get_project_health():
    """Get overall project health metrics."""
    features = sdk.features.all()

    stats = {
        "total": len(features),
        "completed": len([f for f in features if f.status == "done"]),
        "in_progress": len([f for f in features if f.status == "in-progress"]),
        "blocked": len([f for f in features if f.status == "blocked"]),
        "todo": len([f for f in features if f.status == "todo"]),
    }

    # Calculate completion percentage
    if stats["total"] > 0:
        stats["completion_percent"] = (
            stats["completed"] / stats["total"] * 100
        )

    return stats

# Usage
health = get_project_health()
print(f"Project {health['completion_percent']:.1f}% complete")
print(f"In progress: {health['in_progress']}")
print(f"Blocked: {health['blocked']}")
```

---

### Pattern 5: Task Delegation

```python
from htmlgraph import SDK, delegate_with_id

sdk = SDK(agent="orchestrator")

def delegate_feature_work(feature_id, engineer):
    """Delegate feature implementation to engineer."""

    feature = sdk.features.get(feature_id)
    if not feature:
        raise ValueError(f"Feature {feature_id} not found")

    # Create delegation
    task_id = delegate_with_id(
        prompt=f"""
Implement this feature:

Title: {feature.title}
Description: {feature.content}
Steps: {[s.description for s in feature.steps]}
        """,
        agent=engineer,
        task_id=f"impl-{feature_id}"
    )

    # Track delegation
    with sdk.features.edit(feature_id) as f:
        f.status = "in-progress"
        f.assigned_agent = engineer

    return task_id

# Usage
task_id = delegate_feature_work("feat-123", "code-generator")
```

---

### Pattern 6: Batch Import

```python
from htmlgraph import SDK

sdk = SDK(agent="importer")

def import_features_from_csv(csv_file):
    """Import features from CSV file."""

    import csv

    imported = []
    failed = []

    with open(csv_file) as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                feature = sdk.features.create(row["title"]) \
                    .set_priority(row.get("priority", "medium")) \
                    .set_description(row.get("description", "")) \
                    .save()

                imported.append(feature.id)
            except Exception as e:
                failed.append((row["title"], str(e)))

    return {
        "imported": len(imported),
        "failed": len(failed),
        "feature_ids": imported,
        "errors": failed
    }

# Usage
result = import_features_from_csv("features.csv")
print(f"Imported {result['imported']}, Failed {result['failed']}")
```

---

### Pattern 7: CI/CD Integration

```python
# deploy.py
from htmlgraph import SDK

def pre_deploy_check():
    """Check project health before deployment."""

    sdk = SDK(agent="ci-cd")

    # Get blockers
    blocked = sdk.features.where(status="blocked")
    if blocked:
        print(f"ERROR: {len(blocked)} blocked features")
        for f in blocked:
            print(f"  - {f.title}")
        return False

    # Get work in progress
    in_progress = sdk.features.where(status="in-progress")
    if in_progress:
        print(f"WARNING: {len(in_progress)} features still in progress")

    # Check for high-priority bugs
    critical_bugs = sdk.bugs.where(
        status="todo",
        priority="critical"
    )
    if critical_bugs:
        print(f"ERROR: {len(critical_bugs)} critical bugs")
        return False

    return True

# Usage in CI/CD pipeline
if __name__ == "__main__":
    if pre_deploy_check():
        print("OK to deploy")
    else:
        print("Deployment blocked")
        exit(1)
```

---

### Pattern 8: Metrics Collection

```python
from htmlgraph import SDK
from datetime import datetime, timedelta

sdk = SDK(agent="metrics")

def collect_metrics(days=7):
    """Collect project metrics for the last N days."""

    cutoff = datetime.now() - timedelta(days=days)
    features = sdk.features.all()

    recent_features = [
        f for f in features
        if datetime.fromisoformat(f.created_at) > cutoff
    ]

    metrics = {
        "period_days": days,
        "features_created": len(recent_features),
        "features_completed": len([
            f for f in recent_features if f.status == "done"
        ]),
        "average_completion_rate": len([
            f for f in recent_features if f.status == "done"
        ]) / len(recent_features) if recent_features else 0,
        "bottlenecks": sdk.dep_analytics.find_bottlenecks(top_n=3),
    }

    return metrics

# Usage
metrics = collect_metrics(days=7)
print(f"Features created: {metrics['features_created']}")
print(f"Features completed: {metrics['features_completed']}")
print(f"Completion rate: {metrics['average_completion_rate']:.1%}")
```

---

## Troubleshooting

### Issue: "Agent identifier is required"

**Cause:** No agent specified when creating SDK

**Solution:**
```python
# ❌ Wrong
sdk = SDK()

# ✅ Correct
sdk = SDK(agent="claude")
```

---

### Issue: ".htmlgraph directory not found"

**Cause:** Directory structure not created

**Solution:**
```python
from pathlib import Path

# Create directory structure
for subdir in ["features", "bugs", "spikes", "chores"]:
    Path(f".htmlgraph/{subdir}").mkdir(parents=True, exist_ok=True)

sdk = SDK(agent="claude")
```

---

### Issue: "NodeNotFoundError when editing"

**Cause:** Item ID doesn't exist

**Solution:**
```python
from htmlgraph.exceptions import NodeNotFoundError

try:
    with sdk.features.edit("feat-missing") as f:
        f.status = "done"
except NodeNotFoundError:
    print("Feature not found - creating new one")
    feature = sdk.features.create("New Feature").save()
```

---

### Issue: Empty results from queries

**Cause:** Wrong query syntax or no matching items

**Solution:**
```python
# Check what's available
all_items = sdk.features.all()
print(f"Total items: {len(all_items)}")

# Print available statuses
statuses = set(f.status for f in all_items)
print(f"Available statuses: {statuses}")

# Query correctly
todos = sdk.features.where(status="todo")
print(f"Found {len(todos)} todos")
```

---

### Issue: Slow queries

**Cause:** Large graph or complex queries

**Solution:**
```python
# Use QueryBuilder for complex queries (more efficient)
from htmlgraph import HtmlGraph

graph = HtmlGraph("features/")
results = graph.query_builder() \
    .where("priority", "high") \
    .and_("status").in_(["todo", "in-progress"]) \
    .execute()

# Or filter in Python (for small datasets)
results = [
    f for f in sdk.features.all()
    if f.priority == "high" and f.status != "done"
]
```

---

### Issue: Permission errors

**Cause:** Directory permission issues

**Solution:**
```bash
# Check permissions
ls -la .htmlgraph/
chmod -R 755 .htmlgraph/

# Or create with proper permissions
mkdir -p .htmlgraph/{features,bugs,spikes}
chmod 755 .htmlgraph
chmod 755 .htmlgraph/*
```

---

## Next Steps

1. **Read the full API reference** - [API_REFERENCE.md](API_REFERENCE.md)
2. **Explore HTTP API** - [HTTP_API.md](HTTP_API.md)
3. **Learn orchestration patterns** - [ORCHESTRATION_PATTERNS.md](ORCHESTRATION_PATTERNS.md)
4. **Join the community** - GitHub discussions
5. **Report issues** - GitHub issues

---

## Complete Example Application

```python
"""
Complete example: Project management dashboard
"""

from htmlgraph import SDK
from datetime import datetime

class ProjectManager:
    def __init__(self, agent_name):
        self.sdk = SDK(agent=agent_name)
        self.initialize()

    def initialize(self):
        """Ensure .htmlgraph structure exists."""
        from pathlib import Path
        for subdir in ["features", "bugs", "spikes"]:
            (Path(".htmlgraph") / subdir).mkdir(parents=True, exist_ok=True)

    def create_feature(self, title, priority="medium", steps=None):
        """Create a new feature."""
        builder = self.sdk.features.create(title).set_priority(priority)
        if steps:
            builder.add_steps(steps)
        return builder.save()

    def create_bug(self, title, severity="medium"):
        """Create a bug report."""
        return self.sdk.bugs.create(title) \
            .set_priority(severity) \
            .save()

    def get_status(self):
        """Get project status."""
        features = self.sdk.features.all()
        bugs = self.sdk.bugs.all()

        return {
            "features": {
                "total": len(features),
                "done": len([f for f in features if f.status == "done"]),
                "in_progress": len([f for f in features if f.status == "in-progress"]),
                "blocked": len([f for f in features if f.status == "blocked"]),
            },
            "bugs": {
                "total": len(bugs),
                "critical": len([b for b in bugs if b.priority == "critical"]),
                "open": len([b for b in bugs if b.status != "done"]),
            },
            "health": {
                "bottlenecks": self.sdk.dep_analytics.find_bottlenecks(top_n=3),
                "distribution": self.sdk.analytics.get_work_type_distribution(),
            }
        }

    def report(self):
        """Print project report."""
        status = self.get_status()

        print("=" * 50)
        print("PROJECT STATUS REPORT")
        print("=" * 50)

        print("\nFEATURES:")
        print(f"  Total: {status['features']['total']}")
        print(f"  Done: {status['features']['done']}")
        print(f"  In Progress: {status['features']['in_progress']}")
        print(f"  Blocked: {status['features']['blocked']}")

        print("\nBUGS:")
        print(f"  Total: {status['bugs']['total']}")
        print(f"  Critical: {status['bugs']['critical']}")
        print(f"  Open: {status['bugs']['open']}")

        print("\nHEALTH METRICS:")
        bottlenecks = status['health']['bottlenecks']
        if bottlenecks:
            print("  Top Bottlenecks:")
            for item in bottlenecks[:3]:
                print(f"    - {item['title']} (blocks {item['blocking_count']})")

        print("\n" + "=" * 50)

# Usage
if __name__ == "__main__":
    pm = ProjectManager("claude")

    # Create some work
    feature = pm.create_feature(
        "User Authentication",
        priority="high",
        steps=["Design", "Implement", "Test"]
    )

    bug = pm.create_bug("Login button styling", severity="medium")

    # Print report
    pm.report()
```

---

## Getting Help

- **Documentation**: See [API_REFERENCE.md](API_REFERENCE.md)
- **Examples**: Check GitHub repository examples/
- **Issues**: Report bugs on GitHub
- **Discussions**: Join community discussions

---

Version: 0.24.1
Last Updated: 2025-01-06
