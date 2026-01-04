# Gemini Spawner Agent

Spawn Google Gemini 2.0-Flash for exploratory work, batch operations, and multimodal tasks with FREE tier optimization.

## Purpose

Delegate work to Google Gemini via HeadlessSpawner with automatic fallback to Haiku if Gemini CLI fails. Optimized for cost efficiency using Gemini's FREE tier (2M tokens/minute).

## When to Use

Activate this spawner when:
- Exploratory research requiring large context windows
- Batch operations over many files
- Multimodal tasks (image analysis, document processing)
- Cost-sensitive workflows (Gemini FREE tier vs paid alternatives)
- Need fast iteration cycles with high token throughput
- Tasks not requiring Claude's deep reasoning

## Workflow

1. **Attempt Gemini spawn** via HeadlessSpawner.spawn_gemini()
2. **Parse result** - Extract response and token usage
3. **Handle errors** - Check for CLI issues, timeouts, JSON parsing
4. **Fallback to Haiku** - If Gemini fails, spawn via Task() with Haiku
5. **Report results** - Return findings with cost analysis

## Use Cases

### Exploratory Research
```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()
result = spawner.spawn_gemini(
    prompt="Search codebase for all auth patterns and summarize",
    include_directories=["src/", "tests/"],
    model="gemini-2.0-flash"
)

if result.success:
    print(f"Found patterns: {result.response}")
    print(f"Tokens: {result.tokens_used} (FREE tier)")
else:
    # Fallback to Haiku via Task()
    Task(prompt="Search codebase for all auth patterns", subagent_type="haiku")
```

### Batch File Analysis
```python
# Process many files in parallel
for file in files:
    result = spawner.spawn_gemini(
        prompt=f"Analyze {file} for security vulnerabilities",
        include_directories=[os.path.dirname(file)]
    )
    save_report(file, result.response)
```

### Multimodal Processing
```python
# Gemini can process images, PDFs, documents
result = spawner.spawn_gemini(
    prompt="Extract all text and tables from this diagram",
    include_directories=["docs/diagrams/"]
)
```

## Code Pattern

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# Spawn Gemini with JSON output
result = spawner.spawn_gemini(
    prompt="Your task description here",
    output_format="json",              # or "stream-json"
    model="gemini-2.0-flash",          # FREE tier model
    include_directories=["src/"],      # Context directories
    timeout=120                        # Seconds
)

# Check result - IMPORTANT: Detect empty responses!
is_empty_response = result.success and not result.response
if result.success and not is_empty_response:
    print(f"Response: {result.response}")
    print(f"Tokens: {result.tokens_used}")

    # Access raw output for stats
    stats = result.raw_output.get("stats", {})
    models_used = stats.get("models", {})
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
        Task: Same task but with Haiku fallback
        Reason: Gemini {error_msg}
        """,
        subagent_type="haiku"
    )
```

## Error Handling

Common errors and solutions:

### Gemini CLI Not Found
```
Error: "Gemini CLI not found. Ensure 'gemini' is installed and in PATH."
Solution: Install Gemini CLI or fallback to Haiku
```

### Timeout
```
Error: "Gemini CLI timed out after 120 seconds"
Solution: Increase timeout or split into smaller tasks
```

### JSON Parse Error
```
Error: "Failed to parse JSON output"
Solution: Check output_format parameter, verify CLI response
```

## FREE Tier Optimization

Gemini 2.0-Flash provides:
- **2M tokens per minute** (FREE)
- **1M token context window**
- **Multimodal capabilities** (images, PDFs, audio)
- **Fast inference** (sub-second latency)

**Cost comparison**:
- Gemini 2.0-Flash: **FREE** (rate limited)
- Claude Haiku: **$0.25/M input, $1.25/M output**
- Claude Sonnet: **$3/M input, $15/M output**

Use Gemini for high-volume exploratory work to minimize costs.

## Fallback Strategy

If Gemini spawn fails, automatically fallback to Haiku:

```python
result = spawner.spawn_gemini(prompt="Task")

if not result.success:
    # Log Gemini failure
    print(f"Gemini failed: {result.error}")

    # Fallback to Haiku (cheaper than Sonnet)
    Task(
        prompt=f"""
        Task: {prompt}
        Note: Attempted Gemini but failed, using Haiku fallback.
        """,
        subagent_type="haiku"
    )
```

## Integration with HtmlGraph

Track spawner usage for cost analysis:

```python
from htmlgraph import SDK

sdk = SDK(agent="gemini-spawner")
spike = sdk.spikes.create(
    title="Gemini: Batch Analysis Results",
    findings=f"""
    ## Task
    {prompt}

    ## Results
    {result.response}

    ## Performance
    - Model: gemini-2.0-flash
    - Tokens: {result.tokens_used}
    - Cost: FREE tier
    - Fallback used: {not result.success}
    """
).save()
```

## Success Metrics

This spawner succeeds when:
- ✅ Gemini CLI executes successfully
- ✅ Response parsed from JSON output
- ✅ Token usage tracked accurately
- ✅ Fallback triggered on failure
- ✅ Cost savings realized (FREE vs paid)
- ✅ Results documented in HtmlGraph
