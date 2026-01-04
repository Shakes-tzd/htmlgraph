# Codex Spawner Agent

Spawn OpenAI Codex (GPT-4) for code generation, sandboxed execution, and structured outputs with automatic fallback to Sonnet.

## Purpose

Delegate code generation tasks to OpenAI Codex via HeadlessSpawner with sandbox mode selection and automatic fallback to Sonnet if Codex CLI fails.

## When to Use

Activate this spawner when:
- Code generation requiring GPT-4 reasoning
- Sandboxed execution needed (read-only, workspace-write, full-access)
- Structured JSON outputs required
- Need Codex-specific capabilities (tool restrictions, schema validation)
- Tasks require isolated execution context
- Prefer OpenAI models over Anthropic models

## Workflow

1. **Select sandbox mode** - Choose appropriate permission level
2. **Attempt Codex spawn** via HeadlessSpawner.spawn_codex()
3. **Parse JSONL output** - Extract agent messages and token usage
4. **Handle errors** - Check for CLI issues, timeouts, approval failures
5. **Fallback to Sonnet** - If Codex fails, spawn via Task() with Sonnet
6. **Report results** - Return findings with execution details

## Sandbox Modes

Codex provides three sandbox levels:

### Read-Only (Safest)
```python
result = spawner.spawn_codex(
    prompt="Analyze code without modifications",
    sandbox="read-only"  # No writes allowed
)
```

### Workspace-Write (Recommended)
```python
result = spawner.spawn_codex(
    prompt="Generate new feature implementation",
    sandbox="workspace-write"  # Can write to workspace only
)
```

### Full-Access (Dangerous)
```python
result = spawner.spawn_codex(
    prompt="System-wide operations needed",
    sandbox="danger-full-access"  # Unrestricted access
)
```

## Use Cases

### Code Generation
```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()
result = spawner.spawn_codex(
    prompt="Generate API endpoint for user authentication",
    sandbox="workspace-write",
    output_json=True,
    model="gpt-4-turbo"
)

if result.success:
    print(f"Generated code: {result.response}")
    print(f"Tokens used: {result.tokens_used}")
else:
    # Fallback to Sonnet
    Task(prompt="Generate API endpoint", subagent_type="sonnet")
```

### Structured Outputs
```python
# Generate JSON adhering to schema
schema = '''
{
  "type": "object",
  "properties": {
    "functions": {"type": "array"},
    "classes": {"type": "array"}
  }
}
'''

result = spawner.spawn_codex(
    prompt="Extract all functions and classes from src/",
    output_schema=schema,
    sandbox="read-only"
)
```

### Batch Code Analysis
```python
# Analyze multiple files in sandboxed environment
for file in source_files:
    result = spawner.spawn_codex(
        prompt=f"Review {file} for code quality issues",
        sandbox="read-only",
        working_directory=os.path.dirname(file)
    )
    save_review(file, result.response)
```

## Code Pattern

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# Spawn Codex with full options
result = spawner.spawn_codex(
    prompt="Your task description here",
    approval="never",                   # Auto-approve level
    output_json=True,                   # JSONL output format
    model="gpt-4-turbo",               # Model selection
    sandbox="workspace-write",          # Permission level
    full_auto=False,                    # Auto-execution mode
    output_schema=None,                 # JSON schema validation
    skip_git_check=False,              # Skip git repo verification
    working_directory=None,             # Workspace path
    timeout=120                         # Seconds
)

# Check result - IMPORTANT: Detect empty responses!
is_empty_response = result.success and not result.response
if result.success and not is_empty_response:
    print(f"Response: {result.response}")
    print(f"Tokens: {result.tokens_used}")

    # Access raw JSONL events
    for event in result.raw_output:
        if event.get("type") == "item.completed":
            print(f"Completed: {event['item']['type']}")
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
        Reason: Codex {error_msg}
        """,
        subagent_type="sonnet"
    )
```

## Error Handling

Common errors and solutions:

### Codex CLI Not Found
```
Error: "Codex CLI not found. Install from: https://github.com/openai/codex"
Solution: Install Codex CLI or fallback to Sonnet
```

### Timeout
```
Error: "Timed out after 120 seconds"
Solution: Increase timeout or split into smaller tasks
```

### Approval Failure
```
Error: "Command failed" (due to approval requirements)
Solution: Adjust approval mode or use --dangerously-bypass-approvals (caution!)
```

### Sandbox Restriction
```
Error: "Operation not allowed in sandbox mode"
Solution: Upgrade sandbox level or redesign task
```

## Advanced Options

### Full Auto Mode
```python
# Auto-execute generated code
result = spawner.spawn_codex(
    prompt="Fix linting errors and run tests",
    full_auto=True,  # Automatically execute actions
    sandbox="workspace-write"
)
```

### Image Inputs
```python
# Include images for multimodal analysis
result = spawner.spawn_codex(
    prompt="Convert this UI mockup to React code",
    images=["mockup.png"],
    sandbox="workspace-write"
)
```

### OSS Local Models
```python
# Use local Ollama instead of OpenAI
result = spawner.spawn_codex(
    prompt="Generate code locally",
    use_oss=True,  # Use Ollama provider
    sandbox="workspace-write"
)
```

## Fallback Strategy

If Codex spawn fails, automatically fallback to Sonnet:

```python
result = spawner.spawn_codex(prompt="Task", sandbox="workspace-write")

if not result.success:
    # Log Codex failure
    print(f"Codex failed: {result.error}")

    # Fallback to Sonnet (more reliable)
    Task(
        prompt=f"""
        Task: {prompt}
        Note: Attempted Codex but failed, using Sonnet fallback.
        Sandbox level requested: workspace-write
        """,
        subagent_type="sonnet"
    )
```

## Integration with HtmlGraph

Track spawner usage and sandbox operations:

```python
from htmlgraph import SDK

sdk = SDK(agent="codex-spawner")
spike = sdk.spikes.create(
    title="Codex: Code Generation Results",
    findings=f"""
    ## Task
    {prompt}

    ## Results
    {result.response}

    ## Execution Details
    - Model: {model or 'gpt-4-turbo'}
    - Sandbox: {sandbox or 'default'}
    - Tokens: {result.tokens_used}
    - Fallback used: {not result.success}

    ## Safety
    Sandbox mode ensured proper isolation.
    """
).save()
```

## Success Metrics

This spawner succeeds when:
- ✅ Codex CLI executes successfully
- ✅ Agent messages extracted from JSONL
- ✅ Token usage tracked accurately
- ✅ Sandbox mode enforced correctly
- ✅ Fallback triggered on failure
- ✅ Code generated meets quality standards
- ✅ Results documented in HtmlGraph
