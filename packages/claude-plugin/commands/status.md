<!-- Efficiency: SDK calls: 1, Bash calls: 0, Context: ~5% -->

# /htmlgraph:status

Check project status and active features

## Usage

```
/htmlgraph:status
```

## Parameters



## Examples

```bash
/htmlgraph:status
```
Show project progress and current feature



## Instructions for Claude

This command uses the SDK's `get_status()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS (OPTIMIZED - 1 SDK CALL INSTEAD OF 3 CLI CALLS):**

1. **Get comprehensive status (single SDK call):**
   ```python
   status = sdk.get_status()
   active = sdk.features.where(status="in-progress")
   ```

   **Context usage: <5% (compared to 25% with 3 CLI calls)**

2. **Extract key metrics:**
   - Total features: status['total_nodes']
   - Completed: status['done_count']
   - In progress: status['in_progress_count']
   - Completion percentage: (done_count / total_nodes * 100)
   - Active features with details from 'active' list

3. **Present a summary** using the output template below

4. **Recommend next steps** based on status:
   - If no active features → Suggest `/htmlgraph:recommend`
   - If active features exist → Show their progress
   - If features done → Acknowledge progress
   - Suggest `/htmlgraph:plan` for new work
```

### Output Format:

## Project Status

**Progress:** {status['done_count']}/{status['total_nodes']} ({percentage}%)
**Active:** {status['in_progress_count']} features in progress

### Current Feature(s)
{active_features with titles and step progress}

### Quick Actions
- Use `/htmlgraph:plan` to start planning new work
- Use `/htmlgraph:recommend` to get recommendations
- Run `htmlgraph serve` to open dashboard
