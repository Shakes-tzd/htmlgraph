# /htmlgraph:track

Manually track an activity or note.

## Usage

```
/htmlgraph:track <tool> <summary> [--files file1 file2]
```

## Arguments

- `tool` (required): The tool/action type (e.g., "Note", "Decision", "Research")
- `summary` (required): Description of the activity
- `--files` (optional): Related files

## Instructions for Claude

### Track activity:
```bash
htmlgraph track "<tool>" "<summary>" --files <file1> <file2>
```

### Examples:
```bash
# Track a decision
htmlgraph track "Decision" "Chose React over Vue for frontend" --files src/components/App.tsx

# Track research
htmlgraph track "Research" "Investigated auth options: JWT vs sessions"

# Track a note
htmlgraph track "Note" "User prefers dark mode as default"
```

### After tracking:
```markdown
## Activity Tracked

**Type:** {tool}
**Summary:** {summary}
**Attributed to:** {feature_id or "No active feature"}

Activity recorded in current session.
```
