# Orchestrator Directives Skill

Use this skill for delegation patterns and decision frameworks in orchestrator mode.

**Trigger keywords:** orchestrator, delegation, subagent, task coordination, parallel execution

---

## CRITICAL: Cost-First Delegation (IMPERATIVE)

**Claude Code is EXPENSIVE. You MUST delegate to FREE/CHEAP AIs first.**

### PRE-DELEGATION CHECKLIST (MUST EXECUTE BEFORE EVERY TASK())

```
BEFORE delegating, MUST ask IN ORDER:

1. Can Gemini do this?
   → Exploration, research, batch ops, file analysis
   → YES = MUST use spawn_gemini (FREE)

2. Is this code work?
   → Implementation, fixes, tests, refactoring
   → YES = MUST use spawn_codex (cheap, specialized)

3. Is this git/GitHub?
   → Commits, PRs, issues, branches
   → YES = MUST use spawn_copilot (cheap, integrated)

4. Does this need deep reasoning?
   → Architecture, complex planning
   → YES = Use Claude Opus (expensive, but needed)

5. Is this coordination?
   → Multi-agent work
   → YES = Use Claude Sonnet (mid-tier)

6. ONLY if above fail → Haiku (fallback)
```

### WRONG vs CORRECT

```
WRONG (wastes Claude quota):
- Code implementation → Task(haiku)    # USE spawn_codex
- Git commits → Task(haiku)            # USE spawn_copilot
- File search → Task(haiku)            # USE spawn_gemini (FREE!)
- Research → Task(haiku)               # USE spawn_gemini (FREE!)

CORRECT (cost-optimized):
- Code implementation → spawn_codex()   # Cheap, sandboxed
- Git commits → spawn_copilot()         # Cheap, GitHub-native
- File search → spawn_gemini()          # FREE!
- Research → spawn_gemini()             # FREE!
- Strategic decisions → Claude Opus     # Expensive, but needed
- Haiku → FALLBACK ONLY                 # When others fail
```

---

## Core Philosophy

**Delegation > Direct Execution.** Cascading failures consume exponentially more context than structured delegation.

**Cost-First > Capability-First.** Use FREE/cheap AIs before expensive Claude models.

## Quick Reference: What to Delegate

### Execute Directly (Orchestrator Only)

- `Task()` / `spawn_*()` - Delegation itself
- `AskUserQuestion()` - Clarifying requirements
- `TodoWrite()` - Tracking work
- SDK operations - Creating features, spikes
- Single file quick lookup
- Simple status checks

### ALWAYS Delegate (with Cost-First Routing)

| Operation | MUST Use | Fallback |
|-----------|----------|----------|
| Research, exploration | spawn_gemini (FREE) | Haiku |
| Code implementation | spawn_codex ($) | Sonnet |
| Bug fixes | spawn_codex ($) | Haiku |
| Git operations | spawn_copilot ($) | Haiku |
| File analysis | spawn_gemini (FREE) | Haiku |
| Testing | spawn_codex ($) | Haiku |
| Architecture | Claude Opus ($$$$) | Sonnet |

## Decision Framework

1. **Is this exploratory/research?** → spawn_gemini (FREE)
2. **Is this code work?** → spawn_codex (cheap)
3. **Is this git/GitHub?** → spawn_copilot (cheap)
4. **Needs deep reasoning?** → Claude Opus (expensive)
5. **Everything else** → spawn_gemini FIRST, Haiku fallback

## Cost-First Delegation Patterns

### Research/Exploration (USE GEMINI - FREE!)
```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# FREE exploration with Gemini
result = spawner.spawn_gemini(
    prompt="Search codebase for all auth patterns and summarize",
    include_directories=["src/", "tests/"]
)

if not result.success:
    # ONLY fallback to Haiku if Gemini fails
    Task(prompt="Search for auth patterns", subagent_type="haiku")
```

### Code Implementation (USE CODEX - CHEAP!)
```python
# Use Codex for code work (NOT Haiku!)
result = spawner.spawn_codex(
    prompt="Implement OAuth authentication endpoint",
    sandbox="workspace-write"
)

if not result.success:
    # Fallback to Sonnet for complex code
    Task(prompt="Implement OAuth", subagent_type="sonnet")

# ALWAYS verify generated code
# ./scripts/verify-code.sh src/path/to/file.py
```

### Git Operations (USE COPILOT - CHEAP!)
```python
# Use Copilot for git (NOT Haiku!)
result = spawner.spawn_copilot(
    prompt="Commit changes and create PR",
    allow_tools=["shell(git)", "github(*)"]
)

if not result.success:
    # Fallback to delegated script
    Task(
        prompt="./scripts/git-commit-push.sh 'message' --no-confirm",
        subagent_type="haiku"
    )
```

## Parallel Coordination

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# Parallel spawning with cost-first routing
research = spawner.spawn_gemini("Research auth patterns")      # FREE
impl = spawner.spawn_codex("Implement OAuth")                  # $
git = spawner.spawn_copilot("Create PR")                       # $

# All run in parallel, optimized for cost
```

## SDK Integration

```python
from htmlgraph import SDK
sdk = SDK(agent='orchestrator')

# Track delegated work with spawner info
feature = sdk.features.create("Implement auth") \
    .set_priority("high") \
    .add_metadata({
        "spawner": "codex",  # Track which spawner used
        "cost_tier": "$"     # Track cost tier
    }) \
    .save()
```

## Verification After Spawning

**MUST verify code generated by Gemini/Codex:**

```bash
# Quick verification
./scripts/verify-code.sh src/path/to/file.py

# Full quality check
./scripts/test-quality.sh src/path/to/file.py

# If verification fails, iterate with SAME spawner
# DO NOT escalate to Claude just because verification failed
```

---

**For spawner selection:** Use `/multi-ai-orchestration` skill
**For complete patterns:** See [reference.md](./reference.md)
