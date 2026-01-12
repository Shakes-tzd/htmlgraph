# Multi-AI Orchestration - Complete Reference

## COST-FIRST ROUTING (IMPERATIVE)

**Before using any spawner, MUST follow this decision tree:**

```
┌──────────────────────────────────────────────────────────────┐
│ COST-FIRST ROUTING CHECKLIST                                 │
│                                                              │
│ 1. Is this exploration/research/batch work?                 │
│    → MUST use spawn_gemini (FREE)                           │
│                                                              │
│ 2. Is this code generation/fixes/tests?                     │
│    → MUST use spawn_codex (cheap, specialized)              │
│                                                              │
│ 3. Is this git/GitHub work?                                 │
│    → MUST use spawn_copilot (cheap, integrated)             │
│                                                              │
│ 4. Does this REQUIRE deep reasoning?                        │
│    → MAY use spawn_claude (expensive)                       │
│                                                              │
│ 5. Everything else?                                         │
│    → spawn_gemini FIRST (FREE), Haiku fallback              │
└──────────────────────────────────────────────────────────────┘
```

## Cost Hierarchy

| Tier | Spawner | Cost | Use Case |
|------|---------|------|----------|
| FREE | spawn_gemini | $0 | Exploration, research, batch ops, multimodal |
| $ | spawn_codex | Low | Code generation, fixes, tests, refactoring |
| $ | spawn_copilot | Low | Git operations, GitHub workflows |
| $$ | Task(haiku) | Medium | Fallback ONLY when above fail |
| $$$ | Task(sonnet) | High | Multi-agent coordination |
| $$$$ | spawn_claude | Very High | Strategic architecture, complex reasoning |

---

## HeadlessSpawner API

### spawn_gemini (USE FIRST - FREE!)

**Purpose:** Exploration, research, batch operations, multimodal analysis

**Cost:** FREE (2M tokens/minute rate limit)

**Configuration:**
```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()
result = spawner.spawn_gemini(
    prompt="Search codebase for all auth patterns",
    include_directories=["src/", "tests/"]
    # model=None (default) - uses latest Gemini models (Gemini 3 preview)
)
```

**Features:**
- FREE tier with 2M tokens/minute
- 1M token context window
- Vision API for image analysis
- Multimodal (images, PDFs, audio)
- Fastest response times

**MUST use for:**
- Codebase exploration and research
- File searching and analysis
- Batch operations over many files
- Document/image analysis
- Any exploratory work before implementation

### spawn_codex (USE FOR CODE - CHEAP)

**Purpose:** Code generation, bug fixes, workspace edits

**Cost:** $ (cheap, code-specialized)

**Configuration:**
```python
result = spawner.spawn_codex(
    prompt="Implement OAuth authentication endpoint",
    sandbox="workspace-write"  # Required for edits
)
```

**Sandbox modes:**
- `workspace-write` - Auto-approve code edits
- `workspace-read` - Read-only access
- `network` - Allow network operations

**MUST use for:**
- Implementing features
- Fixing bugs
- Refactoring code
- Writing tests
- Any code generation work

### spawn_copilot (USE FOR GIT - CHEAP)

**Purpose:** Git operations, GitHub workflows

**Cost:** $ (cheap, GitHub-integrated)

**Configuration:**
```python
result = spawner.spawn_copilot(
    prompt="Commit changes and create PR",
    allow_tools=["shell(git)", "github(*)"]
)
```

**Tool permissions:**
- `shell(git)` - Git command access
- `read(*.py)` - File read access
- `github(*)` - GitHub API access

**MUST use for:**
- Git commits and pushes
- PR creation and review
- Branch management
- GitHub issue management
- Any git/GitHub workflow

### spawn_claude (EXPENSIVE - STRATEGIC ONLY)

**Purpose:** Complex reasoning, architecture, design

**Cost:** $$$$ (very high - use sparingly)

**Configuration:**
```python
result = spawner.spawn_claude(
    prompt="Design scalable notification system",
    permission_mode="plan"  # Safe, generates plan only
)
```

**Permission modes:**
| Mode | Description |
|------|-------------|
| `bypassPermissions` | Auto-approve all |
| `acceptEdits` | Auto-approve code edits only |
| `dontAsk` | Fail on any permission |
| `plan` | Generate plan without executing |
| `delegate` | Balanced safety + autonomy |

**ONLY use for:**
- System architecture decisions
- Complex multi-domain analysis
- Strategic planning
- Deep reasoning that other AIs cannot handle

## Spawner Comparison Table (Updated with Costs)

| Spawner | Cost Tier | Price | Speed | Primary Use |
|---------|-----------|-------|-------|-------------|
| `spawn_gemini` | FREE | $0 | Fast | Exploration, research, batch |
| `spawn_codex` | $ | Low | Medium | Code generation, fixes |
| `spawn_copilot` | $ | Low | Medium | Git/GitHub operations |
| `spawn_claude` | $$$$ | High | Slow | Strategic reasoning only |

