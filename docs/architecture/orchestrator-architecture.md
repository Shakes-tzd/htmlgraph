# Orchestrator Architecture: Flexible Multi-Agent Coordination

**"Coordination, Not Control" - Flexible Model Selection Based on Task Needs**

This document describes HtmlGraph's orchestrator pattern for coordinating multiple AI agents in parallel, preserving context efficiency while maximizing model flexibility.

---

## Core Principle: Flexibility Over Rigidity

The orchestrator pattern is **NOT a rigid hierarchy** with fixed rules. Instead:

- ✅ **Flexible model selection** - Any model can do any work; choose based on task fit and cost
- ✅ **Dynamic spawner composition** - Mix and match spawner types within the same workflow
- ✅ **Cost optimization** - Use cheaper models for exploratory work, pay for expensive reasoning when needed
- ✅ **Capability-first thinking** - What capability is needed? Which model/CLI provides it best?

**Anti-Pattern: Rigid Rules**
```python
# ❌ WRONG - "Gemini must do exploration"
# ❌ WRONG - "Claude must do reasoning"
# ❌ WRONG - "Copilot must do git operations"
```

**Pattern: Capability-Based Selection**
```python
# ✅ RIGHT - "This task needs fast, cheap exploration → Use Gemini spawner"
# ✅ RIGHT - "This task needs deep reasoning → Use Claude Opus"
# ✅ RIGHT - "This task needs GitHub integration → Use Copilot spawner"
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Orchestrator (Haiku)                     │
│              Cheap, Strategic, Context-Preserving               │
│                                                                 │
│  Role: Coordinate parallel work, make high-level decisions    │
│  Context: Stays clean (delegates heavy lifting)               │
│  Cost: Minimal (mostly Task() calls)                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬─────────────────┐
        │              │              │                 │
        ▼              ▼              ▼                 ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────────┐
   │ Gemini  │   │ Copilot │   │ Codex   │   │ Claude (any) │
   │ Spawner │   │ Spawner │   │ Spawner │   │   Spawner    │
   └────┬────┘   └────┬────┘   └────┬────┘   └──────┬───────┘
        │             │             │                │
        │ FREE        │ GitHub      │ Codex          │ Any task
        │ exploratory │ integrated  │ integrated     │ (reasoning,
        │ research    │ workflows   │ workflows      │  analysis)
        │ batch ops   │ git ops     │ coding         │
        │             │ GitHub API  │ completions    │
        ▼             ▼             ▼                ▼
     ┌────────────────────────────────────────────────┐
     │         Parallel Subagent Execution            │
     │    (Each runs independently with full tool     │
     │     access within their spawner's scope)       │
     └────────────────────────────────────────────────┘
```

---

## The Four Spawner Types

### 1. Gemini Spawner

**Best for:** Exploratory research, batch analysis, multimodal tasks, cost-sensitive workflows

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()
result = spawner.spawn_gemini(
    prompt="Analyze codebase and find all authentication patterns",
    model="gemini-2.0-flash",  # FREE tier with 2M tokens/min
    include_directories=["src/auth", "src/security"],
    output_format="json"
)

if result.success:
    patterns = json.loads(result.response)
    print(f"Found {len(patterns)} patterns (Cost: FREE)")
else:
    # Automatic fallback to Haiku
    Task(prompt="Find auth patterns", subagent_type="general-purpose")
```

**Characteristics:**
- Model: Google Gemini 2.0-Flash
- Cost: FREE tier (2M tokens/minute)
- Best use: Large-scale exploration, batch file analysis
- Fallback: Automatic to Haiku if CLI fails
- Tools: Read, Bash, Grep, Glob, WebSearch, WebFetch

**When to choose:**
- Need to analyze large codebases (exploratory)
- Budget-conscious (FREE tier)
- Batch processing many files
- Don't require Claude's deep reasoning
- Want fast iteration (2M tokens/min throughput)

---

### 2. Copilot Spawner

**Best for:** GitHub-integrated workflows, git operations, repository management

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# GitHub operations only
result = spawner.spawn_copilot(
    prompt="Create GitHub issue and link to PR #123",
    allow_tools=["github(*)"]  # Fine-grained tool control
)

# Git operations only
result = spawner.spawn_copilot(
    prompt="Create feature branch and commit changes",
    allow_tools=["shell(git)"]
)

# Mixed permissions
result = spawner.spawn_copilot(
    prompt="GitHub workflow with restrictions",
    allow_tools=["github(*)", "shell(git)"],
    deny_tools=["shell(rm)", "write(/etc/*)"]
)

if result.success:
    print(f"GitHub operation complete: {result.response}")
else:
    # Automatic fallback to Sonnet
    Task(prompt="Use gh CLI for GitHub operations", subagent_type="sonnet")
```

