# /htmlgraph:feature-start

Start working on a feature (moves it to in-progress).

## Usage

```
/htmlgraph:feature-start <feature-id>
```

## Arguments

- `feature-id` (required): The feature ID to start working on

## Instructions for Claude

### If feature-id provided:
```bash
htmlgraph feature start <feature-id>
```

### If no feature-id:
First list available features:
```bash
htmlgraph feature list --status todo
```

Then ask the user which feature to start.

### After starting:
Present the feature context:
```markdown
## Started: {feature_title}

**ID:** {feature_id}
**Status:** in-progress

### Description
{feature description}

### Steps
{list implementation steps if any}

---

All activity will now be attributed to this feature.
What would you like to work on first?
```
