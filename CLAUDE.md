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

**CRITICAL: ALL Claude Code integrations (hooks, agents, skills) must be built in the PLUGIN SOURCE.**

**Plugin Source:** `packages/claude-plugin/.claude-plugin/`
**Do NOT edit:** `.claude/` directory (auto-synced from plugin)

### Plugin Components - What Belongs in the Plugin

Everything that extends Claude Code functionality should be in `packages/claude-plugin/.claude-plugin/`:

#### 1. **Hooks** (All CloudEvent handlers)
   - **Location:** `packages/claude-plugin/.claude-plugin/hooks/`
   - **What:** Python scripts that respond to Claude Code events
   - **Examples:**
     - `session-start.py` - Runs when Claude Code session starts
     - `user-prompt-submit.py` - Runs when user submits a prompt (creates UserQuery events)
     - `track-event.py` - Records all tool calls and completions to database
     - `pretooluse-spawner-router.py` - Routes Task() calls to spawner agents
     - `session-end.py` - Cleanup when session ends
     - `subagent-stop.py` - Handles subagent completion
   - **Why plugin:** Hooks are Claude Code infrastructure—must be packaged for distribution

#### 2. **Subagent Agents** (AI agents spawned via Task())
   - **Location:** `packages/claude-plugin/.claude-plugin/agents/`
   - **What:** Python executables that run as autonomous subagents
   - **Current Examples:**
     - `gemini-spawner.py` - Routes exploration tasks to Google Gemini (FREE)
     - `codex-spawner.py` - Routes code implementation to OpenAI Codex
     - `copilot-spawner.py` - Routes git/GitHub operations to GitHub Copilot
   - **Pattern:** All must track their own activities via `spawner_event_tracker.py`
   - **Why plugin:** Agents are re-usable across projects, distributed with plugin

#### 3. **Skills** (User-invocable commands)
   - **Location:** `packages/claude-plugin/.claude-plugin/skills/`
   - **What:** Markdown skill definitions + embedded Python for orchestration
   - **Current Examples:**
     - `/orchestrator-directives` - Delegation patterns
     - `/multi-ai-orchestration` - Spawner model selection
     - `/code-quality` - Quality gate workflow
     - `/deployment-automation` - Release process
     - `/debugging-workflow` - Debug methodology
     - `/memory-sync` - Doc synchronization
   - **Why plugin:** Skills are Claude Code UI components—must be packaged for distribution

#### 4. **Plugin Configuration**
   - **Location:** `packages/claude-plugin/.claude-plugin/plugin.json`
   - **What:** Plugin metadata, agent definitions, capabilities
   - **Includes:**
     - Plugin name, version, description
     - Agent registry (name → executable mapping)
     - MCP server configurations
     - Capabilities and model info
   - **Why plugin:** Defines how Claude Code loads and runs the plugin

#### 5. **Configuration & Prompts**
   - **Location:** `packages/claude-plugin/.claude-plugin/config/`
   - **What:** System prompts, classification rules, drift thresholds
   - **Examples:**
     - `classification-prompt.md` - Prompt for work type classification
     - `drift-config.json` - Context drift detection settings
   - **Why plugin:** Shared across all users; updates distributed via plugin

### Directory Structure

```
packages/claude-plugin/.claude-plugin/  <-- SOURCE (make changes here)
├── hooks/
│   ├── hooks.json                   ← Hook event routing
│   └── scripts/
│       ├── session-start.py         ← Database session creation
│       ├── user-prompt-submit.py    ← UserQuery event creation
│       ├── track-event.py           ← All event tracking
│       ├── pretooluse-spawner-router.py  ← Task() delegation routing
│       ├── posttooluse-integrator.py     ← Activity linking
│       ├── session-end.py           ← Session cleanup
│       └── subagent-stop.py         ← Subagent completion
├── agents/
│   ├── gemini-spawner.py            ← Gemini exploration agent
│   ├── codex-spawner.py             ← Code implementation agent
│   ├── copilot-spawner.py           ← Git/GitHub agent
│   └── spawner_event_tracker.py     ← Child activity recording
├── skills/
│   ├── orchestrator-directives/     ← Delegation patterns
│   ├── multi-ai-orchestration/      ← Spawner selection
│   ├── code-quality/                ← Quality gates
│   ├── deployment-automation/       ← Release workflow
│   ├── debugging-workflow/          ← Debug methodology
│   └── memory-sync/                 ← Doc synchronization
├── config/
│   ├── classification-prompt.md     ← Work classification AI
│   └── drift-config.json            ← Drift thresholds
└── plugin.json                      ← Plugin metadata

.claude/  <-- AUTO-SYNCED (do not edit)
├── hooks/ (synced from plugin)
├── agents/ (synced from plugin)
├── skills/ (synced from plugin)
└── config/ (synced from plugin)
```

### Critical Rule: Single Source of Truth

**NEVER edit `.claude/` expecting changes to persist.**

- ❌ Edit `.claude/hooks/hooks.json` → Changes lost on plugin update
- ❌ Edit `.claude/hooks/scripts/*.py` → Changes lost on plugin update
- ❌ Edit `.claude/agents/` → Changes lost on plugin update
- ❌ Add hooks to `.claude/` → Not published, not shareable

**ALWAYS edit in plugin source:**

- ✅ Edit `packages/claude-plugin/.claude-plugin/hooks/hooks.json`
- ✅ Edit `packages/claude-plugin/.claude-plugin/hooks/scripts/*.py`
- ✅ Add agents to `packages/claude-plugin/.claude-plugin/agents/`
- ✅ Add skills to `packages/claude-plugin/.claude-plugin/skills/`

### Workflow: Making Changes to Plugin

1. **Make changes in plugin source:**
   ```bash
   # Edit files in packages/claude-plugin/.claude-plugin/
   vim packages/claude-plugin/.claude-plugin/hooks/scripts/user-prompt-submit.py
   vim packages/claude-plugin/.claude-plugin/plugin.json
   ```

2. **Run quality checks:**
   ```bash
   uv run ruff check --fix && uv run ruff format && uv run mypy src/ && uv run pytest
   ```

3. **Verify plugin is synced (in dev mode, hooks run from plugin source):**
   ```bash
   # In dev mode, Claude Code runs hooks from plugin source directly
   # No need to manually sync during development
   ```

4. **Commit changes:**
   ```bash
   git add packages/claude-plugin/.claude-plugin/
   git commit -m "fix: update hook X with Y changes"
   ```

5. **Deploy (publishes plugin update):**
   ```bash
   ./scripts/deploy-all.sh 0.9.7 --no-confirm
   # This updates version in plugin.json and publishes to distribution

### Never Do This

- Edit `.claude/hooks/hooks.json` directly
- Edit `.claude/hooks/scripts/*.py` directly
- Edit `.claude/agents/` directly
- Add new hooks to `.claude/` expecting them to run
- Make changes to `.claude/` expecting them to persist

### Always Do This

- Edit `packages/claude-plugin/.claude-plugin/hooks/hooks.json`
- Edit `packages/claude-plugin/.claude-plugin/hooks/scripts/*.py`
- Add agents to `packages/claude-plugin/.claude-plugin/agents/`
- Add skills to `packages/claude-plugin/.claude-plugin/skills/`
- Commit plugin source files
- Test in dev mode (hooks run from plugin automatically)

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
