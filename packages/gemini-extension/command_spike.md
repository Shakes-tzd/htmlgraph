
### `/spike` - Create a research/planning spike

**Usage:** `/htmlgraph:spike <title> [--context TEXT] [--timebox HOURS]`

**Examples:**
- `/htmlgraph:spike "Research OAuth providers"` - Create a 4-hour research spike
- `/htmlgraph:spike "Investigate caching strategies" --timebox 2` - Create a 2-hour spike
- `/htmlgraph:spike "Plan data migration" --context "Moving from SQL to NoSQL"` - Spike with background context


**SDK Method:** `sdk.start_planning_spike()`

```python
from htmlgraph import SDK

sdk = SDK(agent="gemini")

Same as claude_code but with agent="gemini"
```
