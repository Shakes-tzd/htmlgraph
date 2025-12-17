# /htmlgraph:feature-complete

Mark a feature as complete.

## Usage

```
/htmlgraph:feature-complete [feature-id]
```

## Arguments

- `feature-id` (optional): The feature ID to complete. If not provided, completes the current active feature.

## Instructions for Claude

### Get current feature if not specified:
```bash
htmlgraph feature list --status in-progress
```

### Complete the feature:
```bash
htmlgraph feature complete <feature-id>
```

### After completion:
```bash
# Show updated status
htmlgraph status
htmlgraph feature list
```

Present summary:
```markdown
## Feature Completed

**ID:** {feature_id}
**Title:** {title}
**Status:** done

### Progress Update
**Completed:** {done}/{total} ({percentage}%)

### What's Next?
{List pending features if any}

Would you like to start the next feature?
```
