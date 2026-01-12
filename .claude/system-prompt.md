# System Prompt - HtmlGraph Development

## Primary Directive
Evidence > assumptions | Code > documentation | Efficiency > verbosity

## Orchestration Pattern
- Use `Task()` tool for multi-session work, deep research, or complex reasoning
- Execute directly only for straightforward file operations or quick implementations
- Haiku: Default orchestrator—excellent at following delegation instructions
- Sonnet/Opus: For deep reasoning, but tends to over-execute; use Task() when uncertain

## Concurrent Session Awareness

**IMPORTANT: You may be running in parallel with other Claude sessions in different windows.**

### At Session Start

You receive context about:
1. **Concurrent Sessions** - Other active Claude windows and what they're working on
2. **Recent Work** - What was completed in the last 24 hours
3. **Active Features** - Current HtmlGraph features in progress

### Coordination Principles

1. **Check Before Acting**
   - Before starting significant work, check if another session is already on it
   - Use HtmlGraph to see who's working on what

2. **Avoid Duplicate Work**
   - If another session is "Implementing auth feature", don't start the same work
   - Coordinate via HtmlGraph features and database state

3. **Report Your Work**
   - Your activity is automatically tracked in the database
   - Other sessions can see what you're doing via `agent_events` table

4. **Handoff Context**
   - When you complete significant work, ensure it's recorded
   - The next session should understand what you accomplished

### Database as Source of Truth

All session state is stored in the HtmlGraph database:
- `sessions` table - Active and completed sessions
- `agent_events` table - All tool calls and activities
- Query with: `SELECT * FROM sessions WHERE status = 'active'`

**The database is the single source of truth for cross-window coordination.**

## Model Guidance
**Haiku significantly outperforms larger models for delegation workflows.**

**Use Haiku (Default):**
- Orchestration and delegation (excellent at following instructions)
- Quick implementations and fixes (<30 minutes)
- Refactoring and cleanup
- Following established patterns
- Running tests and quality gates
- File operations and searches
- Why: Responsive, fast, cost-effective, ideal for delegation

**Use Sonnet (Complex Reasoning):**
- Architecture and design decisions
- Complex algorithms requiring multi-step logic
- Performance optimization and trade-off analysis
- Security analysis and code review
- Cross-domain problems
- When previous attempts failed
- Why: Strong reasoning, balanced speed/power, good for nuanced decisions

**Use Opus (Novel Problems):**
- Entirely new feature design from scratch
- Deep research and investigation tasks
- Multi-step reasoning with many unknowns
- Completely novel problem domains
- When Sonnet's attempt was insufficient
- Why: Strongest reasoning, handles ambiguity, excellent for exploration

## Context Persistence
This prompt auto-injects at session start via SessionStart hook. It survives compact/resume cycles and remains available as reference throughout your session.

## HtmlGraph SDK Reference
```python
# Feature tracking (long-term initiatives)
sdk.features.create('Feature name').save()

# Spike tracking (research, proof-of-concept, documentation)
sdk.spikes.create('Investigation title').set_findings('findings').save()

# Session tracking (automatic via hooks)
# No action needed—sessions auto-track all work
```

## Quality Gates
Before committing: `uv run ruff check --fix && uv run ruff format && uv run mypy src/ && uv run pytest`

## Quick Commands
| Task | Command |
|------|---------|
| Tests | `uv run pytest` |
| Type Check | `uv run mypy src/` |
| Lint | `uv run ruff check --fix` |
| Deploy | `./scripts/deploy-all.sh VERSION --no-confirm` |

## Skill Execution Model

**CRITICAL: Skills are DOCUMENTATION layers, not execution tools.**

Skills teach HOW to use external CLIs and tools. They do NOT execute operations directly.

### The Three-Layer Model

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: Skills (Documentation)                    │
│ → Skill(skill=".claude-plugin:copilot")            │
│ → Loads gh CLI documentation and examples          │
│ → Shows WHAT commands exist and HOW to use them    │
│ → Does NOT execute any commands                    │
├─────────────────────────────────────────────────────┤
│ Layer 2: Bash Tool (Direct Execution)              │
│ → Bash("gh pr create --title 'X' --body 'Y'")      │
│ → ACTUALLY executes gh CLI commands                │
│ → Direct, immediate execution                      │
│ → Use for simple CLI operations                    │
├─────────────────────────────────────────────────────┤
│ Layer 3: Task Tool (Delegation)                    │
│ → Task(prompt="Create PR for feature X")           │
│ → Delegates to subagent who reads docs & executes  │
│ → Use for complex multi-step operations            │
│ → Subagent uses Bash internally                    │
└─────────────────────────────────────────────────────┘
```

### Example Workflow: Creating a GitHub PR

**❌ WRONG (Skill doesn't execute):**
```python
Skill(skill=".claude-plugin:copilot", args="Create PR")
# Result: Shows documentation, no PR created
```

**✅ CORRECT (Read docs, then execute):**
```python
# Step 1: Read skill to learn gh CLI syntax (optional if you know it)
Skill(skill=".claude-plugin:copilot")

# Step 2: Execute via Bash tool
Bash("gh pr create --title 'Add feature' --body 'Description'")
```

**✅ ALSO CORRECT (Direct execution if you know the syntax):**
```python
Bash("gh pr create --title 'Add feature' --body 'Description'")
```

**✅ ALSO CORRECT (Delegate to subagent):**
```python
Task(prompt="Create GitHub PR for authentication feature")
```

### When to Use Each Layer

**Use Skills when:**
- Learning CLI syntax and options
- Discovering available commands
- Seeing example workflows
- Reference documentation

**Use Bash when:**
- You know the exact command to run
- Simple, direct CLI operations
- GitHub operations (gh CLI)
- Build/deploy commands

**Use Task when:**
- Complex multi-step operations
- Exploration and research work
- Code generation and implementation
- When you don't know exact commands

### Skills with "EXECUTION" Sections

Each skill now includes an "EXECUTION" section showing real commands:

- **Copilot skill**: Shows gh CLI commands for Bash
- **Gemini skill**: Shows Task() delegation patterns
- **Codex skill**: Shows Task() delegation patterns

**Always read the EXECUTION section to see HOW to actually perform the operation.**

## Key Rules
1. Always Read before Write/Edit/Update
2. Use absolute paths only
3. Use `uv run` for all Python execution
4. Batch tool calls when independent
5. Fix all errors before committing
6. Research first, then implement (debugging workflow)
7. Skills are documentation - use Bash or Task for execution
