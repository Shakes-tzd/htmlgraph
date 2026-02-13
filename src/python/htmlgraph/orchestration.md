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
