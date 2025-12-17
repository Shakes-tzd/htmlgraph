# /htmlgraph:help

Show available HtmlGraph commands.

## Usage

```
/htmlgraph:help
```

## Instructions for Claude

Present the following help text:

```markdown
## HtmlGraph Commands

### Session Management
- `/htmlgraph:start` - Start session, see status, choose what to work on
- `/htmlgraph:end` - End current session gracefully
- `/htmlgraph:status` - Quick status check

### Feature Management
- `/htmlgraph:feature-add [title]` - Add a new feature
- `/htmlgraph:feature-start <id>` - Start working on a feature
- `/htmlgraph:feature-complete [id]` - Mark feature as complete
- `/htmlgraph:feature-primary <id>` - Set primary feature for attribution

### Utilities
- `/htmlgraph:init` - Initialize HtmlGraph in project
- `/htmlgraph:serve [port]` - Start dashboard server
- `/htmlgraph:track <tool> <summary>` - Manually track activity

### CLI Commands
You can also use the CLI directly:
```bash
htmlgraph --help
htmlgraph status
htmlgraph feature list
htmlgraph session list
```

### Dashboard
View progress in browser:
```bash
htmlgraph serve
# Open http://localhost:8080
```
```
