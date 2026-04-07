# API Reference

Complete API documentation for HtmlGraph.

## Documentation Formats

HtmlGraph provides API documentation in two formats:

- **This site** - Integrated MkDocs documentation with examples and guides
- **[Standalone API Docs](/htmlgraph/api-pdoc/htmlgraph.html)** - Auto-generated pdoc documentation (alternative view)

Choose whichever format you prefer!

## Core Modules

- **[SDK](sdk.md)** - Main SDK interface for agents
- **[HtmlGraph](graph.md)** - Core graph operations
- **[Models](models.md)** - Pydantic data models
- **[Planning](planning.md)** - Spec and Plan models
- **[Agents](agents.md)** - Agent interface
- **[Server](server.md)** - Dashboard server
- **[TrackBuilder](track-builder.md)** - Fluent track creation API
- **[ID Generation](ids.md)** - Collision-resistant IDs for multi-agent collaboration

## Quick Reference

### Importing

```python
from htmlgraph import SDK, HtmlGraph
from htmlgraph.models import Feature, Track, Session
from htmlgraph.planning import Spec, Plan

# ID generation utilities
from htmlgraph import generate_id, parse_id, is_valid_id
```

### SDK Initialization

```python
from htmlgraph import SDK

# Basic initialization
sdk = SDK(agent="claude")

# Custom graph directory
sdk = SDK(agent="claude", graph_dir="/path/to/.htmlgraph")

# Disable auto-session management
sdk = SDK(agent="claude", auto_session=False)
```

### Common Operations

```python
# Features
feature = sdk.features.create("Task")
features = sdk.features.all()
filtered = sdk.features.where(status="in-progress")

# Tracks
track = sdk.tracks.builder().title("Project").create()
tracks = sdk.tracks.all()

# Sessions
sessions = sdk.sessions.all()
current = sdk.sessions.current()

# Status
status = sdk.status()
```

## Type Hints

HtmlGraph is fully typed with Pydantic models:

```python
from htmlgraph import SDK
from htmlgraph.models import Feature, FeatureStatus, Priority

def process_feature(feature: Feature) -> None:
    if feature.status == FeatureStatus.IN_PROGRESS:
        print(f"Working on: {feature.title}")

sdk: SDK = SDK(agent="claude")
feature: Feature = sdk.features.create("Task")
```

## Error Handling

HtmlGraph raises specific exceptions:

```python
from htmlgraph import SDK
from htmlgraph.exceptions import (
    FeatureNotFoundError,
    TrackNotFoundError,
    ValidationError
)

sdk = SDK(agent="claude")

try:
    feature = sdk.features.get("invalid-id")
except FeatureNotFoundError as e:
    print(f"Feature not found: {e}")

try:
    track = sdk.tracks.builder().create()  # Missing title
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## Next Steps

Browse the API documentation:

- [SDK Reference](sdk.md) - Complete SDK API
- [Models Reference](models.md) - Data models and schemas
- [TrackBuilder Reference](track-builder.md) - TrackBuilder fluent API
