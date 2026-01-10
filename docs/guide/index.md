# User Guide

Welcome to the HtmlGraph user guide. This section provides in-depth documentation for all HtmlGraph features.

## What You'll Learn

This guide covers:

- **[Features & Tracks](features-tracks.md)** - Creating and managing features and tracks
- **[TrackBuilder](track-builder.md)** - Mastering the TrackBuilder fluent API
- **[Delegation](delegation.md)** - Distributing work to parallel subagents with Task()
- **[Skills](skills.md)** - Specialized guides for orchestration, deployment, and debugging
- **[Session Hierarchies](session-hierarchies.md)** - Understanding parent-child session relationships
- **[Sessions](sessions.md)** - Understanding session tracking and attribution
- **[Agents](agents.md)** - Integrating HtmlGraph with AI agents
- **[Dashboard](dashboard.md)** - Using the interactive dashboard

## Quick Navigation

### For Beginners

Start with these guides in order:

1. [Features & Tracks](features-tracks.md) - Learn the basics
2. [Dashboard](dashboard.md) - Visualize your work
3. [Sessions](sessions.md) - Understand activity tracking

### For Agent Developers

Jump to these sections:

1. [Delegation](delegation.md) - Task distribution and orchestration patterns
2. [Skills](skills.md) - Specialized guides for complex workflows
3. [Session Hierarchies](session-hierarchies.md) - Parent-child session relationships
4. [Agents](agents.md) - Agent integration patterns
5. [TrackBuilder](track-builder.md) - Deterministic track creation
6. [Sessions](sessions.md) - Session management and attribution

### For Power Users

Advanced topics:

1. [Skills](skills.md) - Master all specialized guides and decision frameworks
2. [Session Hierarchies](session-hierarchies.md) - Advanced session querying and analysis
3. [Delegation](delegation.md) - Complex delegation patterns and cost optimization
4. [TrackBuilder](track-builder.md) - Complex track workflows
5. [Sessions](sessions.md) - Custom session handling
6. [API Reference](../api/index.md) - Complete API documentation

## Common Workflows

### Creating a Simple Feature

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")
feature = sdk.features.create(
    title="Add login page",
    priority="high",
    steps=["Create component", "Add routing", "Write tests"]
)
```

[Learn more →](features-tracks.md#creating-features)

### Creating a Complex Track

```python
track = sdk.tracks.builder() \
    .title("User Authentication") \
    .with_spec(overview="Full auth system") \
    .with_plan_phases([
        ("Phase 1", ["OAuth setup (2h)", "JWT middleware (3h)"])
    ]) \
    .create()
```

[Learn more →](track-builder.md)

### Linking Features to Tracks

```python
# Create features for the track
auth_feature = sdk.features.create(
    title="OAuth Setup",
    track_id=track.track_id
)

jwt_feature = sdk.features.create(
    title="JWT Middleware",
    track_id=track.track_id
)
```

[Learn more →](features-tracks.md#linking-features-to-tracks)

### Starting a Session

Sessions are automatically managed by HtmlGraph hooks:

```bash
# Session starts automatically when you begin working
htmlgraph feature start feature-001

# View session status
htmlgraph status

# Session ends automatically when you complete the feature
htmlgraph feature complete feature-001
```

[Learn more →](sessions.md)

## Need Help?

- Check the [API Reference](../api/index.md) for detailed SDK documentation
- Browse [Examples](../examples/index.md) for real-world use cases
- Read the [Philosophy](../philosophy/why-html.md) to understand design decisions
- Visit [GitHub Discussions](https://github.com/Shakes-tzd/htmlgraph/discussions) for community support
