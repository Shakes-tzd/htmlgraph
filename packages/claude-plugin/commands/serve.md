# /htmlgraph:serve

Start the dashboard server.

## Usage

```
/htmlgraph:serve [port]
```

## Arguments

- `port` (optional): Port number (default: 8080)

## Instructions for Claude

### Start the server:
```bash
htmlgraph serve --port ${port:-8080}
```

### Present:
```markdown
## Dashboard Running

**URL:** http://localhost:{port}

The dashboard shows:
- Feature progress and kanban board
- Session history with activity logs
- Graph visualization of dependencies

Press Ctrl+C to stop the server.
```

Note: If running in background, use:
```bash
htmlgraph serve --port {port} &
```
