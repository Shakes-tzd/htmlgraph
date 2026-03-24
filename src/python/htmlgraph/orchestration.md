# Orchestration Rules

## What You Execute Directly
- `Bash` — simple CLI commands (git, build, deploy)
- `AskUserQuestion` — clarify requirements
- `Task` — delegate work to subagents

## What You NEVER Execute Directly
- `Read`, `Grep`, `Glob` — delegate to htmlgraph:researcher
- `Edit`, `Write` — delegate to htmlgraph:haiku-coder, sonnet-coder, or opus-coder
- `NotebookEdit` — delegate to a coder agent

## Parallel Delegation
Launch multiple independent Task() calls in a single message for maximum throughput.

## Error Handling
If a subagent fails, escalate the model (haiku → sonnet → opus) rather than retrying at the same level.

## Quality Gates
- After UI changes → delegate to `htmlgraph:ui-reviewer` for visual validation
- Before merging significant work → consider `htmlgraph:roborev` for code review
- Before committing → `uv run ruff check --fix && uv run ruff format && uv run mypy src/ && uv run pytest`

## Available Agents
| Agent | Purpose |
|-------|---------|
| htmlgraph:researcher | Exploration, documentation research |
| htmlgraph:haiku-coder | Quick fixes, 1-2 files |
| htmlgraph:sonnet-coder | Features, 3-8 files (DEFAULT) |
| htmlgraph:opus-coder | Architecture, 10+ files |
| htmlgraph:debugger | Error investigation |
| htmlgraph:test-runner | Testing, quality gates |
| htmlgraph:ui-reviewer | Visual QA via chrome-devtools |
| htmlgraph:roborev | Automated code review |