**Characteristics:**
- Model: GitHub Copilot CLI
- Cost: Depends on Copilot subscription
- Best use: GitHub-native operations, git workflows
- Fallback: Automatic to Claude Sonnet if CLI fails
- Tools: Read, Bash, Grep, Glob (with fine-grained permissions)

**Tool Permission Controls:**
```python
# Allow specific tools only
allow_tools=["github(*)", "shell(git)"]

# Block dangerous operations
deny_tools=["shell(rm)", "write(/etc/*)", "shell(sudo)"]

# Hybrid approach
allow_tools=["github(*)", "shell(git)"]
deny_tools=["shell(rm)"]
```

**When to choose:**
- GitHub-centric workflows (issues, PRs, actions)
- Need GitHub API access
- Want tool-restricted execution for safety
- Git operations integrated with GitHub
- Testing Copilot's code generation capabilities

---

### 3. Codex Spawner

**Best for:** Code generation, Codex platform integration, coding completions

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()
result = spawner.spawn_codex(
    prompt="Generate unit tests for src/auth/login.py",
    include_directories=["src/auth"],
    model="codex"  # Or specific model available on Codex
)

if result.success:
    tests = result.response
    print(f"Generated tests:\n{tests}")
else:
    # Automatic fallback to Claude
    Task(prompt="Generate unit tests for auth module")
```

**Characteristics:**
- Model: Codex platform default
- Cost: Platform-dependent
- Best use: Code generation, coding tasks
- Fallback: Automatic to Claude if CLI fails
- Tools: Read, Bash, Grep, Glob

**When to choose:**
- Code generation and completions needed
- Codex platform integration required
- Prefer Codex's code-specific capabilities
- Testing different models for code tasks
- Codex-specific features (e.g., execution environment)

---

### 4. Claude Spawner (Flexible)

**Best for:** Reasoning, analysis, strategic planning, any complex task

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# Use any Claude model via Task()
result = spawner.spawn_claude(
    prompt="Analyze architecture and recommend refactoring",
    model="claude-opus-4-5",  # Or haiku, sonnet, etc.
    reasoning="extensive"  # For complex reasoning tasks
)

# Or simpler: just use Task() directly
Task(
    subagent_type="general-purpose",
    prompt="Analyze architecture and recommend refactoring"
)
```

**Characteristics:**
- Model: Any Claude model (Haiku, Sonnet, Opus, etc.)
- Cost: Model-dependent
- Best use: Reasoning, analysis, strategic decisions
- Flexibility: Can use alternative models within spawner
- Tools: Full access (Read, Bash, Grep, Glob, Edit, Write)

**Model selection within Claude spawner:**
```python
# Use Haiku for cheap, fast tasks
Task(subagent_type="general-purpose",
     prompt="Run tests and report failures")

# Use Sonnet for balanced tasks
result = spawner.spawn_claude(
    model="claude-3-5-sonnet-20241022",
    prompt="Code refactoring task"
)

# Use Opus for deep reasoning
result = spawner.spawn_claude(
    model="claude-opus-4-5",
    prompt="Complex architectural analysis"
)
```

**When to choose:**
- Reasoning and analysis required
- Strategic planning and decision-making
- Complex multi-step problems
- When other spawners don't fit
- Need Claude's specific capabilities

---

## Decision Framework: Which Spawner to Use?

