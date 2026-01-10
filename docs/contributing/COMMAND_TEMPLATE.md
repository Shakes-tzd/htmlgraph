# Slash Command Template

<!-- Efficiency: SDK calls: 1, Bash calls: 0, Context: ~5% -->

This template provides a standardized pattern for creating efficient HtmlGraph slash commands.

---

## Command Structure

Every slash command should follow this structure:

```markdown
# /htmlgraph:command-name

Brief description of what this command does

## Usage

```
/htmlgraph:command-name [arg1] [--flag]
```

## Parameters

- `arg1` (required/optional): Description of argument
- `--flag` (optional): Description of flag

## Examples

```bash
/htmlgraph:command-name value1
```
Description of what this example does

## Instructions for Claude

This command uses the SDK's `method_name()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Single SDK call for data retrieval:**
   ```bash
   uv run htmlgraph command-name [args]
   ```

   **Context usage: <5%**

2. **Parse the output** to extract:
   - Key data point 1
   - Key data point 2
   - Key data point 3

3. **Present the summary** using the output template below

4. **Recommend next steps** based on results
```

### Output Format:

## [Command Result Title]

**Key Info 1:** {value1}
**Key Info 2:** {value2}

### Details
{detailed_info}

### What's Next?
{next_steps}
```
```

---

## Best Practices

### 1. **Minimize Tool Calls**

**❌ INEFFICIENT (Multiple CLI calls):**
```python
# Step 1: List features
htmlgraph feature list

# Step 2: Get status
htmlgraph status

# Step 3: Check sessions
htmlgraph session list

# Step 4: Parse and combine outputs
# Result: ~30% context usage, 3+ bash calls
```

**✅ EFFICIENT (Single SDK call):**
```python
# Single optimized call that returns structured data
result = sdk.get_session_start_info()

# Result: ~5% context usage, 1 bash call or direct SDK method
```

### 2. **Use SDK Methods Over CLI**

**Priority order:**
1. **Direct SDK method** (best) - e.g., `sdk.features.complete(id)`
2. **Optimized CLI command** (good) - e.g., `htmlgraph session start-info`
3. **Multiple CLI calls** (avoid) - Last resort only

### 3. **Return Structured Data**

Commands should return structured data that's easy to parse:

**✅ GOOD:**
```json
{
  "status": "completed",
  "feature_id": "feat-001",
  "title": "User Authentication",
  "progress": {"done": 5, "total": 10, "percentage": 50}
}
```

**❌ BAD:**
```text
Feature completed: feat-001
Title: User Authentication
Progress: 50% (5/10)
```

### 4. **Add Efficiency Metrics**

Every command file should include a metrics header:

```markdown
<!-- Efficiency: SDK calls: 1, Bash calls: 0, Context: ~5% -->
```

**Metrics explained:**
- **SDK calls**: Number of direct Python SDK method calls
- **Bash calls**: Number of subprocess/CLI invocations
- **Context**: Estimated LLM context usage percentage

**Target goals:**
- SDK calls: 1 (or 0 if using direct SDK method)
- Bash calls: 0-1
- Context: <10%

### 5. **Error Handling**

Always specify what to do when operations fail:

```python
# Check if initialized
if not sdk.is_initialized():
    print("Error: HtmlGraph not initialized. Run /htmlgraph:init first")
    return

# Validate input
if not feature_id:
    print("Error: No feature ID provided and no active features found")
    return

# Handle SDK errors
try:
    result = sdk.features.complete(feature_id)
except Exception as e:
    print(f"Error completing feature: {e}")
    return
```

### 6. **Consistent Output Format**

Use markdown formatting for readability:

```markdown
## [Section Title]

**Label:** value
**Another Label:** another value

### Subsection

- Bullet point 1
- Bullet point 2

### What's Next?

Recommend specific actions based on the result.
```

### 7. **Context-Aware Recommendations**

Commands should provide intelligent next steps:

```python
# After completing a feature
if pending_features:
    print(f"### What's Next?\n")
    print(f"Start next feature: {pending_features[0].title}")
    print(f"Or run `/htmlgraph:recommend` for recommendations")
elif bottlenecks:
    print(f"### What's Next?\n")
    print(f"Address {len(bottlenecks)} bottlenecks blocking progress")
