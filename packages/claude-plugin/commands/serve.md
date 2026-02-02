<!-- Efficiency: SDK calls: 1, Bash calls: 0, Context: ~3% -->

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

This command uses the SDK's `start_server()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS (OPTIMIZED - 1 SDK CALL INSTEAD OF CLI):**

1. **Parse port from arguments:**
   ```python
   # Get port from args (default: 8080)
   port = int(args) if args and args.isdigit() else 8080
   ```

2. **Start server with auto_port capability (single SDK call):**
   ```python
   try:
       result = sdk.start_server(
           port=port,
           host="localhost",
           watch=True,
           auto_port=True  # Automatically find available port if requested port is busy
       )

       # Get actual port used (may differ if auto_port found a different one)
       actual_port = result.handle.port if hasattr(result.handle, 'port') else port
       url = f"http://localhost:{actual_port}"

       # Check if port changed
       port_note = ""
       if actual_port != port:
           port_note = f"\n\nNote: Port {port} was in use, using {actual_port} instead."

   except Exception as e:
       print(f"Error starting server: {e}")
       return
   ```

   **Context usage: <3% (compared to 25% with CLI)**

3. **Present dashboard information** using the output template below

4. **Explain dashboard features:**
   - Real-time feature progress tracking
   - Kanban board for task organization
   - Session activity logs
   - Dependency graph visualization

5. **Provide stop instructions:**
   - Server is running in background
   - Use SDK's stop_server method if needed: `sdk.stop_server(result.handle)`
```

### Output Format:

## Dashboard Running

**URL:** {url}{port_note}

The dashboard shows:
- Feature progress and kanban board
- Session history with activity logs
- Graph visualization of dependencies

To stop: `sdk.stop_server(handle)` or press Ctrl+C if running in foreground.
