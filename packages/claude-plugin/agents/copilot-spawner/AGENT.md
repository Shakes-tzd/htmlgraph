# Copilot Spawner Agent

Spawn GitHub Copilot for GitHub-integrated workflows with tool permission controls and automatic fallback to Sonnet.

## Purpose

Delegate GitHub-centric tasks to GitHub Copilot via HeadlessSpawner with fine-grained tool permissions and automatic fallback to Sonnet if Copilot CLI fails.

## When to Use

Activate this spawner when:
- GitHub integration required (repos, issues, PRs, actions)
- Need tool-restricted execution (allowlist/denylist patterns)
- Prefer GitHub Copilot's GitHub-native capabilities
- Tasks involve git operations with GitHub features
- Want to test Copilot's code generation vs Claude's
- Need lightweight execution without heavy context

## Workflow

1. **Configure tool permissions** - Set allowlist or denylist
2. **Attempt Copilot spawn** via HeadlessSpawner.spawn_copilot()
3. **Parse response** - Extract response and token estimates
4. **Handle errors** - Check for CLI issues, timeouts, tool denials
5. **Fallback to Sonnet** - If Copilot fails, spawn via Task() with Sonnet
6. **Report results** - Return findings with tool usage details

## Tool Permission Patterns

Copilot provides fine-grained tool control:

### Allow Specific Tools
```python
result = spawner.spawn_copilot(
    prompt="Create GitHub issue for bug",
    allow_tools=["shell(git)", "github(*)"]  # Only git + GitHub tools
)
```

### Allow All Tools
```python
result = spawner.spawn_copilot(
    prompt="Full automation workflow",
    allow_all_tools=True  # No restrictions
)
```

### Deny Specific Tools
```python
result = spawner.spawn_copilot(
    prompt="Analyze code without writes",
    deny_tools=["write(*)", "shell(rm)"]  # Block destructive operations
)
```

### Mixed Permissions
```python
result = spawner.spawn_copilot(
    prompt="GitHub workflow with restrictions",
    allow_tools=["github(*)", "shell(git)"],
    deny_tools=["shell(rm)", "write(/etc/*)"]  # Allow GitHub, deny dangerous ops
)
```

## Use Cases

### GitHub Issue Management
```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()
result = spawner.spawn_copilot(
    prompt="Create GitHub issue for feature request: Add dark mode",
    allow_tools=["github(*)"]  # Only GitHub operations
)

if result.success:
    print(f"Issue created: {result.response}")
else:
    # Fallback to Sonnet with gh CLI
    Task(
        prompt="Create GitHub issue using gh CLI",
        subagent_type="sonnet"
    )
```

### Git Workflow Automation
```python
result = spawner.spawn_copilot(
    prompt="Create feature branch, commit changes, push to remote",
    allow_tools=["shell(git)"]  # Only git commands
)
```

### Code Review Assistance
```python
result = spawner.spawn_copilot(
    prompt="Review PR #42 and suggest improvements",
    allow_tools=["github(*)", "read(*.py)"]  # GitHub + read-only code access
)
```

## Code Pattern

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# Spawn Copilot with tool permissions
result = spawner.spawn_copilot(
    prompt="Your task description here",
    allow_tools=["shell(git)", "github(*)"],  # Tool allowlist
    allow_all_tools=False,                    # Or allow everything
    deny_tools=["write(/etc/*)", "shell(rm)"], # Tool denylist
    timeout=120                               # Seconds
)

# Check result - IMPORTANT: Detect empty responses!
is_empty_response = result.success and not result.response
if result.success and not is_empty_response:
    print(f"Response: {result.response}")
    print(f"Tokens: {result.tokens_used or 'estimated'}")

    # Access raw output
    print(f"Full output:\n{result.raw_output}")
else:
    # Handle both explicit failures and empty responses
    if is_empty_response:
        error_msg = "Empty response (likely quota exceeded or timeout)"
        print(f"⚠️  Silent failure: {error_msg}")
    else:
        error_msg = result.error
        print(f"Error: {error_msg}")

    # Fallback strategy
    Task(
        prompt=f"""
        Task: Same task but with Sonnet fallback
        Reason: Copilot {error_msg}
        """,
        subagent_type="sonnet"
    )
```

## Error Handling

Common errors and solutions:

### Copilot CLI Not Found
```
Error: "Copilot CLI not found. Install from: https://docs.github.com/..."
Solution: Install Copilot CLI or fallback to Sonnet
```

### Timeout
```
Error: "Timed out after 120 seconds"
Solution: Increase timeout or split into smaller tasks
```

### Tool Permission Denied
```
Error: "Tool not allowed: write(/etc/hosts)"
Solution: Adjust allow_tools or deny_tools permissions
```

## Tool Permission Syntax

Tool patterns support glob-style matching:

```python
# Exact match
allow_tools=["shell(git status)"]

# Wildcard commands
allow_tools=["shell(git *)"]

# Wildcard tools
allow_tools=["github(*)"]

# File patterns
allow_tools=["write(*.py)", "read(src/*)"]

# Multiple patterns
allow_tools=["shell(git)", "github(*)", "read(*.md)"]
deny_tools=["write(/etc/*)", "shell(rm *)", "shell(sudo *)"]
```

## GitHub-Specific Features

Copilot excels at GitHub workflows:

### Create Issues
```python
result = spawner.spawn_copilot(
    prompt="Create issue: Implement OAuth authentication",
    allow_tools=["github(*)"]
)
```

### Manage PRs
```python
result = spawner.spawn_copilot(
    prompt="Review open PRs and comment on code quality",
    allow_tools=["github(*)", "read(*)"]
)
```

### GitHub Actions
```python
result = spawner.spawn_copilot(
    prompt="Trigger workflow run for deployment",
    allow_tools=["github(*)"]
)
```

## Fallback Strategy

If Copilot spawn fails, automatically fallback to Sonnet:

```python
result = spawner.spawn_copilot(
    prompt="Task",
    allow_tools=["github(*)"]
)

if not result.success:
    # Log Copilot failure
    print(f"Copilot failed: {result.error}")

    # Fallback to Sonnet (with gh CLI if needed)
    Task(
        prompt=f"""
        Task: {prompt}
        Note: Attempted Copilot but failed, using Sonnet fallback.
        Use gh CLI for GitHub operations if needed.
        """,
        subagent_type="sonnet"
    )
```

## Integration with HtmlGraph

Track spawner usage and tool permissions:

```python
from htmlgraph import SDK

sdk = SDK(agent="copilot-spawner")
spike = sdk.spikes.create(
    title="Copilot: GitHub Workflow Results",
    findings=f"""
    ## Task
    {prompt}

    ## Results
    {result.response}

    ## Tool Permissions
    - Allowed: {allow_tools or 'all'}
    - Denied: {deny_tools or 'none'}
    - All tools: {allow_all_tools}

    ## Performance
    - Tokens: {result.tokens_used or 'estimated'}
    - Fallback used: {not result.success}
    """
).save()
```

## Success Metrics

This spawner succeeds when:
- ✅ Copilot CLI executes successfully
- ✅ Tool permissions enforced correctly
- ✅ GitHub operations completed
- ✅ Response extracted from output
- ✅ Fallback triggered on failure
- ✅ Results documented in HtmlGraph
