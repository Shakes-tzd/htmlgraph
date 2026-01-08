# Standardized Task() Prompt Template with SDK Logging

## Purpose

This template ensures that all delegated tasks via `Task()` properly log their findings back to the parent event, enabling complete parent-child event tracing.

When you use this template:
1. Task() creates a parent event in the orchestrator context
2. Subagent executes the delegated work
3. Subagent uses SDK to create spike(s) with findings
4. SubagentStop hook updates parent event with completion status and spike count
5. Dashboard shows complete parent-child event trace

## Basic Template

Use this template for all `Task()` delegations:

```python
Task(
    prompt="""
[Your implementation instructions here]

🔴 CRITICAL - Report Activity to HtmlGraph:

At the end of your work, capture findings with this SDK code:

```python
from htmlgraph import SDK
import os

# Initialize SDK with your agent type
sdk = SDK(agent="<AGENT_TYPE>")

# Get parent event reference if available
parent_event_id = os.environ.get("HTMLGRAPH_PARENT_EVENT")

# Create spike with your findings
spike = sdk.spikes.create("<SPIKE_TITLE>") \\
    .set_findings(f'''
## Your Findings Title

[Your detailed findings and analysis here]

## Summary
- Key finding 1
- Key finding 2
- Key finding 3

## References
- Source 1
- Source 2
''') \\
    .save()

# Log completion
print(f"✅ Task complete")
print(f"📊 Findings: {spike.id}")
if parent_event_id:
    print(f"👤 Parent event: {parent_event_id}")
```
    """
)
```

## Complete Examples by Agent Type

### Gemini Spawner Example

```python
Task(
    prompt="""
Analyze the given system architecture and provide insights on:
1. Current design patterns
2. Potential bottlenecks
3. Improvement recommendations

🔴 CRITICAL - Report Activity to HtmlGraph:

At the end of your work, capture findings with:

```python
from htmlgraph import SDK
import os

sdk = SDK(agent="gemini-spawner")
parent_event_id = os.environ.get("HTMLGRAPH_PARENT_EVENT")

spike = sdk.spikes.create("Architecture Analysis - Gemini") \\
    .set_findings(f'''
## System Architecture Analysis

### Design Patterns Identified
- Pattern 1: Description
- Pattern 2: Description

### Performance Bottlenecks
1. Bottleneck A at [location]
2. Bottleneck B at [location]

### Improvement Recommendations
1. Recommendation 1 - Impact: [high/medium/low]
2. Recommendation 2 - Impact: [high/medium/low]
3. Recommendation 3 - Impact: [high/medium/low]

### Implementation Priority
1. Quick wins (< 1 day)
2. Medium effort (1-3 days)
3. Long-term improvements

**Parent Event:** {parent_event_id}
''') \\
    .save()

print(f"✅ Architecture analysis complete")
print(f"📊 Analysis spike: {spike.id}")
if parent_event_id:
    print(f"👤 Linked to parent: {parent_event_id}")
```
    """,
    subagent_type="gemini-spawner"
)
```

### Researcher Agent Example

```python
Task(
    prompt="""
Research and compile information about [topic]:
1. Background and context
2. Current state of the field
3. Recent developments
4. Expert opinions and findings

🔴 CRITICAL - Report Activity to HtmlGraph:

```python
from htmlgraph import SDK
import os

sdk = SDK(agent="researcher")
parent_event_id = os.environ.get("HTMLGRAPH_PARENT_EVENT")

spike = sdk.spikes.create("Research: [Topic Name]") \\
    .set_findings(f'''
## Research Findings: [Topic]

### Background & Context
[Your research here]

### Current State
[Current state analysis]

### Recent Developments (2024-2025)
[Recent developments]

### Expert Perspectives
[Expert opinions found]

### Sources
- [Source 1](url)
- [Source 2](url)
- [Source 3](url)

### Key Takeaways
1. Finding 1
2. Finding 2
3. Finding 3

**Parent Event:** {parent_event_id}
**Research Conducted:** {datetime.now().isoformat()}
''') \\
    .save()

print(f"✅ Research complete: {spike.id}")
if parent_event_id:
    print(f"👤 Parent task: {parent_event_id}")
```
    """
)
```

### Debugger Agent Example

```python
Task(
    prompt="""
Debug the reported issue and provide:
1. Root cause analysis
2. Reproduction steps
3. Solution with code examples
4. Prevention strategies

🔴 CRITICAL - Report Activity to HtmlGraph:

```python
from htmlgraph import SDK
import os

sdk = SDK(agent="debugger")
parent_event_id = os.environ.get("HTMLGRAPH_PARENT_EVENT")

spike = sdk.spikes.create("Debug Report: [Issue Name]") \\
    .set_findings(f'''
## Debugging Report

### Issue Description
[Describe the issue]

### Root Cause Analysis
[Analysis of root cause]

### Reproduction Steps
1. Step 1
2. Step 2
3. Step 3

### Solution
```python
# Code fix here
```

### Testing
- Test 1: [what was tested]
- Test 2: [what was tested]

### Prevention
- Preventive measure 1
- Preventive measure 2

**Parent Event:** {parent_event_id}
**Issue Fixed:** [yes/no]
''') \\
    .save()

print(f"✅ Debug analysis complete: {spike.id}")
if parent_event_id:
    print(f"👤 Linked to: {parent_event_id}")
```
    """
)
```

## SDK Integration Points

### Event Environment Variables

These variables are automatically exported when a Task() creates a parent event:

