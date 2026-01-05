# User Guide: System Prompt Customization

Customize your Claude Code system prompt to enforce project-specific guidance, model preferences, and delegation patterns. This guide shows how to create, configure, and manage your system prompt in 5 minutes.

## Table of Contents
- [Quick Start](#quick-start)
- [What You Can Customize](#what-you-can-customize)
- [Creating Your System Prompt](#creating-your-system-prompt)
- [Common Customizations](#common-customizations)
- [Post-Compact Behavior](#post-compact-behavior)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)
- [FAQ](#faq)

---

## Quick Start

Get a working system prompt in 2 minutes:

```bash
# 1. Create the system prompt file
mkdir -p .claude
cat > .claude/system-prompt.md << 'EOF'
# System Prompt - My Project

## Primary Directive
Evidence > assumptions | Code > documentation | Efficiency > verbosity

## Model Selection
- **Haiku**: Quick implementations, orchestration, file operations
- **Sonnet**: Complex reasoning, architecture decisions
- **Opus**: Novel problems, deep research

## Delegation
Use `Task()` for work >30 minutes, >3 files, or requiring tests.

## Quality Gates
Before committing: `uv run ruff check --fix && uv run ruff format && uv run mypy && uv run pytest`
EOF

# 2. Verify it was created
ls -lh .claude/system-prompt.md

# 3. Start a Claude Code session
# The system prompt auto-injects at session start!
```

That's it. Your system prompt is now active and will persist across compacts and resumes.

---

## What You Can Customize

### Default vs Custom

**Plugin Default (All Projects):**
- Included automatically with HtmlGraph plugin
- Available to all projects without setup
- Generic guidance for model selection and delegation

**Your Custom Prompt (This Project Only):**
- Lives in `.claude/system-prompt.md`
- Overrides plugin defaults when present
- Project-specific rules, patterns, and guidance
- Survives compact/resume cycles
- Can be version controlled (commit to git)

### What Should Be in Your System Prompt

```
✅ DO include:
- Project-specific rules (language, style, patterns)
- Model selection guidance ("use Sonnet for X")
- Delegation patterns ("Task() for work >30 min")
- Quality gates (lint, type-check, test commands)
- Key architecture decisions
- Common anti-patterns to avoid
- Project context that doesn't change

❌ DON'T include:
- Sensitive credentials or secrets
- Large code examples (bloats token count)
- Session-specific context (changes each session)
- User-specific preferences (use Claude Code settings for that)
- Information already in README or CLAUDE.md
```

---

## Creating Your System Prompt

### File Location
```
your-project/
├── .claude/
│   ├── system-prompt.md          ← Your custom prompt (EDIT THIS)
│   ├── hooks/
│   │   └── scripts/
│   │       └── session-start.py  ← Injection logic (read-only)
│   └── settings.json             ← Plugin config
└── .htmlgraph/
    └── sessions/                 ← Session tracking
```

### Step 1: Create the File

```bash
mkdir -p .claude
touch .claude/system-prompt.md
```

### Step 2: Add Content

Start with this template and customize for your project:

```markdown
# System Prompt - [Your Project Name]

## Primary Directive
[Your core philosophy]

## Model Guidance

**Use Haiku (Default):**
- Quick implementations and fixes
- Orchestration and delegation
- Following established patterns
- File operations and searches
- Why: Fast, cost-effective, excellent at following instructions

**Use Sonnet (Complex Reasoning):**
- Architecture and design decisions
- Complex algorithms requiring multi-step logic
- Security analysis and code review
- When previous attempts failed
- Why: Strong reasoning, balanced speed/power

**Use Opus (Novel Problems):**
- Entirely new feature design from scratch
- Deep research and investigation tasks
- Completely novel problem domains
- When Sonnet's attempt was insufficient
- Why: Strongest reasoning, handles ambiguity

## Delegation Pattern
- Use `Task()` tool for multi-session work or complex reasoning
- Execute directly only for straightforward operations
- Delegate if: >30 minutes, >3 files, needs tests, novel problems

## Quality Gates
Before committing:
```
uv run ruff check --fix && uv run ruff format && uv run mypy src/ && uv run pytest
```

## Key Rules
1. Always Read before Write/Edit/Update
2. Use absolute paths only
3. Use `uv run` for all Python execution
4. Batch tool calls when independent
5. Fix all errors before committing
```

### Step 3: Verify Injection

After creating the file, start a new Claude Code session. The system prompt auto-injects as additional context. You'll see it appear in the context section of your first message.

---

## Common Customizations

### 1. Enforce Specific Model for Your Work

```markdown
## Model Requirements
- ALWAYS use Sonnet for architecture decisions
- ALWAYS use Haiku for quick file operations
- NEVER use Opus unless explicitly stuck (costly)
```

### 2. Add Language-Specific Rules

```markdown
## Python Standards
- Use type hints on all functions and classes
- Follow PEP 8 (enforced by ruff)
- Write docstrings for public APIs
- Minimum 80% test coverage

## JavaScript Standards
- Use TypeScript for all new code
- ESLint config: `.eslintrc.json`
- Prettier formatting with 2-space indent
```

### 3. Enforce Delegation for Your Team

```markdown
## Team Delegation Rules
- Backend changes: MUST use `Task(subagent_type="codex")`
- Frontend work: MUST use `Task(subagent_type="codex")`
- Database migrations: MUST use `Task()` with human review
- Documentation: Can execute directly if <100 lines
```

### 4. Add Project Context

```markdown
## Architecture Overview
- Monorepo with packages: `/packages/api`, `/packages/web`, `/packages/core`
- Database: PostgreSQL with migrations in `/db/migrations/`
- Test structure: Mirrors src layout, suffixed with `.test.ts`
- Build tool: Vite for frontend, Rollup for libraries

## Critical Paths (Don't break these!)
- `packages/core/types.ts` — Type definitions (breaking changes = pain)
- `packages/api/middleware/` — Request pipeline (must be stable)
- Database schema — Always backward compatible migrations
```

### 5. Add Anti-Patterns to Avoid

```markdown
## Anti-Patterns to Avoid
- ❌ Modifying database schema without migration
- ❌ Importing from `/dist` (use source files)
- ❌ Using `any` type (use proper TypeScript)
- ❌ Committing without running tests
- ❌ Changing third-party APIs without deprecation period
```

---

## Post-Compact Behavior

### How It Works

Your system prompt persists across compact/resume cycles through three layers:

1. **Layer 1 (Immediate)**: SessionStart hook injects prompt as `additionalContext`
   - Runs at session start
   - Makes prompt immediately available
   - Highest reliability (99.9%)

2. **Layer 2 (Fallback)**: Environment variable `CLAUDE_SYSTEM_PROMPT`
   - Backup if Layer 1 fails
   - Persists across context clears
   - 95% reliability

3. **Layer 3 (Recovery)**: File backup system
   - Last resort recovery
   - Always available if file exists
   - 99% reliability

### What Remains Consistent

After using `/compact`:
```
✅ PERSISTS:
- Your system prompt (all three layers)
- Project structure understanding
- Model selection guidance
- Delegation patterns
- Key rules and constraints

⚠️ CLEARS (by design):
- All previous conversation context
- Temporary work context
- Session history
```

---

## Troubleshooting

### System Prompt Not Appearing

**Symptom**: You don't see your system prompt after starting a session.

**Causes**:
1. File doesn't exist or is empty
2. Hook not executing (plugin not installed)
3. File has syntax errors

**Solutions**:
```bash
# 1. Verify file exists and has content
ls -lh .claude/system-prompt.md
wc -l .claude/system-prompt.md  # Should be >10 lines

# 2. Check for syntax errors
cat .claude/system-prompt.md | head -20

# 3. Verify plugin is installed
claude plugin list | grep htmlgraph

# 4. Check hook execution (debug output)
claude --debug  # Then start a session, look for "system-prompt" in output
```

### Customizations Being Ignored

**Symptom**: You edited your system prompt but changes aren't appearing.

**Causes**:
1. Editing the plugin default (read-only)
2. File not saved properly
3. Stale context from previous session

**Solutions**:
```bash
# 1. Verify you're editing the right file
cat .claude/system-prompt.md | grep -i "your project name"

# 2. Make sure it's YOUR file, not the plugin's
# Should be: .claude/system-prompt.md (in your project)
# NOT: ~/.claude/plugin-files/system-prompt-default.md (in plugin)

# 3. After editing, start a NEW session
# (Current session keeps old context)

# 4. Check file permissions
chmod 644 .claude/system-prompt.md
```

### Prompt Not Surviving Compact

**Symptom**: Prompt disappeared after using `/compact`.

**Causes**:
1. File was deleted
2. .claude directory excluded from workspace
3. All three persistence layers failed

**Solutions**:
```bash
# 1. Verify file still exists
ls -lh .claude/system-prompt.md

# 2. Check if .claude is in workspace
# It should NOT be in .gitignore for system-prompt.md

# 3. If all else fails, check backup
# HtmlGraph creates backup at .htmlgraph/.system-prompt-backup.md
ls -lh .htmlgraph/.system-prompt-backup.md

# 4. Restore from backup if needed
cp .htmlgraph/.system-prompt-backup.md .claude/system-prompt.md
```

### Token Budget Exceeded

**Symptom**: System prompt injected, but gets truncated in context.

**Causes**:
1. Prompt is too long (>1000 tokens)
2. Other context consuming budget

**Solutions**:
```bash
# 1. Check prompt size
python3 -c "
text = open('.claude/system-prompt.md').read()
tokens = len(text) // 4  # Rough estimate: 1 token ≈ 4 characters
print(f'Approximate tokens: {tokens}')
"

# 2. Shorten prompt by:
# - Removing verbose examples
# - Using bullet points instead of paragraphs
# - Moving details to README or CLAUDE.md
# - Removing redundant sections

# 3. Increase token budget (if using custom setup)
# Default is 1000 tokens - should be enough for most prompts
```

---

## Examples

### Example 1: Python Project with Quality Gates

```markdown
# System Prompt - PyData Project

## Primary Directive
Quality > Speed | Tests > Coverage | Documentation > Code

## Model Selection
- **Haiku**: File operations, quick fixes, running tests
- **Sonnet**: Algorithm design, performance optimization
- **Opus**: Novel research problems, multi-step reasoning

## Quality Gates
BEFORE every commit:
```
uv run ruff check --fix  # Lint and format
uv run mypy src/         # Type checking
uv run pytest --cov      # Tests with coverage
```

Failure in any step blocks commit.

## Key Rules
1. All functions require type hints
2. All public APIs require docstrings
3. Test coverage minimum: 80%
4. Use `uv run` for ALL Python execution
5. Commit message format: `type(scope): description`

## Anti-Patterns
- ❌ `any` types (use `Union` or proper typing)
- ❌ Bare except clauses
- ❌ Print statements (use logging)
- ❌ Committing without tests passing
```

### Example 2: Frontend Project with Delegation

```markdown
# System Prompt - React App

## Delegation Rules (MANDATORY)
- Component implementation: MUST use `Task(subagent_type="codex")`
- UI design decisions: Execute directly (quick)
- Build system changes: MUST use `Task()` (needs testing)
- Dependency upgrades: MUST use `Task()` (risks conflicts)

## Model Selection
- **Haiku**: File edits, quick refactoring, running tests
- **Sonnet**: Component architecture, state management design
- **Opus**: Design system from scratch, novel patterns

## React Standards
- Functional components only (no class components)
- TypeScript required for all components
- Props interface for every component
- Storybook stories for complex components

## Testing Standards
- All components require unit tests (Jest)
- E2E tests for user flows (Cypress)
- Minimum coverage: 80%
```

### Example 3: DevOps/Infrastructure Project

```markdown
# System Prompt - Infrastructure

## Model Selection (Cost-Conscious)
- **Gemini**: Infrastructure research, documentation reading
- **Codex**: Script generation, configuration templates
- **Haiku**: Simple updates, running tests
- **Sonnet**: Architecture decisions, security review
- **Opus**: Novel infrastructure patterns

## Delegation Rules
- Terraform changes: MUST use `Task()` with plan review
- Script generation: Use Codex spawner
- Documentation research: Use Gemini (FREE)
- Security review: Use Sonnet
- Testing: Execute directly

## Critical Safety Rules
1. ALWAYS generate terraform plan before apply
2. NEVER use `--auto-approve` on production
3. Always review diffs before committing
4. Tag all infrastructure changes with `infra:`
5. Maintain disaster recovery procedures
```

---

## FAQ

### Q: Can I use both plugin default and custom prompts?
**A**: Yes! Your custom `.claude/system-prompt.md` completely overrides the plugin default. Both appear in context, but your version takes precedence for project-specific guidance.

### Q: How large can my system prompt be?
**A**: Recommended limit is 1000 tokens (~4000 characters). Longer prompts consume your context budget. If you need more guidance, split into:
- `.claude/system-prompt.md` — Core rules
- `CLAUDE.md` — Project context
- `README.md` — General information
- `.claude/rules/` — Detailed guidelines

### Q: Does my system prompt need to be in git?
**A**: Recommended yes! It's part of your project's guidance. Add to version control:
```bash
git add .claude/system-prompt.md
git commit -m "docs: add system prompt for project guidance"
```

### Q: What happens if my system prompt has errors?
**A**: The hook will skip injection, but work continues. No exceptions thrown. You'll miss the prompt guidance until fixed.

### Q: Can I have different prompts for different agents?
**A**: Single system prompt per project (in `.claude/system-prompt.md`). Use environment variables or project structure if you need agent-specific logic. Most projects use one consistent prompt.

### Q: How often should I update my system prompt?
**A**: When:
- Project architecture changes significantly
- New quality standards are adopted
- Team processes change
- New libraries or patterns introduced

Most projects update quarterly or on-demand. No need for frequent changes.

### Q: What if I want to test changes to my system prompt?
**A**: Edit `.claude/system-prompt.md`, save, then start a NEW session. Claude Code caches context, so you need a fresh session to see changes.

### Q: Can I include examples in my system prompt?
**A**: Yes, but keep them brief (1-2 lines max). Large examples bloat token usage. Link to examples in code instead:
```markdown
## Example Pattern
See real examples in:
- `src/components/Button.tsx` — Component pattern
- `tests/api.test.ts` — Testing pattern
- `scripts/deploy.sh` — Deployment pattern
```

### Q: How do I know my system prompt is working?
**A**: After starting a session:
1. Look at context section — should show your prompt
2. Check `/hooks` command — should list SessionStart hook
3. Ask Claude a question — responses should follow your rules
4. Use `/compact` then ask again — prompt should reappear

---

## Next Steps

1. **Create your system prompt** (5 minutes using Quick Start)
2. **Start a session** and verify it appears in context
3. **Customize** using Common Customizations section
4. **Test** post-compact persistence with `/compact` command
5. **Commit** to git so your team sees the same guidance

For deeper technical details, see [System Prompt Architecture](SYSTEM_PROMPT_ARCHITECTURE.md).

For admin setup and enforcement, see [Delegation Enforcement Guide](DELEGATION_ENFORCEMENT_ADMIN_GUIDE.md).
