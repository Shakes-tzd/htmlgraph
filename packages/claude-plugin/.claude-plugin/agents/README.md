# Code Execution Agents

**Three execution agents for different complexity levels.**

## Agent Selection Decision Tree

```
┌─────────────────────────────────────────────────────────┐
│ COMPLEXITY ASSESSMENT                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 1. How many files affected?                            │
│    → 1-2 files: Consider Haiku                         │
│    → 3-8 files: Consider Sonnet                        │
│    → 10+ files: Consider Opus                          │
│                                                         │
│ 2. How clear are requirements?                         │
│    → 100% clear: Haiku or Sonnet                       │
│    → 70-90% clear: Sonnet                              │
│    → <70% clear: Opus (needs exploration)              │
│                                                         │
│ 3. What's the cognitive load?                          │
│    → Low (rename, fix typo): Haiku                     │
│    → Medium (implement feature): Sonnet                │
│    → High (design architecture): Opus                  │
│                                                         │
│ 4. What's the risk level?                              │
│    → Low: Haiku                                        │
│    → Medium: Sonnet                                    │
│    → High (security, performance): Opus                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Quick Reference

| Agent | Model | Cost/1M | Use For | Avoid For |
|-------|-------|---------|---------|-----------|
| **haiku-coder** | Haiku 4.5 | $0.80 | Simple edits, typos, config | Multi-file, complex logic |
| **sonnet-coder** | Sonnet 4.5 | $3.00 | Features, integrations, tests | Simple edits, architecture |
| **opus-coder** | Opus 4.5 | $15.00 | Architecture, optimization | Simple tasks, clear requirements |

## Delegation Examples

### Simple Task → Haiku
```python
Task(
    subagent_type='general-purpose',
    model='haiku',
    prompt='Fix typo in README.md line 42: "recieve" → "receive"'
)
# Cost: ~$0.01 | Time: 30s
```

### Moderate Task → Sonnet
```python
Task(
    subagent_type='general-purpose',
    model='sonnet',
    prompt='Implement JWT authentication middleware with token refresh logic and tests'
)
# Cost: ~$0.50 | Time: 10-20 min
```

### Complex Task → Opus
```python
Task(
    subagent_type='general-purpose',
    model='opus',
    prompt='Design distributed caching architecture with Redis, handle cache invalidation across services'
)
# Cost: ~$2-5 | Time: 30-60 min
```

## Cost Optimization Strategy

### 1. Start with Haiku (70% of tasks)
Most tasks are simpler than they appear:
- Single file edits
- Clear requirements
- Low risk

### 2. Escalate to Sonnet (25% of tasks)
When you need:
- Multi-file coordination
- Some design decisions
- Integration work

### 3. Reserve Opus (5% of tasks)
Only when truly needed:
- System architecture
- Complex refactors
- Ambiguous requirements

## Anti-Patterns

### ❌ Don't Over-Engineer
```python
# BAD: Opus for simple task
Task(model='opus', prompt='Fix typo in README')
# Wastes $15 per million tokens

# GOOD: Haiku for simple task
Task(model='haiku', prompt='Fix typo in README')
# Uses $0.80 per million tokens
```

### ❌ Don't Under-Estimate
```python
# BAD: Haiku for complex architecture
Task(model='haiku', prompt='Design microservices architecture')
# Will produce shallow, inadequate design

# GOOD: Opus for complex architecture
Task(model='opus', prompt='Design microservices architecture')
# Produces thoughtful, well-reasoned design
```

## Orchestrator Guidance

As an orchestrator, your job is:

1. **Assess complexity** before delegating
2. **Choose the right agent** based on assessment
3. **Don't delegate to yourself** - execute nothing, coordinate everything
4. **Optimize for cost** - use cheaper agents when possible

### Complexity Assessment Checklist

```python
# Before delegating, ask:
complexity = assess_task(
    files_affected=count_files(),
    requirement_clarity=0.0-1.0,
    cognitive_load='low'|'medium'|'high',
    risk_level='low'|'medium'|'high'
)

if complexity.simple:
    Task(model='haiku', ...)
elif complexity.moderate:
    Task(model='sonnet', ...)
else:
    Task(model='opus', ...)
```

## When in Doubt

**Default to Sonnet** - it's the best balance of capability and cost for most tasks.

**Escalate to Opus** if Sonnet struggles or produces inadequate results.

**Use Haiku** only when 100% confident the task is trivial.
