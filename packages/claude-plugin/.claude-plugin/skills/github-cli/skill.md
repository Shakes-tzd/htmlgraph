---
name: copilot
description: Use GitHub Copilot for Git operations, GitHub integration, and PR handling
when_to_use:
  - GitHub integration (repos, issues, PRs, actions)
  - Git operations and workflow automation
  - Code review and PR management
  - GitHub-native capabilities needed
skill_type: executable
---

# Copilot - GitHub Integration & Git Operations

<python>
import subprocess
import sys
from htmlgraph.orchestration.headless_spawner import HeadlessSpawner

# Get the task prompt from skill arguments
task_prompt = skill_args if 'skill_args' in dir() else ""

if not task_prompt:
    print("❌ ERROR: No task prompt provided")
    print("Usage: Skill(skill='.claude-plugin:copilot', args='Create PR for authentication feature')")
    sys.exit(1)

# Check if copilot CLI is available
cli_check = subprocess.run(
    ["which", "copilot"],
    capture_output=True,
    text=True
)

if cli_check.returncode != 0:
    print("⚠️ Copilot CLI not found on system")
    print("Install from: https://docs.github.com/en/copilot/using-github-copilot/using-github-copilot-in-the-command-line")
    print("\nFallback: Use gh CLI directly or Bash for git operations")
    print("Example: gh pr create --title '...' --body '...'")
    sys.exit(1)

# Copilot CLI is available - use spawner to execute
print("✅ Copilot CLI found, executing spawner...")
print(f"\nTask: {task_prompt[:100]}...")

try:
    spawner = HeadlessSpawner()
    result = spawner.spawn_copilot(
        prompt=task_prompt,
        allow_all_tools=True,
        track_in_htmlgraph=True,
        timeout=120
    )

    if result.success:
        print("\n✅ Copilot execution successful")
        if result.tokens_used:
            print(f"📊 Tokens used: {result.tokens_used}")
        print("\n" + "="*60)
        print("RESPONSE:")
        print("="*60)
        print(result.response)
        if result.tracked_events:
            print(f"\n📈 Tracked {len(result.tracked_events)} events in HtmlGraph")
    else:
        print(f"\n❌ Copilot execution failed: {result.error}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Error executing spawner: {type(e).__name__}: {e}")
    sys.exit(1)
</python>

Use GitHub Copilot CLI for Git operations and GitHub workflow automation.

## When to Use

- **GitHub Integration** - Work with repos, issues, PRs, actions
- **Git Operations** - Branch management, commits, pushes
- **PR Management** - Code reviews, PR creation, commenting
- **GitHub Actions** - Workflow triggers and monitoring
- **Git Workflows** - Automated multi-step git operations

## Requirements

The `gh` CLI (GitHub CLI) must be installed:

```bash
# macOS
brew install gh

# Ubuntu/Debian
sudo apt update && sudo apt install gh

# Windows
choco install gh

# Verify installation
gh --version

# Authenticate with GitHub
gh auth login
```

## How to Invoke

**PRIMARY: Use Skill() to invoke (tries gh CLI first):**

```python
# Recommended approach - uses gh CLI directly via agent spawner
Skill(skill=".claude-plugin:copilot", args="Create PR for authentication feature")
```

**What happens internally:**
1. Check if `gh` CLI is installed on your system
2. If **YES** → Execute gh commands directly: `gh pr create --title "..." --body "..."`
3. If **NO** → Return error message with installation instructions

**FALLBACK: Direct Bash execution (when Skill unavailable):**

```bash
# Manual fallback - direct gh CLI usage
if ! command -v gh &> /dev/null; then
    echo "ERROR: gh CLI not installed"
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Use gh for GitHub operations
gh pr list --state open
gh issue create --title "Bug report" --body "Description"
gh workflow run deploy.yml
```

**Note:** GitHub Copilot CLI integration is accessed via `gh` commands, not as a separate spawner.

## Example Use Cases

### 1. Create and Manage Pull Requests

```bash
# Create feature branch
git checkout -b feature/new-feature
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature

# Create PR using gh
gh pr create \
  --title "Add new feature" \
  --body "Implements X, Y, and Z" \
  --base main
```

### 2. Issue Management

```bash
# Create issue
gh issue create \
  --title "Bug: Authentication fails" \
  --body "Steps to reproduce: ..." \
  --label "bug,priority-high"

# List open issues
gh issue list --state open

# View issue details
gh issue view 42
```

### 3. Code Review

```bash
# List open PRs
gh pr list --state open

# View PR with comments
gh pr view 123 --comments

# Add review comment
gh pr comment 123 --body "LGTM! Great work on error handling."

# Request changes
gh pr review 123 --request-changes --body "Please add unit tests"
```

### 4. GitHub Actions

```bash
# List workflows
gh workflow list

# Trigger workflow
gh workflow run deploy.yml

# View workflow run
gh run list --limit 5
gh run view <RUN_ID> --log
```

### 5. Git Workflow Automation

```bash
# Complete feature workflow
git checkout -b feature/oauth
# ... make changes ...
git add .
git commit -m "feat: add OAuth 2.0 authentication"
git push -u origin feature/oauth
gh pr create --title "Add OAuth 2.0" --body "Implements OAuth flow"
```

## GitHub CLI Access

The `gh` CLI provides full access to GitHub operations. GitHub Copilot integration requires GitHub authentication.

