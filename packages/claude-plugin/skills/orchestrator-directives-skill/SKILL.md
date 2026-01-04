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
   → YES = MUST use Gemini spawner (FREE)

2. Is this code work?
   → Implementation, fixes, tests, refactoring
   → YES = MUST use Codex spawner (cheap, specialized)

3. Is this git/GitHub?
   → Commits, PRs, issues, branches
   → YES = MUST use Copilot spawner (cheap, integrated)

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
- Code implementation → Task(haiku)               # USE Codex spawner
- Git commits → Task(haiku)                       # USE Copilot spawner
- File search → Task(haiku)                       # USE Gemini spawner (FREE!)
- Research → Task(haiku)                          # USE Gemini spawner (FREE!)

CORRECT (cost-optimized):
- Code implementation → Codex spawner             # Cheap, sandboxed
- Git commits → Copilot spawner                   # Cheap, GitHub-native
- File search → Gemini spawner                    # FREE!
- Research → Gemini spawner                       # FREE!
- Strategic decisions → Claude Opus               # Expensive, but needed
- Haiku → FALLBACK ONLY                           # When spawners fail
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
| Research, exploration | Gemini spawner (FREE) | Haiku |
| Code implementation | Codex spawner ($) | Sonnet |
| Bug fixes | Codex spawner ($) | Haiku |
| Git operations | Copilot spawner ($) | Haiku |
| File analysis | Gemini spawner (FREE) | Haiku |
| Testing | Codex spawner ($) | Haiku |
| Architecture | Claude Opus ($$$$) | Sonnet |

## Decision Framework

1. **Is this exploratory/research?** → Gemini spawner (FREE)
2. **Is this code work?** → Codex spawner (cheap)
3. **Is this git/GitHub?** → Copilot spawner (cheap)
4. **Needs deep reasoning?** → Claude Opus (expensive)
5. **Everything else** → Gemini spawner FIRST, Haiku fallback

## Cost-First Delegation Patterns

**IMPORTANT: As a Claude Code agent, use Task() with spawner subagent types (not HeadlessSpawner Python API).**

### Research/Exploration (USE GEMINI - FREE!)
```
# ✅ CORRECT - Use Task with Gemini spawner subagent type
Task(
    subagent_type="htmlgraph:gemini-spawner",
    description="Explore codebase for auth patterns",
    prompt="""
    Search codebase for all authentication patterns and summarize:
    - Include directories: src/, tests/
    - Look for: JWT, OAuth, session handling
    - Provide summary of findings
    """
)

# If Gemini spawner unavailable, fallback to Haiku
Task(prompt="Search for auth patterns", subagent_type="haiku")
```

### Code Implementation (USE CODEX - CHEAP!)
```
# ✅ CORRECT - Use Task with Codex spawner subagent type
Task(
    subagent_type="htmlgraph:codex-spawner",
    description="Implement OAuth endpoint",
    prompt="""
    Implement OAuth authentication endpoint:
    - Sandbox mode: workspace-write
    - Add JWT token generation
    - Include error handling
    - Write unit tests
    """
)

# If Codex spawner unavailable, fallback to Sonnet
Task(prompt="Implement OAuth endpoint", subagent_type="sonnet")

# ALWAYS verify generated code
Task(
    subagent_type="haiku",
    description="Verify code quality",
    prompt="Run ./scripts/verify-code.sh src/path/to/file.py"
)
```

### Git Operations (USE COPILOT - CHEAP!)
```
# ✅ CORRECT - Use Task with Copilot spawner subagent type
Task(
    subagent_type="htmlgraph:copilot-spawner",
    description="Commit and create PR",
    prompt="""
    Commit changes and create pull request:
    - Message: "feat: add OAuth authentication"
    - Files: src/auth/*.py, tests/test_auth.py
    - Create PR with description of changes
    """
)

# If Copilot spawner unavailable, use script fallback
Task(
    subagent_type="haiku",
    description="Run git commit script",
    prompt="./scripts/git-commit-push.sh 'feat: add auth' --no-confirm"
)
```

**Note:** HeadlessSpawner is the Python API for direct programmatic usage. As a Claude Code agent, you should use the Task() tool with spawner subagent types as shown above.

## Parallel Coordination

```
# ✅ CORRECT - Parallel Task() calls with spawner subagent types
# All three run in parallel, optimized for cost

Task(
    subagent_type="htmlgraph:gemini-spawner",
    description="Research auth patterns",
    prompt="Analyze all authentication patterns in codebase..."
)

Task(
    subagent_type="htmlgraph:codex-spawner",
    description="Implement OAuth",
    prompt="Implement OAuth authentication based on research..."
)

Task(
    subagent_type="htmlgraph:copilot-spawner",
    description="Create PR",
    prompt="Commit changes and create pull request..."
)

# All run in parallel, optimized for cost:
# - Gemini: FREE
# - Codex: $ (cheap)
# - Copilot: $ (cheap)
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
