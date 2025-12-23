# /htmlgraph:serve

Start the dashboard server

## Usage

```
/htmlgraph:serve [port]
```

## Parameters

- `port` (optional) (default: 8080): Port number for the dashboard server


## Examples

```bash
/htmlgraph:serve
```
Start dashboard on default port 8080

```bash
/htmlgraph:serve 3000
```
Start dashboard on port 3000



## Instructions for Claude

This command uses the SDK's `None()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Start the server:**
   ```bash
   htmlgraph serve --port ${port:-8080}
   ```

2. **Present the dashboard output** using the output template above

3. **Explain the dashboard features:**
   - Real-time feature progress tracking
   - Kanban board for task organization
   - Session activity logs
   - Dependency graph visualization

4. **Provide instructions** for stopping the server:
   - Press Ctrl+C to stop
   - Or use background mode: `htmlgraph serve --port {port} &`
```

### Output Format:

## Dashboard Running

**URL:** http://localhost:{port}

The dashboard shows:
- Feature progress and kanban board
- Session history with activity logs
- Graph visualization of dependencies

Press Ctrl+C to stop the server.