```
Task starts here
      │
      ▼
Is it exploratory research?
├─ YES → Gemini spawner (FREE, fast, 2M tokens/min)
└─ NO → Continue...
        │
        ▼
Does it need GitHub integration?
├─ YES → Copilot spawner (GitHub API, git ops)
└─ NO → Continue...
        │
        ▼
Is it a code generation task?
├─ YES → Codex spawner (code completions)
└─ NO → Continue...
        │
        ▼
Does it need reasoning/analysis?
├─ YES → Claude spawner (any Claude model)
└─ NO → Default to Claude spawner
```

**But remember:** These are suggestions, not rules. Mix and match based on actual task needs:

```python
# ✅ Flexible approach - use best tool for each subtask
Task(subagent_type="gemini-spawner",
     prompt="Explore codebase and list all API endpoints")

Task(subagent_type="copilot-spawner",
     prompt="Create GitHub issue for findings")

Task(subagent_type="claude-spawner",
     prompt="Analyze endpoints for security issues")
```

---

## Pattern Examples

### Pattern 1: Parallel Multi-Tool Exploration

Launch multiple spawners to explore different aspects simultaneously:

```python
from htmlgraph import SDK

sdk = SDK(agent="orchestrator")

# Parallel exploration - all run at same time
gemini_task = Task(
    subagent_type="gemini-spawner",
    prompt="Find all authentication patterns in src/auth/. Return JSON with pattern names, file locations, and brief descriptions."
)

codex_task = Task(
    subagent_type="codex-spawner",
    prompt="Generate unit tests for src/auth/login.py based on common auth patterns."
)

claude_task = Task(
    subagent_type="claude-spawner",
    prompt="Analyze auth patterns for security vulnerabilities. Focus on: token handling, session management, input validation."
)

# Orchestrator waits for all to complete
# Each runs in parallel - total time = slowest task
print("Exploration complete!")
```

**Benefits:**
- All work runs in parallel (not sequential)
- Each agent uses best tool for their task
- Orchestrator stays focused (just coordinates)
- Total time = slowest subagent (not sum of all)

---

### Pattern 2: Cost-Optimized Workflow

Use cheaper models for heavy lifting, expensive models only for reasoning:

```python
# Step 1: Cheap exploration (Gemini FREE)
gemini_result = Task(
    subagent_type="gemini-spawner",
    prompt="Analyze 500+ Python files for security issues. Return structured list of potential issues found."
)

# Step 2: Expensive analysis (Claude Opus - only on findings)
analysis_result = Task(
    subagent_type="claude-spawner",  # Uses expensive model
    prompt=f"""Given these potential security issues found by exploration:

{gemini_result.findings}

Perform deep security analysis:
1. Verify each issue is real (not false positive)
2. Estimate severity (critical/high/medium/low)
3. Recommend fixes
4. Create remediation plan

Output: Prioritized security report with fixes"""
)

print(f"Cheap exploration: FREE (Gemini)")
print(f"Deep analysis: 1,000 tokens (Opus)")
print(f"Total cost: Minimal")
```

**Cost Breakdown:**
- Exploration: FREE (Gemini spawner)
- Analysis: Only on real findings (Opus)
- Orchestrator: Minimal (just coordination)

---

### Pattern 3: Model Fallback Chain

Use preferred model with automatic fallback:

```python
# Primary: Gemini (FREE)
# Fallback: Haiku (if Gemini CLI fails)
result = spawner.spawn_gemini(
    prompt="Explore codebase",
    model="gemini-2.0-flash"
)

if not result.success:
    print("Gemini failed, falling back to Haiku...")
    # Automatic fallback in spawner
    # OR explicit fallback
    Task(prompt="Explore codebase", subagent_type="general-purpose")
```

**Fallback chains:**
- Gemini spawner → Haiku if CLI fails
- Copilot spawner → Sonnet if CLI fails
- Codex spawner → Claude if CLI fails
- Claude spawner → Any other Claude model if needed

---

### Pattern 4: Mixed Spawner Workflow

Combine different spawners for optimal cost and capability:

```python
# Part 1: Cheap, parallel exploration (multiple spawners)
exploration_results = {
    "auth": Task(
        subagent_type="gemini-spawner",
        prompt="Explore src/auth/ security"
    ),
    "api": Task(
        subagent_type="gemini-spawner",
        prompt="Explore src/api/ endpoints"
    ),
    "github": Task(
        subagent_type="copilot-spawner",
        prompt="Check GitHub issues and PRs",
        allow_tools=["github(*)"]
    )
}

# Part 2: Consolidation (expensive reasoning, once only)
consolidation = Task(
    subagent_type="claude-spawner",
    prompt=f"""Based on exploration findings:

Auth findings: {exploration_results['auth'].response}
API findings: {exploration_results['api'].response}
GitHub status: {exploration_results['github'].response}

Create a unified plan for next steps."""
)

# Cost profile:
# - Exploration: FREE (Gemini) + GitHub API (Copilot)
# - Consolidation: One expensive Claude call
# - Total: Optimized cost with thorough analysis
```

---

## Model Flexibility Within Spawners

**Key insight:** Spawners are NOT limited to their primary model. Use alternative models within spawners:

```python
# ✅ Gemini spawner usually uses Gemini 2.0-Flash
spawner = HeadlessSpawner()
result = spawner.spawn_gemini(
    prompt="Explore codebase",
    model="gemini-2.0-flash"  # Primary
)

# ✅ But it can also use Haiku for cost optimization
Task(subagent_type="general-purpose",
     prompt="Explore codebase (faster alternative)")

# ✅ Copilot spawner usually uses Copilot
result = spawner.spawn_copilot(
    prompt="GitHub workflow",
    allow_tools=["github(*)"]
)

# ✅ But fallback uses Sonnet
# (automatic in spawner, or explicit Task())

# ✅ Claude spawner can use ANY Claude model
result = spawner.spawn_claude(model="claude-haiku")   # Cheap
result = spawner.spawn_claude(model="claude-sonnet")  # Balanced
result = spawner.spawn_claude(model="claude-opus-4-5") # Expensive
```

**Principle:** Models are tools, not rigid assignments.

---

## Cost Optimization Strategy

### 1. Know Your Task Requirements

```python
# Task type → Best spawner → Expected cost
{
    "exploratory": ("gemini-spawner", "FREE"),
    "batch-analysis": ("gemini-spawner", "FREE"),
    "github-ops": ("copilot-spawner", "GitHub API"),
    "code-generation": ("codex-spawner", "Platform-dependent"),
    "reasoning": ("claude-spawner", "Model-dependent"),
    "mixed-task": ("multiple spawners", "Optimized"),
}
```

### 2. Parallel Over Sequential

```python
# ❌ Sequential (expensive orchestrator fills context)
result1 = bash("search for auth patterns")
result2 = bash("search for api patterns")
result3 = bash("search for db patterns")
# Cost: 3 × expensive orchestrator tool calls

# ✅ Parallel (cheap orchestrator, parallel subagents)
Task(prompt="search for auth patterns")  # Subagent 1
Task(prompt="search for api patterns")   # Subagent 2
Task(prompt="search for db patterns")    # Subagent 3
# Cost: 3 × cheap subagent calls, runs in parallel
```

### 3. Use Cheap Models for Heavy Lifting

```python
# Pattern: Gemini for exploration, Claude for reasoning
Task(subagent_type="gemini-spawner",
     prompt="Find all database tables and relationships")

Task(subagent_type="claude-spawner",
     prompt="Analyze schema design and recommend improvements")

# Cost breakdown:
# - Exploration: FREE (Gemini)
# - Analysis: Expensive (Claude) but only on structured findings
```

### 4. Progressive Disclosure

```python
# Start cheap, escalate only if needed
Task(subagent_type="gemini-spawner",
     prompt="Does this code have security issues?")

if security_issues_found:
    # Only now use expensive Opus for deep analysis
    Task(subagent_type="claude-spawner",
         prompt="Deep security analysis and fixes",
         model="claude-opus-4-5")
```

---

## Orchestrator Benefits Over Direct Execution

### Context Preservation

```
DIRECT (fills context):
Orchestrator reads file 1 → context: 20 lines
Orchestrator reads file 2 → context: 40 lines
Orchestrator reads file 3 → context: 60 lines
... total context pollution: HIGH

DELEGATED (preserves context):
Orchestrator Task("Read files and summarize")
Subagent reads all 3 files
Orchestrator gets: 1 summary line
... total context pollution: MINIMAL
```

