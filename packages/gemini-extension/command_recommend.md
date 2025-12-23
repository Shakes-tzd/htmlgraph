
### `/recommend` - Get smart recommendations on what to work on next

**Usage:** `/htmlgraph:recommend [--count N] [--check-bottlenecks]`

**Examples:**
- `/htmlgraph:recommend` - Get top 3 recommendations with bottleneck check
- `/htmlgraph:recommend --count 5` - Get top 5 recommendations
- `/htmlgraph:recommend --no-check-bottlenecks` - Recommendations only, skip bottleneck analysis


**SDK Method:** `sdk.recommend_next_work()`

```python
from htmlgraph import SDK

sdk = SDK(agent="gemini")

Same as claude_code but with agent="gemini"
```
