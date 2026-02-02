<!-- Efficiency: SDK calls: 2, Bash calls: 0, Context: ~5% -->

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

This command uses the SDK's `track_activity()` and `get_active_work_item()` methods.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS (OPTIMIZED - 2 SDK CALLS INSTEAD OF CLI):**

1. **Validate or suggest tool types:**
   ```python
   # Standard tool types for manual tracking
   standard_types = ["Decision", "Research", "Note", "Context", "Blocker", "Insight", "Refactor"]

   if not tool:
       print("Please specify a tool type. Standard options:")
       for t in standard_types:
           print(f"  - {t}")
       return

   # Accept any tool type, but show suggestion if non-standard
   if tool not in standard_types:
       print(f"Note: Using custom tool type '{tool}'. Standard types: {', '.join(standard_types)}")
   ```

2. **Track the activity (single SDK call):**
   ```python
   # Parse files from args if provided
   files = args.get('files', []) if args else []

   # Track activity
   entry = sdk.track_activity(
       tool=tool,
       summary=summary,
       file_paths=files
   )
   ```

3. **Get active feature attribution (single SDK call):**
   ```python
   active_item = sdk.get_active_work_item()
   feature_info = f"Feature: {active_item.id} - {active_item.title}" if active_item else "No active feature"
   ```

   **Context usage: <5% (compared to 30% with CLI parsing)**

4. **Present summary** using the output template below

5. **Show attribution:**
   - Display which feature this activity is linked to
   - If no active feature, suggest starting one with `/htmlgraph:start`
```

### Output Format:

## Activity Tracked

**Type:** {tool}
**Summary:** {summary}
**Files:** {', '.join(files) if files else 'None'}
**Attributed to:** {feature_info}

Activity recorded in current session.

{suggestion_text if no active feature}
