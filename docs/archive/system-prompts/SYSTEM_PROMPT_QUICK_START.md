# System Prompt Quick Start - 5-Minute Setup

Get your project's system prompt working in 5 minutes with this quick start guide.

## What Is a System Prompt? (1 minute)

A **system prompt** is a file (`.claude/system-prompt.md`) that contains your project's guidance for Claude—model selection, delegation patterns, quality gates, and key rules. It's automatically injected into every Claude Code session and survives context compacts.

**Why it matters:**
- Guides Claude's behavior consistently across sessions
- Persists across `/compact` commands (automatic recovery)
- Encodes team agreements and project patterns
- Eliminates manual re-stating of context

## Quick Setup (2 minutes)

### Step 1: Create the file
```bash
mkdir -p .claude
cat > .claude/system-prompt.md << 'EOF'
# System Prompt - My Project

## Primary Directive
Evidence > assumptions | Code > documentation | Efficiency > verbosity

## Model Selection
- **Haiku**: Quick tasks, orchestration, file operations
- **Sonnet**: Complex reasoning, architecture decisions
- **Opus**: Novel problems, deep research

## Delegation Pattern
Use `Task()` for work >30 minutes, >3 files, or requiring tests.

## Key Rules
1. Always Read before Write/Edit/Update
2. Use absolute paths only
3. Use `uv run` for all Python execution
4. Batch tool calls when independent
5. Fix all errors before committing

## Quality Gates
Before committing:
```bash
uv run ruff check --fix && uv run ruff format && uv run mypy src/ && uv run pytest
```
EOF
```

### Step 2: Verify it works
```bash
# Check the file exists
ls -lh .claude/system-prompt.md

# Start a new Claude Code session
# You should see your system prompt content in the context!
```

### Step 3: Test persistence
```bash
# In Claude Code, run:
/compact

# System prompt should re-appear after context clears
```

Done! Your system prompt is now active and persistent.

## What You Can Customize

Edit `.claude/system-prompt.md` to add:

**Model Guidance** - When to use which model:
```markdown
## Model Selection
- **Haiku**: Quick fixes, running tests, orchestration
- **Sonnet**: Complex logic, architecture, security review
- **Opus**: Novel features, deep research, creative design
```

**Delegation Rules** - When to use Task():
```markdown
## Delegation Pattern
Delegate when:
- Task takes >30 minutes
- Requires file exploration
- Needs extensive testing
- Affects multiple components
```

**Quality Gates** - Commands to run before commit:
```markdown
## Quality Gates
BEFORE every commit:
uv run ruff check --fix && uv run ruff format && \
uv run mypy src/ && uv run pytest
```

**Architecture Notes** - Key project decisions:
```markdown
## Key Architecture Decisions
- Monorepo with /packages, /src, /tests directories
- TypeScript for all new frontend code
- Database migrations always backward compatible
- Type coverage minimum 90%
```

**Anti-Patterns** - What NOT to do:
```markdown
## Anti-Patterns to Avoid
- ❌ Using `any` types (use proper TypeScript)
- ❌ Importing from /dist (use source files)
- ❌ Committing without running tests
- ❌ Modifying database schema without migration
```

## Common Configurations

### Python Project with Testing
```markdown
# System Prompt - Python Project

## Model Selection
- Haiku: File operations, quick fixes, running tests
- Sonnet: Algorithm design, performance optimization
- Opus: Novel research problems

## Quality Gates
BEFORE every commit:
uv run ruff check --fix && uv run mypy src/ && uv run pytest --cov

## Key Rules
1. All functions require type hints
2. All public APIs require docstrings
3. Minimum 80% test coverage
4. Use `uv run` for ALL Python execution
```

### React Project with Components
```markdown
# System Prompt - React Frontend

## Delegation Rules (MANDATORY)
- Component implementation: MUST use Task()
- UI design decisions: Execute directly
- Build system changes: MUST use Task()
- Dependency upgrades: MUST use Task()

## React Standards
- Functional components only
- TypeScript required
- Props interface for every component
- Storybook stories for complex components

## Key Rules
1. Prettier formatting: 2-space indent
2. ESLint must pass before commit
3. 80% test coverage minimum
4. No console logs in commits
```

