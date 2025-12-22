# HtmlGraph Development Guide

## Meta-Principle: Dogfooding & Replicability

**CRITICAL**: HtmlGraph is both:
1. **The product we're building** - A graph database package
2. **The tool we're using** - To track its own development

**This means:**
- ✅ Every action we take MUST be replicable by users through the published package
- ✅ Use the SDK, CLI, or plugins - NOT custom scripts
- ❌ No one-off scripts that users can't replicate
- ❌ No manual database edits
- ❌ No shortcuts that bypass the package

## The Dogfooding Loop

```
┌─────────────────────────────────────────────┐
│   We develop HtmlGraph features             │
│   ↓                                         │
│   We use those features to track development│
│   ↓                                         │
│   We discover issues/improvements           │
│   ↓                                         │
│   We fix/enhance HtmlGraph                  │
│   └──────────────────────────────────────┘
```

**Every action demonstrates best practices to users.**

---

## Core Development Principles

### 1. **Use the SDK (Primary Interface)**

```python
# ✅ CORRECT - Using published SDK
from htmlgraph import SDK

sdk = SDK(agent="claude")
feature = sdk.features.create("New Feature")
    .set_priority("high")
    .save()

# ❌ WRONG - Direct file manipulation
with open('.htmlgraph/features/feat-001.html', 'w') as f:
    f.write('<html>...</html>')  # Users can't validate this!
```

### 2. **Use CLI for One-Off Commands**

```bash
# ✅ CORRECT - Using published CLI
uv run htmlgraph feature start feat-001
uv run htmlgraph status

# ❌ WRONG - Custom script users don't have
python scripts/my-custom-helper.py  # Not in package!
```

### 3. **Use Plugins for Extensions**

```bash
# ✅ CORRECT - Published plugin
claude plugin install htmlgraph

# ❌ WRONG - Local-only modification
# Editing .claude-code/config.json manually
```

### 4. **Document Everything Through Package**

```python
# ✅ CORRECT - Using SDK to document
with sdk.features.edit("feat-001") as f:
    f.activity_log.append("Decision: Chose X over Y because Z")

# ❌ WRONG - External note file users don't have access to
# echo "Decision log" >> ~/my-private-notes.txt
```

---

## Environment Variables & Secrets

### PyPI Publishing

**Location:** `.env` file (git-ignored, not committed)

**Required for:** Publishing packages to PyPI

**.env format:**
```bash
# PyPI API Token for package publishing
PyPI_API_TOKEN=pypi-xxxxxxxxxxxxxxxxxxxx
```

**How to get a token:**
1. Go to https://pypi.org/manage/account/token/
2. Create a new API token
3. Scope it to the `htmlgraph` project
4. Copy the token (starts with `pypi-`)
5. Add to `.env` file

**Publishing workflow:**
```bash
# 1. Bump version in pyproject.toml
# 2. Build package
uv build

# 3. Publish (sources token from .env)
source .env && uv publish --token "$PyPI_API_TOKEN"
```

**Important:** The `.env` file is local-only. Each developer needs their own PyPI token.

---

## Development Workflow (Replicable)

### Starting a New Feature

```python
# ✅ Use SDK (users will do this too)
from htmlgraph import SDK

sdk = SDK(agent="your-name")

# Create feature
feature = sdk.features.create("Add Dark Mode Support")
    .set_priority("high")
    .add_steps([
        "Design color palette",
        "Update CSS variables",
        "Add theme toggle",
        "Test accessibility"
    ])
    .save()

print(f"Created: {feature.id}")
```

Or via CLI:
```bash
# ✅ Use CLI (users will do this too)
uv run htmlgraph feature create "Add Dark Mode Support"
uv run htmlgraph feature start <feature-id>
```

### Working on a Feature

```python
# ✅ Use SDK context manager (users will do this too)
with sdk.features.edit("feat-001") as f:
    f.status = "in-progress"
    f.steps[0].completed = True
```

### Completing a Feature

```bash
# ✅ Use CLI (users will do this too)
uv run htmlgraph feature complete feat-001
```

### Publishing Release

```bash
# 1. Run tests (users should do this too)
uv run pytest

# 2. Bump version in pyproject.toml
# (users won't publish but should understand versioning)

# 3. Build (users might build locally)
uv build

# 4. Publish (only maintainers, but process is documented)
source .env && uv publish --token "$PyPI_API_TOKEN"
```

---

## What Users Can Replicate

### ✅ Users CAN Replicate:

1. **Feature tracking** - Create, start, complete features
2. **Session tracking** - Sessions auto-tracked by plugin
3. **Status queries** - Check project status at any time
4. **Analytics** - View progress, bottlenecks, trends
5. **Dashboard** - Visual progress tracking
6. **Git integration** - Hooks for automatic tracking
7. **SDK usage** - All SDK operations
8. **CLI usage** - All CLI commands
9. **Plugin installation** - Claude Code integration

### ❌ Users CANNOT Replicate:

1. **PyPI publishing** - Only maintainers have token
   - But process is documented!
2. **GitHub push access** - Only maintainers can push
   - But users can fork!

