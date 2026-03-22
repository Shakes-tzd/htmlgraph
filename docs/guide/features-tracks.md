# Features & Tracks

Learn how to create and manage features and tracks in HtmlGraph.

## Features

Features are the atomic units of work. Each feature represents a single deliverable with clear steps and status.

### Creating Features

#### Basic Feature

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

feature = sdk.features.create(
    title="Add user profile page",
    priority="high"
)
```

#### Feature with Steps

```python
feature = sdk.features.create(
    title="Add user profile page",
    priority="high",
    steps=[
        "Create profile component",
        "Add routing",
        "Fetch user data",
        "Write tests"
    ]
)
```

#### Feature with Custom Properties

```python
feature = sdk.features.create(
    title="Add user profile page",
    priority="high",
    status="todo",
    steps=["Create component", "Add routing", "Write tests"],
    properties={
        "effort": 4,  # hours
        "assignee": "claude",
        "tags": ["ui", "frontend"]
    }
)
```

### Querying Features

```python
# Get all features
all_features = sdk.features.all()

# Filter by status
in_progress = sdk.features.where(status="in-progress")

# Filter by priority
high_priority = sdk.features.where(priority="high")

# Multiple filters
blocked_high = sdk.features.where(status="blocked", priority="high")

# Get a specific feature
feature = sdk.features.get("feat-a1b2c3d4")
```

### Updating Features

```python
# Get the feature
feature = sdk.features.get("feat-a1b2c3d4")

# Update status
feature.status = "in-progress"
feature.save()

# Complete a step
feature.steps[0].completed = True
feature.save()

# Update priority
feature.priority = "critical"
feature.save()

# Add a note to activity log
sdk.track_activity(
    feature_id=feature.id,
    activity="Discovered dependency on auth service"
)
```

### Deleting Features

```python
# Delete a feature
sdk.features.delete("feat-a1b2c3d4")
```

## Tracks

Tracks are multi-feature projects that bundle related work with specifications and plans.

### When to Use Tracks

Use tracks when:

- Work spans **3+ related features**
- You need **multi-phase planning**
- Clear **specs and requirements** are needed
- Work has **dependencies and sequencing**
- You want **time estimates and milestones**

### Creating Tracks

#### Simple Track

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

track = sdk.tracks.create(
    title="User Authentication System",
    priority="high"
)
```

#### Track with Spec and Plan

Use the TrackBuilder API for complex tracks:

```python
track = sdk.tracks.builder() \
    .title("User Authentication System") \
    .priority("high") \
    .with_spec(
        overview="Implement secure authentication with OAuth 2.0",
        requirements=[
            ("Google OAuth integration", "must-have"),
            ("GitHub OAuth integration", "must-have"),
            ("JWT token management", "must-have"),
            ("Refresh token rotation", "should-have")
        ],
        success_criteria=[
            "Users can sign in with Google",
            "Users can sign in with GitHub",
            "Tokens refresh automatically before expiry",
            "99.9% uptime for auth service"
        ],
        constraints=[
            "Must comply with GDPR",
            "Must use OAuth 2.0 standard",
            "Maximum 500ms latency for token validation"
        ]
    ) \
    .with_plan_phases([
        ("Phase 1: OAuth Setup", [
            "Configure OAuth providers (2h)",
            "Set up redirect endpoints (1h)",
            "Create callback handlers (2h)"
        ]),
        ("Phase 2: JWT Implementation", [
            "Implement JWT signing (3h)",
            "Add token refresh logic (2h)",
            "Create middleware (2h)"
        ]),
        ("Phase 3: Testing & Deployment", [
            "Write integration tests (4h)",
            "Test with real OAuth providers (2h)",
            "Deploy to staging (1h)"
        ])
    ]) \
    .create()

print(f"Created track: {track.track_id}")
# View at: .htmlgraph/tracks/{track.track_id}/index.html
```

See the [TrackBuilder Guide](track-builder.md) for complete documentation.

### Linking Features to Tracks

Create features that belong to a track:

```python
# Create the track
track = sdk.tracks.builder() \
    .title("User Authentication System") \
    .priority("high") \
    .create()

# Create features linked to the track
oauth_feature = sdk.features.create(
    title="OAuth Setup",
    priority="high",
    track_id=track.track_id,
    steps=[
        "Configure Google OAuth",
        "Configure GitHub OAuth",
        "Set up redirect endpoints"
    ]
)

jwt_feature = sdk.features.create(
    title="JWT Implementation",
    priority="high",
    track_id=track.track_id,
    steps=[
        "Implement JWT signing",
        "Add token refresh logic",
        "Create auth middleware"
    ]
)

test_feature = sdk.features.create(
    title="Testing & Deployment",
    priority="medium",
    track_id=track.track_id,
    steps=[
        "Write integration tests",
        "Test with OAuth providers",
        "Deploy to staging"
    ]
)
```

### Querying Tracks

```python
# Get all tracks
all_tracks = sdk.tracks.all()

# Get a specific track
track = sdk.tracks.get("trk-a1b2c3d4")

# Get all features for a track
features = sdk.features.where(track_id=track.track_id)
```

### Track Structure

Each track creates a directory with three HTML files:

```
.htmlgraph/tracks/trk-a1b2c3d4/
├── index.html    # Track overview and status
├── spec.html     # Requirements and success criteria
└── plan.html     # Phased implementation plan
```

Open any file in a browser to view it with full styling and navigation.

## Feature Relationships

Features can have relationships with other features:

### Blocking Relationships

```python
# Create features
db_feature = sdk.features.create(title="Database Schema")
auth_feature = sdk.features.create(title="User Authentication")

# Add blocking relationship
sdk.features.add_edge(
    from_id=db_feature.id,
    to_id=auth_feature.id,
    relationship="blocks"
)

# Now auth_feature shows it's blocked by db_feature
```

### Related Features

```python
# Link related features
sdk.features.add_edge(
    from_id=auth_feature.id,
    to_id=session_feature.id,
    relationship="related"
)
```

## Feature Status Workflow

The standard status progression:

```
todo → in-progress → blocked → in-progress → done
  ↓                                             ↓
  └──────────────> cancelled <─────────────────┘
```

### Status Meanings

- **todo**: Not started
- **in-progress**: Currently being worked on
- **blocked**: Waiting on dependencies
- **done**: Completed successfully
- **cancelled**: Work abandoned

### CLI Workflow

```bash
# Create a feature
htmlgraph feature create "Add profile page" --priority high

# Start working on it
htmlgraph feature start feat-a1b2c3d4

# Mark as complete
htmlgraph feature complete feat-a1b2c3d4
```

## Best Practices

### Feature Naming

- **Good**: "Add user profile page", "Fix login redirect bug"
- **Bad**: "Work on stuff", "Update code"

Be specific and action-oriented.

### Feature Sizing

Keep features small and focused:

- **Good**: 1-8 hours of work, 3-7 steps
- **Too small**: <1 hour, trivial changes
- **Too large**: >16 hours, should be a track

### Track Planning

For tracks, invest time in the spec and plan:

- Clear success criteria
- Realistic time estimates
- Logical phase progression
- Dependencies identified upfront

### Activity Logging

Document decisions and discoveries:

```python
sdk.track_activity(
    feature_id=feature.id,
    activity="Decided to use Passport.js for OAuth (simpler than Auth0)"
)
```

## Next Steps

- [TrackBuilder Guide](track-builder.md) - Master the TrackBuilder API
- [Sessions Guide](sessions.md) - Understand activity tracking
- [Dashboard Guide](dashboard.md) - Visualize your work
- [API Reference](../api/sdk.md) - Complete SDK documentation
