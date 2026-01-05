# System Prompt Persistence - Quick Reference Card

## What It Does (30 seconds)

Your system prompt at `.claude/system-prompt.md` is automatically injected into every Claude Code session via the SessionStart hook. It survives compacts, resumes, and context clears.

## Installation (1 minute)

```bash
# 1. Verify HtmlGraph plugin
claude plugin list | grep htmlgraph

# 2. Start a session (auto-creates .claude/system-prompt.md)
cd your-project

# 3. System prompt auto-created, ready to customize
ls -la .claude/system-prompt.md
```

## Customize Your Prompt (5 minutes)

Edit `.claude/system-prompt.md`:

```markdown
# Your System Prompt

## Primary Directive
Evidence > assumptions | Code > documentation

## Workflow Pattern
- Use Task() for complex work
- Execute directly for simple tasks
- Haiku for delegation

## Model Guidance
- Haiku: Quick tasks, delegation
- Sonnet: Complex reasoning
- Opus: Novel problems

## Key Rules
1. Always Read before Write
2. Use absolute paths
3. Batch tool calls
4. Fix errors before committing
```

## Verify It Works (2 minutes)

```bash
# Check prompt injected at session start
# (You should see your content in context)

# Use /compact to test persistence
# (Prompt should re-appear after context reset)

# Debug if needed
claude --debug
```

## Model Selection (Quick)

| Task | Model | Why |
|------|-------|-----|
| Bug fix, refactor, quick task | **Haiku** | Fast, cheap, follows patterns |
| Complex logic, architecture | **Sonnet** | Good reasoning, balanced cost |
| Novel problem, research | **Opus** | Best reasoning, thorough |

**Decision Tree:**
```
Straightforward task?
├─ YES → Use Haiku
└─ NO → Need complex reasoning?
   ├─ YES → Use Sonnet
   └─ NO → Novel/research?
      ├─ YES → Use Opus
      └─ NO → Use Sonnet
```

## Common Configurations

### HtmlGraph Development
```markdown
# System Prompt - HtmlGraph Development

## Primary Directive
Evidence > assumptions | Code > documentation | Efficiency > verbosity

## Orchestration Pattern
- Use Task() for multi-session work, deep research, or complex reasoning
- Execute directly only for straightforward file operations
- Haiku: Default orchestrator—excellent at following delegation instructions
- Sonnet/Opus: For deep reasoning, but tends to over-execute; use Task() when uncertain

## Model Guidance
- Haiku (Recommended): Orchestration, delegation, quick tasks
- Sonnet: Complex reasoning, architecture decisions
- Opus: Novel problems, research-heavy investigations

## Key Rules
1. Always Read before Write/Edit/Update
2. Use absolute paths only
3. Use `uv run` for all Python execution
4. Batch tool calls when independent
5. Fix all errors before committing
6. Research first, then implement
```

### General Development
```markdown
# System Prompt - General Development

## Primary Directive
Write reliable, maintainable code with comprehensive testing.

## Workflow
1. Read existing code before changes
2. Plan before implementation
3. Write tests before code
4. Run tests before committing

## Model Selection
- Haiku: Quick fixes, refactoring, simple features
- Sonnet: Architecture, complex logic, research
- Opus: Novel problems, major decisions

## Key Rules
1. Always test before committing
2. No console.logs or debug code in commits
3. Use meaningful variable names
4. Document complex logic
```

### Research-Focused
```markdown
# System Prompt - Research

## Primary Directive
Thorough investigation before implementation.

## Research Workflow
1. Define research questions clearly
2. Explore multiple sources
3. Analyze findings systematically
4. Document decision rationale

## Model Selection
- Haiku: Quick literature searches
- Sonnet: Comparative analysis
- Opus: Deep investigation of novel topics

## Key Rules
1. Always cite sources
2. Document assumptions
3. Consider multiple perspectives
4. Test hypotheses before committing
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Prompt not appearing | Check file exists: `ls .claude/system-prompt.md` |
| Prompt not persisting after compact | Use `/compact` again (may take 2 cycles) |
| Hook not executing | Verify plugin: `claude plugin list \| grep htmlgraph` |
| File not readable | Fix permissions: `chmod 644 .claude/system-prompt.md` |
| Prompt has old content | Restart session or use `/clear` |
| Hook timeout | Reduce prompt size (aim for <500 words) |

## File Locations

```
your-project/
├── .claude/
│   ├── system-prompt.md          ← Edit this!
│   ├── hooks/
│   │   └── scripts/
│   │       └── session-start.py  ← Read-only
│   └── settings.json
└── .htmlgraph/
    └── sessions/