### Parallel Execution

```
SEQUENTIAL (slow):
Subagent 1: 10 seconds
Subagent 2: 10 seconds
Subagent 3: 10 seconds
Total time: 30 seconds

PARALLEL (fast):
Subagent 1: 10 seconds  ↓
Subagent 2: 10 seconds  ↓ Run at same time
Subagent 3: 10 seconds  ↓
Total time: 10 seconds (3x faster!)
```

### Cost Optimization

```
DIRECT (expensive):
Orchestrator (Opus): 5 tool calls, full context
Cost: 5 × expensive operations

DELEGATED (cheap):
Orchestrator (Haiku): 5 Task() calls
Subagents (Haiku/Gemini): Do the actual work
Cost: 5 × cheap orchestration calls
```

---

## Advanced: Subagent Capabilities

Each spawner type has different tool access:

| Spawner | Tools | Best For |
|---------|-------|----------|
| **Gemini** | Read, Bash, Grep, Glob, WebSearch, WebFetch | Exploration, research, multimodal |
| **Copilot** | Read, Bash, Grep, Glob (+ GitHub API) | GitHub workflows, git operations |
| **Codex** | Read, Bash, Grep, Glob | Code generation, completions |
| **Claude** | All tools (Read, Bash, Edit, Write, Grep, Glob) | General purpose, complex tasks |

---

## Troubleshooting

### Spawner Fails to Connect

```python
# If spawner CLI fails, automatic fallback occurs
result = spawner.spawn_gemini(prompt="...")

if not result.success:
    print(f"Spawner failed: {result.error}")
    # Fallback to Task() with general-purpose subagent
    Task(prompt=original_prompt)
```

### Subagent Exceeded Time Limit

```python
# Make prompt more specific, tighter boundaries
Task(
    prompt="In src/auth/ only, find login patterns. Stop after 5 minutes."
)
```

### Results Not Structured Enough

```python
# Request explicit output format
Task(
    prompt="""Find API endpoints and return as JSON:
    {
        "endpoints": [
            {"path": "/api/users", "method": "GET", "file": "src/api/users.py"}
        ]
    }"""
)
```

---

## Best Practices

1. **Start with Orchestrator Mode (Guidance)**
   - Learn patterns before strict enforcement
   - Warnings help identify optimization opportunities

2. **Delegate Early**
   - Don't fill orchestrator context before delegating
   - Delegate exploratory work immediately

3. **Mix Spawners Strategically**
   - Cheap models for exploration
   - Expensive models only for reasoning
   - GitHub spawner for GitHub ops

4. **Use Parallel Execution**
   - Multiple Task() calls run in parallel
   - Total time = slowest task, not sum of all

5. **Request Structured Output**
   - Ask for JSON, markdown tables, or organized text
   - Makes consolidation easier

6. **Monitor Results**
   - Check subagent status via session tracking
   - Review child sessions for debugging

---

## Related Documentation

- [Delegation Guide](./guide/delegation.md) - Detailed delegation patterns
- [AGENTS.md](../AGENTS.md) - SDK and workflow examples
- [CLAUDE.md](../CLAUDE.md) - Project-specific guidance
- [examples/](../examples/) - Real-world usage examples

---

## Summary

The orchestrator pattern is **flexible, not rigid**:

- ✅ **Choose models based on task needs** (not fixed rules)
- ✅ **Mix spawner types within workflows** (pick the right tool)
- ✅ **Optimize cost strategically** (cheap for exploration, expensive for reasoning)
- ✅ **Preserve orchestrator context** (delegate heavy lifting)
- ✅ **Maximize parallel execution** (run independent tasks simultaneously)

**Key insight:** The orchestrator is a **coordinator, not a controller**. Its job is to:
1. Break work into parallel subtasks
2. Delegate to best-fit spawner agents
3. Wait for results
4. Consolidate findings
5. Make high-level decisions

Everything else runs in subagents, keeping the orchestrator cheap and focused.
