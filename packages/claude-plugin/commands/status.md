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

This command uses the SDK's `None()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Run these commands:**
   ```bash
   htmlgraph status
   htmlgraph feature list
   htmlgraph session list --limit 3
   ```

2. **Parse the output** to extract:
   - Total features and completion percentage
   - Currently active features
   - Recent session count

3. **Present a summary** using the output template above

4. **Recommend next steps** based on status:
   - If no active features → Suggest `/htmlgraph:recommend`
   - If bottlenecks exist → Highlight them
   - If features done → Acknowledge progress
```

### Output Format:

## Project Status

**Progress:** {done}/{total} ({percentage}%)
**Active:** {in_progress_count} features in progress

### Current Feature(s)
{active_features}

### Quick Actions
- Use `/htmlgraph:plan` to start planning new work
- Use `/htmlgraph:recommend` to get recommendations
- Run `htmlgraph serve` to open dashboard
