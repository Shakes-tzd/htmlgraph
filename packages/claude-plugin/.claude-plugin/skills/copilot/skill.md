---
name: copilot
description: GitHub CLI (gh) operations - Create PRs, manage issues, work with GitHub repositories
when_to_use:
  - Creating pull requests and issues
  - Managing GitHub repositories
  - Git operations via gh CLI
  - GitHub authentication and configuration
  - Repository cloning and forking
skill_type: executable
---

# GitHub CLI (gh) Operations

⚠️ **IMPORTANT: This skill is DOCUMENTATION ONLY - it does NOT execute code.**

This skill teaches you HOW to use the GitHub CLI (`gh`). To actually execute commands, use the **Bash tool** with the examples shown in the "EXECUTION" section below.

## What is GitHub CLI (gh)?

GitHub CLI (`gh`) is a command-line tool for GitHub operations:
- **Pull Requests** - Create, view, merge, and manage PRs
- **Issues** - Create, list, and manage GitHub issues
- **Repositories** - Clone, fork, and manage repos
- **Authentication** - Manage GitHub credentials and tokens
- **Workflows** - Trigger and view GitHub Actions

Works in your terminal with the `gh` command.

## Skill vs Execution Model

**CRITICAL DISTINCTION:**

| What | Description |
|------|-------------|
| **This Skill** | Documentation teaching HOW to use `gh` CLI |
| **Bash Tool** | ACTUAL execution of `gh` commands |

**Workflow:**
1. Read this skill to learn `gh` CLI syntax and options
2. Use **Bash tool** to execute the actual commands
3. Use SDK to track results in HtmlGraph

## Installation

```bash
# Install GitHub CLI
# macOS
brew install gh

# Ubuntu/Debian
sudo apt update && sudo apt install gh

# Windows
choco install gh

# Authenticate with GitHub
gh auth login

# Verify installation
gh --version
```

## EXECUTION - Real Commands to Use in Bash Tool

**⚠️ To actually execute GitHub operations, use these commands via the Bash tool:**

### Create Pull Request
```bash
# Basic PR creation
gh pr create --title "Feature: Add authentication" --body "Implements JWT auth"

# PR with multiple options
gh pr create --title "Fix bug" --body "Description" --base main --head feature-branch

# Interactive PR creation
gh pr create --web
```

### Manage Issues
```bash
# Create issue
gh issue create --title "Bug: Login fails" --body "Steps to reproduce..."

# List issues
gh issue list --state open

# View issue
gh issue view 123
```

### Repository Operations
```bash
# Clone repository
gh repo clone owner/repo

# Fork repository
gh repo fork owner/repo --clone

# Create repository
gh repo create my-new-repo --public
```

### Git Operations via gh
```bash
# Check status and create commit
git add . && git commit -m "feat: add new feature"

# Push and create PR in one command
git push && gh pr create --fill

# View PR status
gh pr status
```

## How to Use This Skill

**STEP 1: Read this skill to learn gh CLI syntax**
```python
# This loads the documentation (this file)
Skill(skill=".claude-plugin:copilot")
```

**STEP 2: Execute commands via Bash tool**
```python
# This ACTUALLY creates a PR
Bash("gh pr create --title 'Feature' --body 'Description'")

# This ACTUALLY creates an issue
Bash("gh issue create --title 'Bug' --body 'Details'")

# This ACTUALLY clones a repo
Bash("gh repo clone user/repo")
```

**What this skill does:**
- ✅ Provides documentation and examples
- ✅ Teaches gh CLI syntax and options
- ✅ Shows common workflows and patterns
- ❌ Does NOT execute commands
- ❌ Does NOT create PRs or issues
- ❌ Does NOT run git operations

**To execute: Use Bash tool with the commands shown in "EXECUTION" section.**

## Example Use Cases (Execute via Bash)

### 1. Pull Request Workflows

```bash
# Create PR after committing changes
Bash("gh pr create --title 'Add feature X' --body 'Implements X with tests'")

# Create draft PR
Bash("gh pr create --draft --title 'WIP: Feature Y'")

# List your PRs
Bash("gh pr list --author @me")

# Merge PR
Bash("gh pr merge 123 --squash")
```

### 2. Issue Management

```bash
# Create bug report
Bash("gh issue create --title 'Bug: Auth fails' --body 'Steps: 1. Login 2. Error'")

# List open issues
Bash("gh issue list --state open")

# Close issue
Bash("gh issue close 456")
```

### 3. Repository Operations

```bash
# Clone repo
Bash("gh repo clone anthropics/claude-code")

# Fork and clone
Bash("gh repo fork user/repo --clone")

# View repo details
Bash("gh repo view")
```

### 4. Commit and Push Workflows

```bash
# Commit all changes and create PR
Bash("git add . && git commit -m 'feat: new feature' && git push && gh pr create --fill")

# Amend last commit and force push
Bash("git commit --amend --no-edit && git push --force-with-lease")

# Check PR status
Bash("gh pr status")
```

### 5. GitHub Actions

```bash
# List workflow runs
Bash("gh run list")

# View specific run
Bash("gh run view 123")

# Re-run failed jobs
Bash("gh run rerun 123 --failed")
```

## Use Cases

