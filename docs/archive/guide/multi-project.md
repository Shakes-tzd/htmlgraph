# Multi-Project Dashboard

Run a single Phoenix LiveView dashboard serving multiple HtmlGraph projects simultaneously.

## Quick Start

```bash
# Set workspace root (directory containing your projects)
export HTMLGRAPH_WORKSPACE=/path/to/workspace

# Start with Docker Compose
docker compose up -d

# Open http://localhost:4000/projects
```

## How It Works

The dashboard scans your workspace root for directories containing `.htmlgraph/htmlgraph.db`. Each discovered project appears in the project selector dropdown.

```
/workspace/
├── project-a/
│   └── .htmlgraph/
│       └── htmlgraph.db    ← discovered
├── project-b/
│   └── .htmlgraph/
│       └── htmlgraph.db    ← discovered
└── project-c/                     ← no .htmlgraph/, ignored
```

## Configuration

### Environment Variables

| Env Var | Default | Description |
|---------|---------|-------------|
| `HTMLGRAPH_WORKSPACE` | Parent directory of current project | Root directory to scan for `.htmlgraph/` |
| `HTMLGRAPH_DB_PATH` | `{workspace}/.htmlgraph/htmlgraph.db` | Default DB path when no project selected |
| `PHX_HOST` | `localhost` | Phoenix host binding |
| `PHX_PORT` | `4000` | Phoenix port |

### Docker Compose Setup

Create `docker-compose.yml` in your workspace root:

```yaml
version: '3.8'

services:
  dashboard:
    image: ghcr.io/shakestzd/htmlgraph-dashboard:latest
    ports:
      - "4000:4000"
    environment:
      HTMLGRAPH_WORKSPACE: /workspace
      PHX_HOST: 0.0.0.0
      PHX_PORT: 4000
    volumes:
      - ./:/workspace:ro
    restart: unless-stopped
```

Then run:

```bash
docker compose up -d
```

View logs:

```bash
docker compose logs -f dashboard
```

## Without Docker

Run the dashboard from any HtmlGraph project with workspace support:

```bash
# From any project directory
cd /path/to/workspace/my-project

# Serve with workspace scanning
htmlgraph serve --workspace /path/to/workspace
```

The dashboard will:
1. Scan `/path/to/workspace` for all `.htmlgraph/htmlgraph.db` files
2. Build a project list
3. Serve on http://localhost:4000

## Project Switching

### Dropdown Selector

Use the project selector dropdown in the navigation bar to switch between projects:

1. Click the project dropdown (top-left of nav)
2. Select a project from the list
3. All views update to show data for the selected project

### Keyboard Shortcuts

- **Cmd/Ctrl + P** - Project selector (when available)
- **Cmd/Ctrl + K** - Command palette

### Deep Linking

Use project selector in URL:

```
http://localhost:4000/?project=project-a
http://localhost:4000/kanban?project=project-b
http://localhost:4000/graph?project=project-c
```

## Views Scoped to Project

All dashboard views are automatically scoped to the selected project:

- **Activity Feed** - Shows events only for this project's sessions
- **Kanban Board** - Displays work items (features, bugs, tasks)
- **Dependency Graph** - Shows work item relationships
- **Costs** - Analytics for this project's activity
- **Analytics** - Metrics and performance data

## Adding New Projects

1. Initialize HtmlGraph in your project:
   ```bash
   cd /path/to/new-project
   htmlgraph init
   ```

2. The dashboard automatically discovers it on next scan

3. No restart needed - just refresh the dashboard

## Database Location Discovery

The dashboard uses this search order:

1. **Explicit path**: `HTMLGRAPH_DB_PATH` environment variable
2. **Project selection**: Selected project's `.htmlgraph/htmlgraph.db`
3. **Workspace scan**: Find all `.htmlgraph/htmlgraph.db` in `HTMLGRAPH_WORKSPACE`
4. **Default**: `~/.htmlgraph/htmlgraph.db` (single-project fallback)

## Troubleshooting

### Projects Not Appearing

Check that each project has been initialized:

```bash
ls -la /workspace/project-*/. htmlgraph/htmlgraph.db

# Or search for all databases
find /workspace -name "htmlgraph.db" -type f
```

Initialize missing projects:

```bash
cd /workspace/project-name
htmlgraph init
```

### Dashboard Not Connecting

Verify workspace path is correct:

```bash
docker compose logs dashboard
# Look for: "Scanning workspace: /path/to/workspace"
```

Check mounted volumes:

```bash
docker exec dashboard ls -la /workspace/
```

### Slow Performance with Many Projects

The dashboard scans all projects on startup. For workspaces with 50+ projects:

1. Use explicit `HTMLGRAPH_DB_PATH` to select a single project
2. Or specify a subset in `HTMLGRAPH_WORKSPACE`

## Performance Tips

- **Use SSD storage** for `.htmlgraph/` databases
- **Limit projects** to 20-30 per dashboard (use separate dashboards for larger teams)
- **Keep databases small** - export old sessions periodically
- **Mount workspace as read-only** - reduces I/O overhead

## Multi-Machine Setup

For distributed team access:

```bash
# Server machine
export HTMLGRAPH_WORKSPACE=/mnt/shared/projects
docker compose up -d

# Access from any client
# http://server-ip:4000/projects
```

## Exporting Data

Export all project data:

```bash
for project in /workspace/*/; do
  if [ -f "$project/.htmlgraph/htmlgraph.db" ]; then
    name=$(basename "$project")
    htmlgraph export -o "exports/$name.jsonl" --db "$project/.htmlgraph/htmlgraph.db"
  fi
done
```

## Next Steps

- [Dashboard User Guide](./dashboard.md) - Full dashboard features
- [Project Workspace Guide](./workspace.md) - Managing workspaces
- [Analytics Guide](./analytics.md) - Multi-project metrics
