---
name: copilot
executable: agents/copilot-spawner.py
model: haiku
description: GitHub Copilot spawner - GitHub-integrated workflows and git operations
capabilities:
  - github_integration
  - git_operations
  - pr_handling
context_window: 100K tokens
cost: INCLUDED (GitHub Copilot subscription)
requires_cli: gh
---

# Copilot Spawner Agent

Spawn GitHub Copilot for GitHub-integrated workflows, git operations, and pull request management.

## Usage

```
Task(
    subagent_type="htmlgraph:copilot",
    prompt="Create a pull request with the recent changes and request review from the team",
    description="GitHub workflow"
)
```

## Capabilities

- **GitHub Integration**: Direct access to GitHub API via `gh` CLI
- **Git Operations**: Branch management, commits, pushes, merges
- **Pull Request Handling**: Create, review, merge PRs
- **Issue Management**: Create and manage issues
- **Workflow Automation**: GitHub Actions integration

## When to Use

- ✅ Git and GitHub operations
- ✅ Pull request creation and management
- ✅ Branch operations and merging
- ✅ GitHub API interactions
- ✅ CI/CD workflow automation

## Parameters

- `--prompt`: Task description for Copilot
- `--allow-tool`: Allow specific tool (can be specified multiple times)
- `--allow-all-tools`: Allow all GitHub tools
- `--deny-tool`: Deny specific tool (can be specified multiple times)
- `--timeout`: Max seconds to wait (default: 120)

## Requirements

- GitHub CLI installed: `brew install gh` (or package manager)
- GitHub authentication: `gh auth login`
- GitHub Copilot subscription active

## Event Tracking

All Copilot spawner invocations are automatically tracked in HtmlGraph:
- Delegation events with full context
- Execution duration and status
- GitHub operations performed
- Agent attribution (actual AI model, not wrapper)
- Tool usage tracking

## Tool Permissions

By default, Copilot has limited tool access for safety. You can:
- Allow specific tools: `--allow-tool git --allow-tool pr`
- Allow all tools: `--allow-all-tools`
- Deny specific tools: `--deny-tool push`

## Pricing

Usage is covered by your existing GitHub Copilot subscription.
