# /htmlgraph:track

Manually track an activity or note

## Usage

```
/htmlgraph:track <tool> <summary> [--files file1 file2]
```

## Parameters

- `tool` (required): The tool/action type (e.g., "Note", "Decision", "Research")
- `summary` (required): Description of the activity
- `files` (optional): Related files


## Examples

```bash
/htmlgraph:track "Decision" "Chose React over Vue for frontend" --files src/components/App.tsx
```
Track a decision with related files

```bash
/htmlgraph:track "Research" "Investigated auth options JWT vs sessions"
```
Track research activity

```bash
/htmlgraph:track "Note" "User prefers dark mode as default"
```
Track a general note



## Instructions for Claude

This command uses the SDK's `None()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Call the track command** with the provided arguments:
   ```bash
   htmlgraph track "<tool>" "<summary>" --files <file1> <file2>
   ```

2. **Parse the output** to extract:
   - Activity type
   - Summary text
   - Feature attribution
   - Confirmation message

3. **Present a summary** using the output template above

4. **Confirm the action:**
   - Show what was tracked
   - Link to active feature if applicable
   - Suggest next steps if needed
```

### Output Format:

## Activity Tracked

**Type:** {tool}
**Summary:** {summary}
**Attributed to:** {feature_id or "No active feature"}

Activity recorded in current session.