else:
    print(f"### What's Next?\n")
    print(f"All features complete! Run `/htmlgraph:plan` to start new work")
```

---

## Command Pattern Examples

### Pattern 1: Single Data Retrieval

**Use case:** Getting project status, listing items

**Template:**
```python
# 1. Single SDK call
result = sdk.method_name()

# 2. Format output
print(format_result(result))

# 3. Suggest next action
print(suggest_next(result))
```

**Example:** `/htmlgraph:status`

### Pattern 2: Single Action

**Use case:** Creating, updating, or completing items

**Template:**
```python
# 1. Validate input
if not is_valid(args):
    print("Error: ...")
    return

# 2. Execute action
result = sdk.method_name(args)

# 3. Show confirmation
print(format_confirmation(result))

# 4. Suggest next action
print(suggest_next(result))
```

**Example:** `/htmlgraph:feature-complete`

### Pattern 3: Planning/Analytics

**Use case:** Strategic commands that need project context

**Template:**
```python
# 1. Get comprehensive context (single call)
context = sdk.get_analytics()

# 2. Execute action with context
result = sdk.method_name(args, context=context)

# 3. Show result with strategic insights
print(format_with_insights(result, context))

# 4. Recommend data-driven next steps
print(strategic_recommendations(result, context))
```

**Example:** `/htmlgraph:plan`, `/htmlgraph:recommend`

---

## Migration Guide

### Converting Inefficient Commands

**Before (4 CLI calls, ~30% context):**
```markdown
### Implementation:

1. **List features:**
   ```bash
   htmlgraph feature list --status in-progress
   ```

2. **Complete feature:**
   ```bash
   htmlgraph feature complete <id>
   ```

3. **Check status:**
   ```bash
   htmlgraph status
   ```

4. **List again:**
   ```bash
   htmlgraph feature list
   ```

5. **Parse and combine outputs**
```

**After (1 SDK call, ~5% context):**
```markdown
### Implementation:

1. **Complete feature and get status (single call):**
   ```python
   result = sdk.features.complete_with_status(feature_id)
   ```

   Returns: {
     "feature": {...},
     "project_status": {...},
     "next_features": [...]
   }

2. **Format and display**

3. **Recommend next steps**
```

### Common Patterns to Replace

| Inefficient Pattern | Efficient Alternative |
|-------------------|----------------------|
| `htmlgraph cmd1 && htmlgraph cmd2 && htmlgraph cmd3` | `sdk.combined_method()` or `htmlgraph optimized-cmd` |
| Parse text output from CLI | Use SDK method returning dict/object |
| List before and after action | Return updated state from action |
| Multiple queries for related data | Single method returning related data |

---

## Testing Commands

### Manual Testing

```bash
# Test in Claude Code CLI
/htmlgraph:command-name test-args

# Verify:
# - Output is well-formatted
# - Recommendations are relevant
# - Context usage is low (<10%)
# - No errors or exceptions
```

### Metrics Validation

**Check context usage:**
1. Run command and note the response length
2. Estimate context: response_tokens / 10000 * 100
3. Target: <10% for most commands

**Check tool calls:**
1. Count Bash invocations in command definition
2. Target: 0-1 bash calls
3. Prefer direct SDK methods over CLI

---

## Reference: Efficient Commands

Study these commands as examples of best practices:

1. **`/htmlgraph:start`** - Uses `session start-info` (1 call replaces 6)
2. **`/htmlgraph:plan`** - Uses `sdk.smart_plan()` (single SDK method)
3. **`/htmlgraph:recommend`** - Uses SDK analytics methods
4. **`/htmlgraph:spike`** - Uses `sdk.start_planning_spike()`

---

## Checklist for New Commands

- [ ] Efficiency metrics header added
- [ ] Uses SDK method or optimized CLI command
- [ ] Total tool calls ≤ 1
- [ ] Context usage < 10%
- [ ] Error handling specified
- [ ] Consistent output format
- [ ] Context-aware recommendations
- [ ] Examples provided
- [ ] Tested manually
- [ ] Documentation complete

---

## Questions?

See:
- **AGENTS.md** - SDK reference and examples
- **packages/claude-plugin/commands/** - Existing command implementations
- **src/python/htmlgraph/sdk.py** - Available SDK methods
