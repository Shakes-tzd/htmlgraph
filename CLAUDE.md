# HtmlGraph - "HTML is All You Need"

## For AI Agents

**Documentation:** [AGENTS.md](./AGENTS.md) | **Gemini:** [GEMINI.md](./GEMINI.md)

---

## Project Vision

Lightweight graph database built on web standards (HTML, CSS, JS) for AI agent coordination and human observability.

- HTML files = Graph nodes
- Hyperlinks = Graph edges
- CSS selectors = Query language
- Zero dependencies, offline-first

---

## Orchestrator Mode

**Delegate ALL operations except:** `Task()`, `AskUserQuestion()`, `TodoWrite()`, SDK operations.

**For complete patterns:** Use `/orchestrator-directives` skill

---

## Code Quality

```bash
uv run ruff check --fix && uv run ruff format && uv run mypy src/ && uv run pytest
# Commit only when ALL pass
```

**For complete workflow:** Use `/code-quality` skill

---

## Deployment

```bash
uv run pytest                              # Run tests
./scripts/deploy-all.sh 0.9.4 --no-confirm  # Deploy
```

**For complete workflow:** Use `/deployment-automation` skill

---

## Quick Commands

| Task | Command |
|------|---------|
| Run tests | `uv run pytest` |
| Lint | `uv run ruff check --fix` |
| Type check | `uv run mypy src/` |
| Deploy | `./scripts/deploy-all.sh VERSION --no-confirm` |
| Serve dashboard | `uv run htmlgraph serve` |
| Status | `uv run htmlgraph status` |

---

## System Prompt Persistence & Delegation Enforcement

**Automatic context injection across session boundaries with cost-optimal delegation.**

Your project's critical guidance (model selection, delegation patterns, quality gates) persists via `.claude/system-prompt.md` and auto-injects at session start, surviving compact/resume cycles.

**Quick Setup**: Create `.claude/system-prompt.md` with project guidance
**Verification**: Run `uv run pytest tests/hooks/test_system_prompt_persistence.py`
**Test Coverage**: 52 unit tests + 31 integration tests + 8 post-compact tests, 98% coverage

### Documentation Guides

| Guide | Audience | Purpose |
|-------|----------|---------|
| [System Prompt Quick Start](./docs/SYSTEM_PROMPT_QUICK_START.md) | Users | Create and customize your system prompt (5-min setup) |
| [System Prompt Architecture](./docs/SYSTEM_PROMPT_ARCHITECTURE.md) | Developers | Deep technical dive + troubleshooting |
| [Delegation Enforcement Admin Guide](./docs/DELEGATION_ENFORCEMENT_ADMIN_GUIDE.md) | Admins/Teams | Setup and monitor delegation enforcement across your team |
| [System Prompt Developer Guide](./docs/SYSTEM_PROMPT_DEVELOPER_GUIDE.md) | Developers | Extend system with custom layers, hooks, and skills |

**Start here**: [System Prompt Quick Start](./docs/SYSTEM_PROMPT_QUICK_START.md)

---

## Debugging Workflow

**CRITICAL: Research first, implement second.**

```bash
# Built-in debug tools
claude --debug <command>    # Verbose output
/hooks                      # List active hooks
/doctor                     # System diagnostics
```

**For complete workflow:** Use `/debugging-workflow` skill

---

## Memory Sync

**Keep documentation synchronized across platforms.**

```bash
uv run htmlgraph sync-docs           # Sync all files
uv run htmlgraph sync-docs --check   # Check sync status
```

**For complete workflow:** Use `/memory-sync` skill

---

## Dogfooding

This project uses HtmlGraph to develop HtmlGraph. The `.htmlgraph/` directory contains real usage examples.

---

## Hook & Plugin Development

**CRITICAL: All hook and system changes must be made to the PLUGIN SOURCE, not the local `.claude/` directory.**

### Directory Structure

```
packages/claude-plugin/.claude-plugin/  <-- SOURCE (make changes here)
├── hooks/
│   ├── hooks.json
│   └── scripts/
│       ├── session-start.py
│       ├── posttooluse-integrator.py
│       └── ...
├── agents/
├── skills/
└── plugin.json

.claude/  <-- LOCAL COPY (synced from plugin, don't edit directly)
```

### Why This Matters

1. **Publishability** - The plugin at `packages/claude-plugin/` is what gets published
2. **Dogfooding** - We use our own plugin to develop HtmlGraph
3. **Sync** - Changes to `.claude/` are overwritten when plugin is updated

### Workflow

1. Make changes in `packages/claude-plugin/.claude-plugin/`
2. Run `claude plugin update htmlgraph` to sync to `.claude/`
3. Test the changes
4. Commit changes to plugin source

### Never Do This

- Edit `.claude/hooks/hooks.json` directly
- Edit `.claude/hooks/scripts/*.py` directly
- Make changes to `.claude/` expecting them to persist

### Always Do This

- Edit `packages/claude-plugin/.claude-plugin/hooks/hooks.json`
- Edit `packages/claude-plugin/.claude-plugin/hooks/scripts/*.py`
- Sync via `claude plugin update htmlgraph` after changes

---

## Project vs General Tooling

**This project is both:**
1. **HtmlGraph Package Development** - Building the tool itself
2. **HtmlGraph Dogfooding** - Using the tool to build itself

**CLAUDE.md contains:**
- ✅ Project-specific: Deployment, testing, debugging HtmlGraph package
- ✅ Quick reference: Links to skills for general patterns

**Plugin/Skills contain:**
- ✅ General patterns: Orchestration, coordination (for all users)
- ✅ Progressive disclosure: Load details on-demand

---

## Skills Reference

| Skill | Use For |
|-------|---------|
| `/orchestrator-directives` | Delegation patterns, decision framework |
| `/multi-ai-orchestration` | Spawner selection, cost optimization |
| `/code-quality` | Lint, type check, testing workflow |
| `/deployment-automation` | Release, versioning, PyPI publishing |
| `/debugging-workflow` | Research-first debugging methodology |
| `/memory-sync` | Documentation synchronization |

---

## Rules Reference

Detailed rules in `.claude/rules/`:
- `orchestration.md` - Complete orchestrator directives
- `code-hygiene.md` - Quality standards
- `deployment.md` - Release workflow
- `debugging.md` - Debug methodology
- `dogfooding.md` - Self-hosting context