```python
import os

# Parent event ID - use to link your findings back
parent_event_id = os.environ.get("HTMLGRAPH_PARENT_EVENT")

# Subagent type - for logging what type of agent you are
subagent_type = os.environ.get("HTMLGRAPH_SUBAGENT_TYPE")

# Session ID - for context about the session
session_id = os.environ.get("HTMLGRAPH_SESSION_ID")
```

### Spike Creation Pattern

Standard pattern for all agent types:

```python
from htmlgraph import SDK

# 1. Initialize SDK with agent type
sdk = SDK(agent="your-agent-type")

# 2. Create spike with title matching your findings
spike = sdk.spikes.create("Your Title Here")

# 3. Set findings with detailed content
spike.set_findings("""
[Your detailed findings]
""")

# 4. Save and get ID
saved_spike = spike.save()

# 5. Log completion
print(f"Created spike: {saved_spike.id}")
```

## Best Practices

### 1. Meaningful Titles

```python
# Good
spike = sdk.spikes.create("Performance Analysis: Database Query Optimization")

# Bad
spike = sdk.spikes.create("Analysis")
```

### 2. Structured Findings

```python
findings = """
## Problem Statement
[Clear description of the problem]

## Analysis Methodology
[How you approached the problem]

## Key Findings
1. Finding 1 with supporting evidence
2. Finding 2 with supporting evidence
3. Finding 3 with supporting evidence

## Recommendations
[Specific, actionable recommendations]

## Next Steps
[What should be done next]
"""

spike.set_findings(findings).save()
```

### 3. Always Reference Parent Event

```python
parent_event_id = os.environ.get("HTMLGRAPH_PARENT_EVENT")

findings = f"""
[Your findings]

---
**Linked to parent task:** {parent_event_id}
**Analysis timestamp:** {datetime.now().isoformat()}
"""

spike.set_findings(findings).save()
```

### 4. Multiple Spikes if Needed

```python
sdk = SDK(agent="gemini-spawner")

# Create spike 1: Analysis
spike1 = sdk.spikes.create("Architecture Analysis") \\
    .set_findings("[Analysis findings]") \\
    .save()

# Create spike 2: Implementation Plan
spike2 = sdk.spikes.create("Implementation Plan") \\
    .set_findings("[Implementation plan]") \\
    .save()

# Create spike 3: Risk Assessment
spike3 = sdk.spikes.create("Risk Assessment") \\
    .set_findings("[Risk assessment]") \\
    .save()

print(f"Created {3} spikes for comprehensive analysis")
```

## Error Handling

```python
from htmlgraph import SDK
import os

try:
    sdk = SDK(agent="your-agent")
    parent_event_id = os.environ.get("HTMLGRAPH_PARENT_EVENT")

    spike = sdk.spikes.create("Your Title") \\
        .set_findings("""[Your findings]""") \\
        .save()

    print(f"✅ Success: {spike.id}")

except ImportError:
    print("⚠️  HtmlGraph SDK not available")
    # Continue with work even if SDK not available
except Exception as e:
    print(f"⚠️  Could not create spike: {e}")
    # Graceful degradation
```

## Event Trace Output

When using this template, you'll see parent-child event traces:

```
Dashboard → Activity → Event Traces
├─ evt-abc123 (Parent Task)
│  ├─ Status: completed
│  ├─ Subagent: gemini-spawner
│  ├─ Duration: 287 seconds
│  ├─ Child Spikes: 2
│  └─ Child Events:
│     └─ subevt-xyz789 (Subagent Completion)
│        ├─ Status: completed
│        └─ Timestamp: 2025-01-08 16:42:01
```

## Testing Your Template

To verify your Task() and SDK integration works:

```bash
# 1. Check that parent event is created
sqlite3 .htmlgraph/index.sqlite \
  "SELECT event_id, status, subagent_type FROM agent_events \
   WHERE event_type='task_delegation' ORDER BY timestamp DESC LIMIT 1;"

# 2. Check that spike was created
sqlite3 .htmlgraph/index.sqlite \
  "SELECT id, title FROM features WHERE type='spike' \
   ORDER BY created_at DESC LIMIT 1;"

# 3. Check parent event was updated with spike count
sqlite3 .htmlgraph/index.sqlite \
  "SELECT status, child_spike_count FROM agent_events \
   WHERE event_type='task_delegation' \
   ORDER BY timestamp DESC LIMIT 1;"

# 4. Query event trace via API
curl http://localhost:8000/api/event-traces
```

## Troubleshooting

### Parent event not created

**Problem:** Task() called but parent event missing

**Solution:**
1. Verify PreToolUse hook is running: `claude --debug Task`
2. Check database: `ls -la .htmlgraph/index.sqlite`
3. Check environment: `echo $HTMLGRAPH_SESSION_ID`

### Spike not linked to parent

**Problem:** Spike created but child_spike_count is 0

**Solution:**
1. Check spike timestamp > parent timestamp
2. Check spike within 1 hour of parent event
3. Verify spike type='spike' in database
4. Check SDK.spikes.create() was called

### Environment variable not available

**Problem:** `HTMLGRAPH_PARENT_EVENT` is None

**Solution:**
1. This is expected if Task() delegation failed
2. Use `os.environ.get(..., "unknown")` with default
3. Continue work even if parent tracking unavailable
4. SDK will still create spike for knowledge capture

## Related Documentation

- [Hybrid Event Capture System](./HYBRID_EVENT_CAPTURE.md)
- [SDK Reference](./SDK.md)
- [Task() Tool Documentation](./TOOLS.md#task)
- [Event Traces API](./API.md#event-traces)