---

## Enforcement Mechanism

### Pre-Delegation Validation

Before any delegation, validate spawner selection:

```python
def validate_spawner_selection(task_type: str, selected_spawner: str) -> bool:
    """
    Enforce cost-first routing rules.
    Returns True if selection is valid, False if wrong spawner.
    """
    cost_first_rules = {
        "exploration": "spawn_gemini",
        "research": "spawn_gemini",
        "batch_ops": "spawn_gemini",
        "file_search": "spawn_gemini",
        "code_generation": "spawn_codex",
        "implementation": "spawn_codex",
        "bug_fix": "spawn_codex",
        "testing": "spawn_codex",
        "git_commit": "spawn_copilot",
        "git_push": "spawn_copilot",
        "pr_creation": "spawn_copilot",
        "github_issue": "spawn_copilot",
        "architecture": "spawn_claude",
        "strategic_planning": "spawn_claude",
    }

    required = cost_first_rules.get(task_type)
    if required and selected_spawner != required:
        print(f"COST VIOLATION: {task_type} should use {required}, not {selected_spawner}")
        return False
    return True
```

### Cost Tracking

Track spawner usage for cost analysis:

```python
from htmlgraph import SDK

sdk = SDK(agent="orchestrator")

# After each spawner call, track cost tier
spike = sdk.spikes.create("Spawner Usage") \
    .set_findings(f"""
    ## Delegation Summary
    - Task: {task_description}
    - Spawner: {spawner_used}
    - Cost Tier: {cost_tier}
    - Tokens: {tokens_used}
    - Was Gemini tried first? {gemini_attempted}
    """) \
    .save()
```

### Verification After Spawning

After Gemini/Codex generates code, MUST verify:

```bash
# Quick verification (fast)
./scripts/verify-code.sh src/path/to/file.py

# Full quality check (thorough)
./scripts/test-quality.sh src/path/to/file.py

# If verification fails:
# 1. Iterate with SAME spawner (not Claude)
# 2. Only escalate if 3+ failures
```

## HtmlGraph Integration

Track all spawned work:

```python
from htmlgraph import SDK
from htmlgraph.orchestration import delegate_with_id

sdk = SDK(agent="orchestrator")

# Create tracked feature
feature = sdk.features.create("Implement OAuth").save()

# Generate delegation context
task_id, prompt = delegate_with_id(
    title="Implement OAuth",
    description="Add JWT tokens...",
    subagent_type="general-purpose"
)

# Delegate with tracking
Task(
    prompt=prompt,
    description=f"{task_id}: Implement OAuth"
)

# Save findings
spike = sdk.spikes.create(f"Orchestration: {task_id}") \
    .set_findings(result) \
    .link_feature(feature.id) \
    .save()
```

## Parallel Coordination Pattern

```python
from htmlgraph.orchestration import delegate_with_id, get_results_by_task_id

# Spawn parallel tasks
auth_id, auth_prompt = delegate_with_id("Implement auth", "...", "general-purpose")
test_id, test_prompt = delegate_with_id("Write tests", "...", "general-purpose")
docs_id, docs_prompt = delegate_with_id("Update docs", "...", "general-purpose")

# Delegate all in parallel
Task(prompt=auth_prompt, description=f"{auth_id}: Implement auth")
Task(prompt=test_prompt, description=f"{test_id}: Write tests")
Task(prompt=docs_prompt, description=f"{docs_id}: Update docs")

# Retrieve results independently
auth_results = get_results_by_task_id(sdk, auth_id)
test_results = get_results_by_task_id(sdk, test_id)
docs_results = get_results_by_task_id(sdk, docs_id)
```

## Anti-Patterns to Avoid

**1. Using spawn_claude for simple queries**
```python
# BAD - expensive for simple work
spawn_claude("Search for all TODO comments")

# GOOD - cheap and fast
spawn_gemini("Search for all TODO comments")
```

**2. Sequential when parallel is possible**
```python
# BAD - total time = T1 + T2 + T3
spawn_codex("Fix auth bugs")  # wait
spawn_codex("Fix db bugs")    # wait
spawn_codex("Fix api bugs")   # wait

# GOOD - total time = max(T1, T2, T3)
spawn_codex("Fix auth bugs")
spawn_codex("Fix db bugs")
spawn_codex("Fix api bugs")
# all run in parallel
```

**3. Mixing business logic with spawning**
```python
# BAD - orchestrator doing tactical work
if file_exists("config.py"):
    spawn_codex("Update config")

# GOOD - delegate everything
Task(prompt="Check if config.py exists and update if needed")
```