## Common Operations

### Branch Management

```bash
# Create and switch to branch
git checkout -b feature/new-feature

# Push with upstream tracking
git push -u origin feature/new-feature

# Delete remote branch
git push origin --delete feature/old-feature
```

### Pull Request Workflow

```bash
# Create PR with template
gh pr create --fill  # Uses PR template

# Draft PR
gh pr create --draft

# Convert draft to ready
gh pr ready 123

# Merge PR
gh pr merge 123 --squash
```

### Issue Tracking

```bash
# Link PR to issue
gh pr create --title "Fix #42: Auth bug"

# Close issue with comment
gh issue close 42 --comment "Fixed in PR #50"

# Assign issue
gh issue edit 42 --add-assignee @username
```

## Fallback Strategy

The skill implements a two-level strategy:

### Level 1: gh CLI via Skill (Preferred)
```python
Skill(skill=".claude-plugin:copilot", args="Create PR for authentication feature")
# Attempts to use gh CLI via agent spawner
```

### Level 2: Direct Bash Execution (Fallback)
```bash
# If Skill unavailable, use Bash directly:
gh pr create --title "Add auth" --body "Implements JWT"
# Requires gh CLI installed
```

### Level 3: Manual Git Commands (Final Fallback)
```bash
# If gh CLI not available, use plain git:
git add .
git commit -m "Add authentication"
git push origin feature-branch
# Manual PR creation via GitHub web UI
```

**Error Handling:**
- Clear error messages if gh CLI not found
- Installation instructions provided
- Alternative approaches suggested

## Error Handling

### gh CLI Not Installed

```bash
Error: "gh: command not found"

Solution:
1. Install gh CLI: https://cli.github.com/
2. Or use Bash with git commands directly
3. Or manual PR creation via GitHub web UI
```

### Authentication Required

```bash
Error: "authentication required"

Solution:
gh auth login
# Follow prompts to authenticate with GitHub
```

### Permission Denied

```bash
Error: "Resource not accessible by personal access token"

Solution:
1. Check repository permissions
2. Regenerate token with required scopes
3. Run: gh auth refresh -h github.com -s repo
```

## Integration with HtmlGraph

Track Git operations in features:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Document PR creation
feature = sdk.features.create(
    title="OAuth Authentication Implementation",
    description="""
    Created via GitHub workflow:
    - Branch: feature/oauth
    - PR: #123
    - Status: In Review

    GitHub CLI commands used:
    - gh pr create
    - gh pr view
    - gh workflow run
    """
).save()
```

## When NOT to Use

Avoid GitHub Copilot for:
- Exploratory research (use Gemini skill)
- Code generation (use Claude or Codex)
- Simple git operations (use git directly)
- Non-GitHub projects (use git directly)

## Tips for Best Results

1. **Authenticate early** - Run `gh auth login` before starting work
2. **Use templates** - Create PR and issue templates for consistency
3. **Leverage gh aliases** - Create shortcuts for common commands
4. **Check permissions** - Ensure token has required scopes
5. **Document workflows** - Track operations in HtmlGraph

## GitHub CLI Aliases

Create shortcuts for common operations:

```bash
# Set up useful aliases
gh alias set prc 'pr create --fill'
gh alias set prv 'pr view --web'
gh alias set prl 'pr list --state open'

# Use aliases
gh prc  # Create PR using template
gh prv 123  # Open PR #123 in browser
gh prl  # List open PRs
```

## Advanced Features

### GitHub API Access

```bash
# Raw API calls
gh api repos/{owner}/{repo}/pulls

# Paginated results
gh api --paginate repos/{owner}/{repo}/issues

# POST request
gh api repos/{owner}/{repo}/issues \
  -f title="New issue" \
  -f body="Description"
```

### Workflow Automation

```bash
# Monitor workflow runs
gh run list --workflow=deploy.yml

# Download artifacts
gh run download <RUN_ID>

# Cancel workflow run
gh run cancel <RUN_ID>
```

## Related Skills

- `/gemini` - For exploring repository structure
- `/codex` - For generating code before committing
- `/code-quality` - For validating code before PR
- `/debugging-workflow` - For fixing CI/CD failures

## Common Workflows

### Feature Development

```bash
# 1. Create branch
git checkout -b feature/name

# 2. Develop and commit
# ... make changes ...
git add .
git commit -m "feat: description"

# 3. Push and create PR
git push -u origin feature/name
gh pr create --title "Feature name" --body "Description"

# 4. Monitor CI
gh pr checks

# 5. Merge after approval
gh pr merge --squash
```

### Bug Fix Workflow

```bash
# 1. Create issue
gh issue create --title "Bug: description" --label bug

# 2. Create fix branch
git checkout -b fix/issue-42

# 3. Fix and commit
git commit -m "fix: resolve #42"

# 4. Create PR linking issue
gh pr create --title "Fix #42: description"

# 5. Auto-close issue on merge
gh pr merge --squash
```

### Release Workflow

```bash
# 1. Create release branch
git checkout -b release/v1.0.0

# 2. Update version files
# ... version bumps ...

# 3. Create release PR
gh pr create --title "Release v1.0.0" --base main

# 4. After merge, create GitHub release
gh release create v1.0.0 \
  --title "Version 1.0.0" \
  --notes "Release notes here" \
  dist/*
```
