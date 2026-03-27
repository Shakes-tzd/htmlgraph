# Features & Tracks

Learn how to create and manage features and tracks in HtmlGraph.

## Features

Features are the atomic units of work. Each feature represents a single deliverable with clear steps and status.

### Creating Features

#### Basic Feature

```bash
htmlgraph feature create "Add user profile page" --priority high
```

#### Feature with Steps

```bash
htmlgraph feature create "Add user profile page" --priority high
# Steps can be added in the HTML file directly or via the dashboard
```

#### Feature with Custom Properties

```bash
htmlgraph feature create "Add user profile page" --priority high
# Open the feature HTML to set additional properties
```

### Querying Features

```bash
# Get all features
htmlgraph feature list

# Filter by status
htmlgraph find features --status in-progress

# Filter by priority
htmlgraph find features --priority high

# Get a specific feature
htmlgraph feature show feat-a1b2c3d4
```

### Updating Features

```bash
# Start working on a feature (sets status to in-progress)
htmlgraph feature start feat-a1b2c3d4

# Complete a feature
htmlgraph feature complete feat-a1b2c3d4
```

### Deleting Features

```bash
# No direct CLI equivalent — archive or cancel instead
htmlgraph feature show feat-a1b2c3d4
# Edit the HTML directly to change status to "cancelled"
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

```bash
htmlgraph track new "User Authentication System" --priority high
```

#### Track with Spec and Plan

Use the TrackBuilder API for complex tracks. See the [TrackBuilder Guide](track-builder.md) for complete documentation.

### Linking Features to Tracks

```bash
# Create the track first
htmlgraph track new "User Authentication System" --priority high
# Note the track ID (e.g. trk-a1b2c3d4)

# Create features linked to the track
htmlgraph feature create "OAuth Setup" --priority high --track trk-a1b2c3d4
htmlgraph feature create "JWT Implementation" --priority high --track trk-a1b2c3d4
htmlgraph feature create "Testing & Deployment" --priority medium --track trk-a1b2c3d4
```

### Querying Tracks

```bash
# Get all tracks
htmlgraph track list

# Get a specific track
htmlgraph track show trk-a1b2c3d4

# Get all features for a track
htmlgraph find features --track trk-a1b2c3d4
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

```bash
# Create features
htmlgraph feature create "Database Schema"
htmlgraph feature create "User Authentication"

# Add blocking relationship (edit the feature HTML directly
# or use the dashboard to link features)
# Open .htmlgraph/features/feat-<auth-id>.html and add the edge
```

### Related Features

```bash
# Link related features via the dashboard or by editing feature HTML directly
uv run htmlgraph serve
# Navigate to the feature and add relationships
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

Document decisions and discoveries by creating a spike:

```bash
htmlgraph spike create "Decided to use Passport.js for OAuth (simpler than Auth0)"
```

## Next Steps

- [TrackBuilder Guide](track-builder.md) - Master the TrackBuilder API
- [Sessions Guide](sessions.md) - Understand activity tracking
- [Dashboard Guide](dashboard.md) - Visualize your work
- [API Reference](../api/sdk.md) - Complete SDK documentation
