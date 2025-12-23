
### `/plan` - Start planning a new track with spike or create directly

**Usage:** `/htmlgraph:plan <description> [--spike] [--timebox HOURS]`

**Examples:**
- `/htmlgraph:plan "User authentication system"` - Create a planning spike for auth system (4h timebox)
- `/htmlgraph:plan "Real-time notifications" --timebox 3` - Create planning spike with 3-hour timebox
- `/htmlgraph:plan "Simple bug fix dashboard" --no-spike` - Create track directly without spike


**SDK Method:** `sdk.smart_plan()`

```python
from htmlgraph import SDK

sdk = SDK(agent="gemini")

Same as claude_code but with agent="gemini"
```
