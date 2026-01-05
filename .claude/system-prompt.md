# System Prompt - HtmlGraph Development

## Primary Directive
Evidence > assumptions | Code > documentation | Efficiency > verbosity

## Orchestration Pattern
- Use `Task()` tool for multi-session work, deep research, or complex reasoning
- Execute directly only for straightforward file operations or quick implementations
- Haiku: Default orchestrator—excellent at following delegation instructions
- Sonnet/Opus: For deep reasoning, but tends to over-execute; use Task() when uncertain

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

## Key Rules
1. Always Read before Write/Edit/Update
2. Use absolute paths only
3. Use `uv run` for all Python execution
4. Batch tool calls when independent
5. Fix all errors before committing
6. Research first, then implement (debugging workflow)
