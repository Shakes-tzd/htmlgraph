# /htmlgraph:init

Initialize HtmlGraph in a project.

## Usage

```
/htmlgraph:init
```

## Instructions for Claude

### Check if already initialized:
```bash
ls -la .htmlgraph 2>/dev/null || echo "Not initialized"
```

### If not initialized:
```bash
htmlgraph init
```

### After initialization:
```bash
# Show what was created
ls -la .htmlgraph/
htmlgraph status
```

Present summary:
```markdown
## HtmlGraph Initialized

Created `.htmlgraph/` directory with:
- `features/` - Feature HTML files
- `sessions/` - Session HTML files
- `bugs/` - Bug tracking (optional)

### Next Steps
1. Add features: `htmlgraph feature add "Feature title"`
2. Start working: `htmlgraph feature start <id>`
3. View dashboard: `htmlgraph serve`

### Dashboard
Open `index.html` in a browser or run:
```bash
htmlgraph serve
# Open http://localhost:8080
```
```
