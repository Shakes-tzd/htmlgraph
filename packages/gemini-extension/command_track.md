
### `/track` - Manually track an activity or note

**Usage:** `/htmlgraph:track <tool> <summary> [--files file1 file2]`

**Examples:**
- `/htmlgraph:track "Decision" "Chose React over Vue for frontend" --files src/components/App.tsx` - Track a decision with related files
- `/htmlgraph:track "Research" "Investigated auth options JWT vs sessions"` - Track research activity
- `/htmlgraph:track "Note" "User prefers dark mode as default"` - Track a general note


**SDK Method:** `sdk.None()`

```python
from htmlgraph import SDK

sdk = SDK(agent="gemini")

Same instructions as Claude Code
```
