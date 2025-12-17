# /htmlgraph:feature-add

Add a new feature to the backlog.

## Usage

```
/htmlgraph:feature-add [title]
```

## Arguments

- `title` (optional): The feature title. If not provided, ask the user.

## Instructions for Claude

### If title provided:
```bash
htmlgraph feature add "<title>"
```

### If no title:
Ask the user: "What feature would you like to add?"

Then create the feature with the provided title.

### After creation:
```bash
# Show the new feature
htmlgraph feature list
```

Present confirmation:
```markdown
## Feature Added

**ID:** {feature_id}
**Title:** {title}
**Status:** todo

Start working on it with:
```bash
htmlgraph feature start {feature_id}
```
```
