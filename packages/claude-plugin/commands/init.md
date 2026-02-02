<!-- Efficiency: SDK calls: 1, Bash calls: 0, Context: ~3% -->

# /htmlgraph:init

Initialize HtmlGraph in a project

## Usage

```
/htmlgraph:init
```

## Parameters



## Examples

```bash
/htmlgraph:init
```
Set up HtmlGraph directory structure in project



## Instructions for Claude

This command uses the SDK's `init_project()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS (OPTIMIZED - 1 SDK CALL INSTEAD OF CLI):**

1. **Initialize project (single SDK call):**
   ```python
   result = sdk.init_project()

   # Check result status
   if result['status'] == 'already_exists':
       print("## HtmlGraph Already Initialized")
       print(f"\n`.htmlgraph/` directory already exists at: {result['path']}")
       print(f"\nExisting directories: {', '.join(result['directories'])}")

   elif result['status'] == 'created':
       print("## HtmlGraph Initialized")
       print(f"\nCreated `.htmlgraph/` at: {result['path']}")
       print("\nDirectory structure:")
       for dirname in result['directories']:
           descriptions = {
               'features': 'Feature work items',
               'sessions': 'Session activity logs',
               'tracks': 'Multi-feature tracks',
               'spikes': 'Research and investigation',
               'bugs': 'Bug tracking',
               'patterns': 'Workflow patterns',
               'insights': 'Session insights',
               'metrics': 'Aggregated metrics',
               'todos': 'Persistent tasks',
               'task-delegations': 'Subagent work tracking'
           }
           desc = descriptions.get(dirname, dirname)
           print(f"  - {dirname}/ - {desc}")
   ```

   **Context usage: <3% (compared to 30% with CLI calls)**

2. **Present next steps** using the output template below

3. **Guide the user:**
   - How to plan work: `/htmlgraph:plan "title"`
   - How to start session: `/htmlgraph:start`
   - How to view dashboard: `/htmlgraph:serve`

4. **Highlight key points:**
   - All subsequent work will be tracked automatically
   - Use SDK/slash commands for all operations
   - Access dashboard to view progress visually
```

### Output Format:

## HtmlGraph Initialized

Created `.htmlgraph/` directory with:
- `features/` - Feature work items
- `sessions/` - Session activity logs
- `tracks/` - Multi-feature tracks
- `spikes/` - Research and investigation
- `bugs/` - Bug tracking
- `patterns/` - Workflow patterns
- `insights/` - Session insights
- `metrics/` - Aggregated metrics
- `todos/` - Persistent tasks
- `task-delegations/` - Subagent work tracking

### Next Steps
1. Plan new work: `/htmlgraph:plan "Feature title"`
2. Start session: `/htmlgraph:start`
3. View dashboard: `/htmlgraph:serve`

### Quick Start
```bash
# Start planning
/htmlgraph:plan "Add user authentication"

# Begin work
/htmlgraph:start

# View progress
/htmlgraph:serve
# Open http://localhost:8080
```
