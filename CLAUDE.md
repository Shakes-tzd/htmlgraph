@AGENTS.md

# HtmlGraph — Claude Code

Local-first observability and coordination platform for AI-assisted development.

---

## Build

**Always use `htmlgraph build`, never `go build` directly.**

```bash
htmlgraph build      # outputs to plugin/hooks/bin/htmlgraph (on your PATH)
plugin/build.sh      # equivalent
```

Running `go build -o htmlgraph ./cmd/htmlgraph/` puts the binary in CWD, not on your PATH.

---

## Quality Gates

```bash
go build ./... && go vet ./... && go test ./...
# Commit only when ALL pass
```

Use `/htmlgraph:code-quality-skill` for the complete pre-commit workflow.

---

## Deploy

```bash
./scripts/deploy-all.sh X.Y.Z --no-confirm   # full pipeline
```

Or `/htmlgraph:deploy X.Y.Z`. CLI binary and plugin are independent installs — the deploy script updates both. Never update one without the other.

---

## Dev Mode

```bash
htmlgraph claude --dev   # loads plugin from source via --plugin-dir
```

Dev mode uninstalls the marketplace plugin, clears cache, and launches with `claude --plugin-dir plugin/`. This ensures agents, skills, tools, and hooks all load from your local source — not stale marketplace copies. The marketplace plugin is reinstalled on exit.

**Why full removal is required:** Disabling a marketplace plugin only affects hooks. Agent definitions and skill content continue loading from `~/.claude/plugins/marketplaces/`, silently shadowing dev source changes.

---

## Plugin Source — Single Source of Truth

**Edit `plugin/`, never `.claude/` (auto-synced, changes are lost).**

| Edit here | Never here |
|-----------|-----------|
| `plugin/hooks/hooks.json` | `.claude/hooks/hooks.json` |
| `plugin/agents/` | `.claude/agents/` |
| `plugin/skills/` | `.claude/skills/` |
| `cmd/` / `internal/` for Go logic | `.claude/` anything |

See `.claude/rules/plugin-development.md` for full plugin structure reference.

---

## Orchestration

Delegate ALL operations except `Task()`, `AskUserQuestion()`, `TodoWrite()`, SDK operations.

Use `/htmlgraph:orchestrator-directives-skill` for delegation patterns and model selection.

---

## Quick Commands

| Task | Command |
|------|---------|
| View work | `htmlgraph snapshot --summary` |
| Run tests | `go test ./...` |
| Build binary | `htmlgraph build` |
| Deploy | `./scripts/deploy-all.sh VERSION --no-confirm` |
| Dashboard | `htmlgraph serve` |
| Status | `htmlgraph status` |

---

## Enabling Agent Teams

HtmlGraph integrates with Claude Code's experimental [agent teams](https://code.claude.com/docs/en/agent-teams) feature. When active, HtmlGraph captures teammate identity on events, attributes feature steps to individual teammates, and can optionally enforce quality gates on task completion.

**Setup:**

1. Set the environment variable: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
2. Requires Claude Code **v2.1.32** or later
3. The plugin works without this flag — hooks gracefully no-op when no team is active

**Optional quality gate** — to block task completion on build/test failures, add to `.htmlgraph/config.json`:

```json
{
  "block_task_completion_on_quality_failure": true
}
```

> **Warning:** Enabling the quality gate can strand teammates. Blocked teammates cannot be `/resume`d. When a gate blocks, stderr includes a recovery command: `htmlgraph feature complete <feature-id>`.

See `/htmlgraph:orchestrator-directives-skill` for decision criteria on when to use teams vs subagents.

---

## Dogfooding

This project uses HtmlGraph to develop itself. `.htmlgraph/` contains real work items — not demos.