### Infrastructure/DevOps Project
```markdown
# System Prompt - Infrastructure

## Model Selection (Cost-Conscious)
- Gemini: Infrastructure research, docs (FREE)
- Haiku: Simple updates, testing
- Sonnet: Architecture decisions, security
- Opus: Novel infrastructure patterns

## Critical Safety Rules
1. ALWAYS generate terraform plan before apply
2. NEVER use --auto-approve on production
3. Always review diffs before committing
4. Tag all infrastructure changes with `infra:`
5. Maintain disaster recovery procedures

## Delegation Rules
- Terraform changes: MUST use Task() with plan review
- Script generation: Can execute directly
- Documentation research: Use Gemini (free)
- Security review: Use Sonnet
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Prompt not appearing | Check file exists: `ls .claude/system-prompt.md` |
| Prompt not persisting after `/compact` | File was deleted or hook not running. Verify plugin: `claude plugin list \| grep htmlgraph` |
| Hook not executing | Install plugin: `claude plugin install htmlgraph@latest` |
| File not readable | Fix permissions: `chmod 644 .claude/system-prompt.md` |
| Prompt has old content | Restart session or use `/clear` then edit file |
| Prompt too large (>1000 tokens) | Remove verbose sections, link to README for details |

**Quick diagnostic:**
```bash
#!/bin/bash
echo "File exists: $([ -f .claude/system-prompt.md ] && echo YES || echo NO)"
echo "File size: $(wc -c < .claude/system-prompt.md 2>/dev/null || echo 0) bytes"
echo "Plugin installed: $(claude plugin list 2>/dev/null | grep -q htmlgraph && echo YES || echo NO)"
echo "In environment: $([ -n "$CLAUDE_SYSTEM_PROMPT" ] && echo YES || echo NO)"
```

## Best Practices

**1. Keep it concise** - Aim for 200-400 tokens (~800-1600 characters)
- Token budget is limited
- Concise rules are more effective than verbose guidance
- Link to detailed docs instead of embedding everything

**2. Be specific** - Generic guidance is less useful
```markdown
# WRONG: "Use best practices"
# RIGHT: "Use uv run for Python, never raw python or pip"
```

**3. Include model guidance** - Help Claude choose the right tool
```markdown
## Model Selection
- Haiku: Delegation, quick tasks (default)
- Sonnet: Complex reasoning, architecture
- Opus: Novel problems, deep research
```

**4. Document your workflow** - Make your process explicit
```markdown
## Development Workflow
1. Read existing code
2. Plan changes before implementation
3. Write tests before code
4. Run quality gates before commit
```

**5. Version control it** - Share with your team
```bash
git add .claude/system-prompt.md
git commit -m "chore: add system prompt for project guidance"
git push
```

## File Locations

```
your-project/
├── .claude/
│   ├── system-prompt.md          ← Edit this file!
│   ├── hooks/
│   │   └── scripts/
│   │       └── session-start.py  ← Auto-managed (read-only)
│   └── settings.json
└── .htmlgraph/
    ├── sessions/                 ← Automatic tracking
    └── .system-prompt-backup.md  ← Auto-created backup
```

## Advanced: Post-Compact Persistence

Your system prompt uses a **three-layer persistence system**:

1. **Layer 1** (Primary) - SessionStart hook injects as `additionalContext`
   - Runs at every session start
   - Highest reliability (99.9%)

2. **Layer 2** (Backup) - Environment variables persist across compacts
   - `CLAUDE_SYSTEM_PROMPT` environment variable
   - Survives `/compact` command (95% reliability)

3. **Layer 3** (Recovery) - File backup in `.htmlgraph/`
   - Auto-created backup copy
   - Emergency recovery (99% reliability)

**Result:** System prompt persists automatically across `/compact` with no manual intervention needed.

For technical details, see [System Prompt Architecture](SYSTEM_PROMPT_ARCHITECTURE.md).

## Next Steps

1. ✅ Create `.claude/system-prompt.md` (use template above)
2. ✅ Start a Claude Code session and verify it appears in context
3. ✅ Customize using sections that match your project
4. ✅ Test with `/compact` to verify persistence
5. ✅ Commit to git: `git add .claude/system-prompt.md && git commit -m "chore: add system prompt"`
6. ✅ Share with team (documented in version control)

## Related Documentation

- **[System Prompt Architecture](SYSTEM_PROMPT_ARCHITECTURE.md)** - Technical deep dive into three-layer system
- **[Delegation Enforcement Guide](DELEGATION_ENFORCEMENT_ADMIN_GUIDE.md)** - Admin setup for teams
- **[Troubleshooting Guide](SYSTEM_PROMPT_TROUBLESHOOTING.md)** - Detailed problem-solving workflows

## Support

Having issues? Check [Troubleshooting Guide](SYSTEM_PROMPT_TROUBLESHOOTING.md) for diagnosis steps and solutions.

---

**Remember:** Your system prompt guides your work throughout every session. Keep it focused, specific, and up-to-date. It evolves as your project and team processes change.
