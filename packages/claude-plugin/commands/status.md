# /htmlgraph:status

Quick status check - shows project progress and current feature.

## Usage

```
/htmlgraph:status
```

## Instructions for Claude

Run the following commands to get status:

```bash
# Get overall status
htmlgraph status

# List features with status
htmlgraph feature list

# List recent sessions
htmlgraph session list --limit 3
```

Then present a brief summary:

```markdown
## Project Status

**Progress:** {done}/{total} ({percentage}%)
**Active:** {in_progress_count} features in progress

### Current Feature(s)
{List active features with their titles}

### Quick Actions
- `htmlgraph feature start <id>` - Start a feature
- `htmlgraph feature complete <id>` - Complete a feature
- `htmlgraph serve` - Open dashboard
```
