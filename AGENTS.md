# HtmlGraph

Local-first observability and coordination platform for AI-assisted development.

## Architecture

| Layer | Role |
|-------|------|
| `.htmlgraph/*.html` | Canonical store — single source of truth |
| SQLite (`.htmlgraph/htmlgraph.db`) | Read index for queries and dashboard |
| Go binary (`htmlgraph`) | CLI + hook handler |

## For AI Agents

All CLI usage, safety rules, and best practices are delivered by the HtmlGraph plugin.
Run `htmlgraph help --compact` for the CLI reference.

## Dogfooding

This project uses HtmlGraph to develop itself. `.htmlgraph/` contains real work items — not demos.

## Agent Teams

When Claude Code's experimental [agent teams](https://code.claude.com/docs/en/agent-teams) feature is enabled (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, requires v2.1.32+), HtmlGraph automatically captures teammate activity: every TeammateIdle, TaskCreated, and TaskCompleted event records `teammate_name` and `team_name`, feature steps are prefixed with the teammate's name for attribution, and an optional quality gate can block task completion on build/test failures. See the "Enabling Agent Teams" section in CLAUDE.md for setup instructions.

## Temporal Awareness

A `UserPromptSubmit` hook injects the current local timestamp (with timezone) on every user prompt. Use it to reason about elapsed time between messages — detect stale context in long sessions, recognize when a session has been resumed after a gap, and avoid treating old references as fresh.