```

## Integration Points

### With HtmlGraph SDK
```python
from htmlgraph import SDK

# Your system prompt guides this
sdk = SDK(agent="claude")

# Feature tracking
feature = sdk.features.create("Task Name").save()

# Session tracking (automatic)
# Your prompt is re-injected after compact
```

### With Orchestrator Mode
```python
# Your system prompt includes orchestrator guidance
Task(
    prompt="Your delegation task...",
    subagent_type="general-purpose"
)
# Subagent receives injected system prompt too
```

### With Session Tracking
```bash
# Check sessions (your prompt was injected)
uv run htmlgraph session list

# View session details
uv run htmlgraph session show <session-id>
```

## Performance

- **Injection latency**: <50ms (negligible)
- **Token cost**: 100-300 tokens (depends on prompt size)
- **Context overhead**: <2% (minimal)
- **Reliability**: High (uses built-in hook mechanism)

## Advanced: Update Your Prompt Effectively

**After editing `.claude/system-prompt.md`:**

1. **Option A - Full restart** (clean slate)
   ```bash
   # Quit Claude Code, start new session
   # Prompt injected fresh
   ```

2. **Option B - Use /compact** (faster)
   ```bash
   /compact
   # Context clears, prompt re-injected
   # Continues in same session
   ```

3. **Option C - Use /clear** (simple)
   ```bash
   /clear
   # Context cleared, prompt re-appears
   ```

## Related Docs

- **SYSTEM_PROMPT_PERSISTENCE_GUIDE.md**: Full installation and configuration guide
- **MODEL_SELECTION_GUIDE.md**: Detailed model selection framework
- **delegate.sh**: Helper script for model decisions
- **ORCHESTRATOR_MODE_GUIDE.md**: Delegation and orchestration patterns

## Checklist: System Prompt Setup

- [ ] HtmlGraph plugin installed (`claude plugin list`)
- [ ] `.claude/system-prompt.md` exists (`ls .claude/system-prompt.md`)
- [ ] Custom prompt added (edited file)
- [ ] Verified in session context (appears at session start)
- [ ] Tested persistence (`/compact` command)
- [ ] Committed to git (`git add .claude/system-prompt.md`)
- [ ] Team knows about it (document in README if team project)

## One-Liners

```bash
# Check if custom prompt exists
test -f .claude/system-prompt.md && echo "✅ Custom prompt found" || echo "❌ Not found"

# Check file size (should be <500 words)
wc -w .claude/system-prompt.md

# Count token estimate (rough: 1 word ≈ 1.3 tokens)
python3 -c "with open('.claude/system-prompt.md') as f: words = len(f.read().split()); tokens = int(words * 1.3); print(f'{words} words ≈ {tokens} tokens')"

# Verify hook is registered
claude /hooks | grep -i sessionstart

# Show your current prompt
cat .claude/system-prompt.md

# Edit your prompt
vim .claude/system-prompt.md  # or your editor
```

## Tips & Tricks

**1. Keep a backup**
```bash
cp .claude/system-prompt.md .claude/system-prompt.md.backup
```

**2. Version control your prompt**
```bash
git add .claude/system-prompt.md
git commit -m "chore: update system prompt with new model guidance"
git push
```

**3. Team prompts**
```bash
# Create per-team prompts
.claude/system-prompt.md          # General
.claude/system-prompt-frontend.md # Frontend team
.claude/system-prompt-backend.md  # Backend team
# (Note: currently supports one system-prompt.md per project)
```

**4. Compare prompts**
```bash
# See what changed between sessions
git log -p .claude/system-prompt.md

# Diff against backup
diff .claude/system-prompt.md .claude/system-prompt.md.backup
```

**5. Test prompt effectiveness**
```bash
# Track which model you used most
# (System logs this automatically in .htmlgraph/sessions/)

# Review past sessions
uv run htmlgraph session list

# Check session details for model info
uv run htmlgraph session show <session-id>
```

## Summary

| What | Where | When |
|------|-------|------|
| **Edit prompt** | `.claude/system-prompt.md` | Anytime |
| **Takes effect** | Next session start | Auto |
| **Survives** | Compacts, resumes, /clear | Auto |
| **Verify** | Show in context, use /compact | Always |
| **Share** | git commit `.claude/system-prompt.md` | Anytime |
| **Debug** | `claude --debug` | If issues |

---

**Remember:** Keep your system prompt focused, specific, and up-to-date. It guides your work throughout the session and should evolve as your needs change.