**Key:** Even actions users can't do are transparent and documented!

---

## Anti-Patterns to Avoid

### ❌ Custom Scripts Not in Package

```bash
# BAD - Users can't replicate
python scripts/fix-drift-scores.py
python scripts/migrate-old-format.py
```

**Instead:**
```bash
# GOOD - Add to CLI
uv run htmlgraph drift recalculate
uv run htmlgraph migrate --from-version 0.1.0
```

### ❌ Manual Database/File Edits

```python
# BAD - Users can't validate
import sqlite3
conn = sqlite3.connect('.htmlgraph/index.db')
conn.execute("UPDATE features SET status='done'")
```

**Instead:**
```python
# GOOD - Use SDK
sdk.features.batch_update(["feat-001"], {"status": "done"})
```

### ❌ Local-Only Configuration

```bash
# BAD - Only works for you
export HTMLGRAPH_SECRET_FEATURE=1
```

**Instead:**
```bash
# GOOD - Document in package, make it a feature flag
uv run htmlgraph config set experimental.feature true
```

### ❌ Undocumented Workflows

```bash
# BAD - Secret knowledge
# (Some manual process you remember but isn't written down)
```

**Instead:**
```bash
# GOOD - Always document
# Add to docs/WORKFLOW.md
# Add to plugin skills
# Add examples to docs/
```

---

## Testing Your Work

### Ask These Questions:

1. ✅ **Can a user replicate this action?**
   - If NO → Refactor to use SDK/CLI/Plugin

2. ✅ **Is this action documented?**
   - If NO → Add to docs/ or plugin skill

3. ✅ **Does this demonstrate best practices?**
   - If NO → Improve the approach

4. ✅ **Would I be proud to show this workflow to users?**
   - If NO → Clean it up!

### Example Check:

**Action:** "I need to mark 10 bugs as done"

**Bad approach:**
```python
# ❌ Direct file editing
import os
for f in os.listdir('.htmlgraph/bugs'):
    # manually edit HTML...
```

**Good approach:**
```python
# ✅ Use SDK (users can do this!)
from htmlgraph import SDK
sdk = SDK()
bug_ids = [f"bug-{i:03d}" for i in range(1, 11)]
sdk.bugs.mark_done(bug_ids)
```

**Why it's good:**
- ✅ Uses published SDK
- ✅ Users can copy-paste this code
- ✅ Demonstrates batch operations
- ✅ Type-safe, validated
- ✅ Maintainable

---

## Documentation Hierarchy

### 1. **docs/SDK_FOR_AI_AGENTS.md**
- Primary SDK reference
- Examples for all collections
- Performance benchmarks
- Best practices

### 2. **docs/WORKFLOW.md**
- Session workflows
- Decision frameworks
- Quality checklists

### 3. **docs/DEVELOPMENT.md** (this file)
- Meta-principles
- Dogfooding practices
- Replicability guidelines

### 4. **Plugin Skills**
- `packages/claude-plugin/skills/htmlgraph-tracker/SKILL.md`
- Real-time guidance for AI agents
- Decision frameworks
- Quick reference

### 5. **CLAUDE.md** (Project-level)
- High-level architecture
- Project vision
- Key design decisions

---

## Commit Message Convention

Every commit should reference the feature (if applicable):

```bash
# ✅ GOOD - References feature
git commit -m "feat(feature-dark-mode): add theme toggle component

Implemented theme toggle with system preference detection.
Users can now switch between light/dark/auto modes.

Part of feature-dark-mode

🤖 Generated with Claude Code"

# ❌ BAD - No context
git commit -m "fixed stuff"
```

---

## Release Checklist

Before publishing to PyPI:

- [ ] All features documented in SDK docs
- [ ] CLI commands tested and documented
- [ ] Plugin skills updated (if applicable)
- [ ] Examples added to `docs/` or `examples/`
- [ ] Tests pass (`uv run pytest`)
- [ ] Version bumped in `pyproject.toml`
- [ ] CHANGELOG.md updated (if exists)
- [ ] Git commits pushed to remote
- [ ] Package built (`uv build`)
- [ ] Package published (`source .env && uv publish --token "$PyPI_API_TOKEN"`)
- [ ] GitHub release created (optional)
- [ ] Documentation site updated (if exists)

**Key:** Every release should expand what users can do!

---

## Summary

**The Golden Rule:**

> "If we can't ship it in the package, we shouldn't do it in development."

**Why this matters:**

1. **Trust** - Users can trust that we use HtmlGraph the way we recommend
2. **Quality** - We experience the same UX as users
3. **Documentation** - Our development IS the documentation
4. **Examples** - Our workflow IS the examples
5. **Bugs** - We find bugs before users do
6. **Features** - We only add features we actually need

**HtmlGraph tracking HtmlGraph = Best possible testing and documentation.**

---

## Questions?

If you're unsure whether an action is replicable:

1. Ask: "Could a user do this with just the PyPI package?"
2. If NO: Refactor to use SDK/CLI/Plugin
3. If YES: Great! Document it as an example

**When in doubt, dogfood it!** 🐶
