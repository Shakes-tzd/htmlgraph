# /htmlgraph:plan

Start planning a new track with spike or create directly

## Usage

```
/htmlgraph:plan <description> [--spike] [--timebox HOURS]
```

## Parameters

- `description` (required): What you want to plan (e.g., "User authentication system")
- `--spike` (optional) (default: True): Create a planning spike first (recommended for complex work)
- `--timebox` (optional) (default: 4.0): Time limit for spike in hours


## Examples

```bash
/htmlgraph:plan "User authentication system"
```
Create a planning spike for auth system (4h timebox)

```bash
/htmlgraph:plan "Real-time notifications" --timebox 3
```
Create planning spike with 3-hour timebox

```bash
/htmlgraph:plan "Simple bug fix dashboard" --no-spike
```
Create track directly without spike



## Instructions for Claude

This command uses the SDK's `smart_plan()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
```python
from htmlgraph import SDK

sdk = SDK(agent="claude")
result = sdk.smart_plan(
    description=args.description,
    create_spike=args.spike,
    timebox_hours=args.timebox
)

# Format and display result
print(format_output(result))
```
```

### Output Format:

## Planning Started

**Type:** {type}
**Title:** {title}
**Status:** {status}

### Project Context
- Bottlenecks: {project_context.bottlenecks_count}
- High-risk items: {project_context.high_risk_count}
- Parallel capacity: {project_context.parallel_capacity}

### Next Steps
{next_steps}