- **Pull Requests** - Create, manage, and merge PRs via command line
- **Issues** - Create and track GitHub issues efficiently
- **Repository Management** - Clone, fork, and configure repos
- **Authentication** - Manage GitHub credentials and tokens
- **CI/CD** - Trigger and monitor GitHub Actions workflows
- **Code Review** - View and comment on PRs from terminal

## Requirements

- GitHub account
- `gh` CLI installed
- Authenticated via `gh auth login`
- Git configured (for git operations)

## Integration with HtmlGraph

Track GitHub operations in features:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Document PR creation
feature = sdk.features.create(
    title="Authentication Feature PR",
    description="""
    Created PR via gh CLI:
    - Title: Add JWT authentication
    - Branch: feature/jwt-auth
    - Status: Ready for review

    Command used:
    gh pr create --title "Add JWT auth" --body "Full implementation with tests"
    """
).save()
```

## When to Use

✅ **Use GitHub CLI (gh) for:**
- Creating and managing pull requests
- Creating and tracking issues
- Cloning and forking repositories
- GitHub authentication
- Viewing and managing workflows
- Command-line GitHub operations

❌ **Don't use gh CLI for:**
- Code generation (use Task() delegation or direct implementation)
- Exploring codebases (use `/gemini` skill instead)
- Complex git operations (use git commands directly)
- Local file operations (use standard bash/python)

## Tips for Best Results

1. **Use --fill flag** - Auto-populate PR details from commits: `gh pr create --fill`
2. **Check status first** - Run `gh pr status` or `gh issue list` before creating new items
3. **Use templates** - Leverage repository issue/PR templates when available
4. **Authenticate early** - Run `gh auth login` at start of session
5. **Combine with git** - Chain git and gh commands: `git push && gh pr create`
6. **Use --web flag** - Open operations in browser when needed: `gh pr create --web`

## Common Patterns (Execute via Bash)

### Pattern 1: Feature Development Workflow

```bash
# 1. Create feature branch
Bash("git checkout -b feature/new-feature")

# 2. Make changes, commit
Bash("git add . && git commit -m 'feat: implement feature'")

# 3. Push and create PR
Bash("git push -u origin feature/new-feature && gh pr create --fill")
```

### Pattern 2: Bug Fix Workflow

```bash
# 1. Create issue for bug
Bash("gh issue create --title 'Bug: Description' --body 'Steps to reproduce'")

# 2. Create branch from issue
Bash("git checkout -b fix/issue-123")

# 3. Fix, commit, and create PR
Bash("git add . && git commit -m 'fix: resolve issue #123' && gh pr create --fill")
```

### Pattern 3: Quick PR Creation

```bash
# 1. Commit all changes
Bash("git add . && git commit -m 'feat: quick feature'")

# 2. Push and create PR in one command
Bash("git push && gh pr create --title 'Quick Feature' --body 'Description'")
```

## Limitations

- Requires GitHub account and authentication
- Internet connection required for GitHub API
- Rate limits apply to API calls
- Some operations require repository permissions
- Cannot execute local git operations (use git directly)

## Related Skills

- `/gemini` - For exploring repository structure and large codebases
- `/codex` - For code generation and implementation
- `/code-quality` - For validating code quality before creating PR
- Git commands - For local repository operations (use Bash directly)

## When NOT to Use

Avoid GitHub CLI for:
- Code generation (use Task() delegation)
- Exploratory research (use `/gemini` skill)
- Local file operations (use standard bash commands)
- Operations not related to GitHub (use appropriate tool)

## Error Handling (Use Bash for Diagnostics)

### GitHub CLI Not Installed

```bash
Error: "gh: command not found"

Solution (via Bash):
# macOS
Bash("brew install gh")

# Verify
Bash("gh --version")
```

### Authentication Required

```bash
Error: "authentication required"

Solution (via Bash):
Bash("gh auth login")
# Follow prompts in terminal
```

### Permission Denied

```bash
Error: "permission denied to repository"

Solution (via Bash):
# Check authentication status
Bash("gh auth status")

# Re-authenticate if needed
Bash("gh auth login --force")
```

## Advanced Usage (Execute via Bash)

### PR with Reviewers and Labels

```bash
Bash("gh pr create --title 'Feature' --body 'Desc' --reviewer user1,user2 --label bug,enhancement")
```

### Create Issue from Template

```bash
Bash("gh issue create --template bug_report.md")
```

### Batch Operations

```bash
# Close multiple issues
Bash("gh issue list --state open --json number --jq '.[].number' | xargs -I {} gh issue close {}")
```

### Integration with Git Workflows

```bash
# Rebase and force push
Bash("git rebase main && git push --force-with-lease && gh pr ready")

# Squash commits and update PR
Bash("git rebase -i HEAD~3 && git push --force-with-lease")
```

## Key Features

| Feature | GitHub CLI (gh) | Description |
|---------|-----------------|-------------|
| Pull Requests | ✅ | Create, merge, review, comment |
| Issues | ✅ | Create, list, close, assign |
| Repositories | ✅ | Clone, fork, create, view |
| Authentication | ✅ | Login, status, token management |
| GitHub Actions | ✅ | List, view, re-run workflows |
| API Access | ✅ | Direct GitHub API calls via `gh api` |
