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

## Development Mode

**CRITICAL: Hooks load htmlgraph from PyPI, not local source, even in dev mode.**

### Starting Dev Mode

```bash
uv run htmlgraph claude --dev
```

This launches Claude Code with:
- Plugin loaded from `packages/claude-plugin/.claude-plugin/`
- Orchestrator system prompt injected
- Multi-AI delegation rules enabled

### How Hooks Load HtmlGraph

**Hook shebangs use:**
```python
#!/usr/bin/env -S uv run --with htmlgraph
```

**Key behavior:**
- `--with htmlgraph` always pulls **latest version from PyPI**
- Even when running from project root, hooks use PyPI package
- No version pinning (always gets latest)
- No need to edit hooks when releasing new versions

### Why PyPI in Dev Mode?

**Testing in production-like environment:**
- Ensures changes work the same way for users
- Catches integration issues before distribution
- No surprises when hooks run in production
- Single source of truth (PyPI package)

### Development Workflow

1. **Make changes** to `src/python/htmlgraph/`
2. **Run tests** locally: `uv run pytest`
3. **Deploy to PyPI**: `./scripts/deploy-all.sh X.Y.Z --no-confirm`
4. **Restart Claude**: Hooks automatically load new version from PyPI
5. **Verify**: Check that changes work correctly

### Session ID Fix (v0.26.3)

**Problem:** PostToolUse hooks don't receive `session_id` in hook_input from Claude Code.

**Solution:** Database fallback query finds session with most recent UserQuery event:
```python
# In src/python/htmlgraph/hooks/context.py
cursor.execute("""
    SELECT session_id FROM agent_events
    WHERE tool_name = 'UserQuery'
    ORDER BY timestamp DESC
    LIMIT 1
""")
```

**Why this works:**
- UserPromptSubmit hooks DO receive `session_id` from Claude Code
- They create UserQuery events with correct session_id
- PostToolUse hooks query database for that session
- All events (UserQuery + tool events) share same session_id

**Verification after restart:**
```bash
sqlite3 .htmlgraph/htmlgraph.db "
SELECT session_id, tool_name, COUNT(*)
FROM agent_events
WHERE session_id = (SELECT session_id FROM sessions ORDER BY created_at DESC LIMIT 1)
GROUP BY tool_name
ORDER BY COUNT(*) DESC;
"
# Should show UserQuery, Bash, Read, etc. all with SAME session_id
```

### Troubleshooting Dev Mode

**Hooks not executing?**
- Check PyPI package is latest: `pip show htmlgraph`
- Verify hooks are executable: `ls -la packages/claude-plugin/.claude-plugin/hooks/scripts/`
- Check hook shebangs: `head -1 packages/claude-plugin/.claude-plugin/hooks/scripts/*.py`

**Session IDs still mismatched?**
- Query database for UserQuery events: `sqlite3 .htmlgraph/htmlgraph.db "SELECT session_id FROM agent_events WHERE tool_name='UserQuery' ORDER BY timestamp DESC LIMIT 1;"`
- Check active sessions: `sqlite3 .htmlgraph/htmlgraph.db "SELECT session_id, status FROM sessions WHERE status='active';"`
- Verify fix is deployed: Check that v0.26.3+ is on PyPI

**Local changes not reflected?**
- Hooks load from PyPI, not local source
- Must deploy to PyPI for hooks to see changes
- Use incremental versions (0.26.2 → 0.26.3 → 0.26.4)

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

## Multi-AI Orchestration via Spawner Agents

**HtmlGraph supports delegating work to multiple AI platforms** through specialized spawner agents. This enables cost-effective, capability-optimized task routing.

### Architecture Overview

The orchestrator automatically selects the best agent for each task based on:
1. **Task Description** - What kind of work is needed (exploration, code generation, git operations)
2. **Agent Capabilities** - What each spawner agent specializes in
3. **Cost Model** - Free vs Paid vs Subscription-included
4. **Availability** - Whether required CLI tools are installed

**Workflow:**
```
User/Orchestrator: "This needs exploration"
         ↓
    Reads agent descriptions (plugin.json)
         ↓
    Selects best agent: gemini-spawner (FREE, exploration)
         ↓
    Task(subagent_type="gemini")
         ↓
    gemini-spawner.py executes
         ↓
    Returns JSON results or error
         ↓
    Error handling: If CLI missing → agent returns error to orchestrator
```

### Three Spawner Agents

#### 1. Gemini Spawner (FREE)
- **File**: `packages/claude-plugin/.claude-plugin/agents/gemini-spawner.py`
- **Use For**: Exploratory research, batch analysis, large-context understanding
- **Model**: Google Gemini 2.0-Flash
- **Context Window**: 2M tokens
- **Cost**: FREE
- **Requires**: `gemini` CLI tool
- **Capabilities**: exploration, analysis, batch_processing

**Example Usage:**
```bash
gemini-spawner.py -p "Analyze codebase and find all API endpoints" \
  --include-directories src/api/ \
  --model gemini-2.0-flash
```

#### 2. Codex Spawner (PAID)
- **File**: `packages/claude-plugin/.claude-plugin/agents/codex-spawner.py`
- **Use For**: Code generation, implementation, file operations with sandbox
- **Model**: OpenAI GPT-4 (Codex)
- **Context Window**: 128K tokens
- **Cost**: Paid (OpenAI credits)
- **Requires**: `codex` CLI tool
- **Capabilities**: code_generation, implementation, file_operations

**Example Usage:**
```bash
codex-spawner.py -p "Implement a REST API for user management" \
  --sandbox workspace-write \
  --model gpt-4-turbo
```

#### 3. Copilot Spawner (SUBSCRIPTION)
- **File**: `packages/claude-plugin/.claude-plugin/agents/copilot-spawner.py`
- **Use For**: GitHub-integrated workflows, git operations, PR handling
- **Model**: GitHub Copilot
- **Context Window**: 100K tokens
- **Cost**: Subscription (GitHub Copilot)
- **Requires**: `gh` (GitHub CLI) tool
- **Capabilities**: github_integration, git_operations, pr_handling

**Example Usage:**
```bash
copilot-spawner.py -p "Create a pull request for feature X" \
  --allow-tool shell git
```

### Agent Selection Matrix

| Task Type | Best Agent | Why | Cost |
|-----------|-----------|-----|------|
| Exploration/Research | Gemini | FREE, 2M context, good at analysis | FREE |
| Code Generation | Codex | Specialized for code, sandbox safe | PAID |
| Git/GitHub Operations | Copilot | Native GitHub integration | INCLUDED |
| Documentation Review | Gemini | Can process large docs, FREE | FREE |
| Implementation | Codex | Code generation + workspace access | PAID |
| Multi-branch Work | Copilot | Git-aware, PR management | INCLUDED |

### Example Workflow: Exploration Task

**Scenario**: You need to understand a large codebase before implementing a feature.

```python
from htmlgraph import SDK, Task

sdk = SDK(agent="orchestrator")

# Delegate exploration to Gemini (FREE)
exploration_result = Task(
    subagent_type="gemini",
    prompt="""
    Explore the codebase and find:
    1. All authentication-related files
    2. Current auth methods used
    3. Where auth is validated
    4. Recommendations for adding OAuth 2.0
    """,
    include_directories=["src/", "docs/"]
)

# Results returned to orchestrator
print(exploration_result)
# → {
#   "success": true,
#   "response": "Found 12 auth-related files...",
#   "model": "gemini-2.0-flash",
#   "cost": 0.0,
#   "agent": "gemini-2.0-flash"
# }
```

### Error Handling: CLI Not Found

If a required CLI is unavailable, the agent returns a transparent error:

**Scenario**: User tries to delegate to Gemini but `gemini` CLI not installed.

```json
{
  "success": false,
  "error": "Gemini CLI not found. Install with: npm install -g @google/generative-ai-cli",
  "agent": "gemini-2.0-flash",
  "duration": 0.1,
  "delegation_event_id": "event-abc123"
}
```

**Orchestrator Response Options:**
1. **Fallback to different agent** - Try Codex if available
2. **Provide installation instructions** - Show user how to install
3. **Use API fallback** - Call service API directly (if supported)
4. **Delegate to another agent** - Try different spawner

### Event Tracking

All spawner agent executions are tracked in HtmlGraph:

```json
{
  "event_id": "event-abc123",
  "event_type": "delegation",
  "agent_id": "orchestrator",
  "tool_name": "Task",
  "context": {
    "spawned_agent": "gemini-2.0-flash",
    "spawner_type": "gemini",
    "model": "gemini-2.0-flash",
    "cost": "FREE"
  },
  "status": "completed",
  "output_summary": "Found 12 auth-related files...",
  "execution_duration_seconds": 15.3,
  "cost_tokens": 0
}
```

### Environment Variables

Spawner agents respect environment variables for parent context:

```bash
# Set by orchestrator before spawning
HTMLGRAPH_PARENT_SESSION=session-xyz
HTMLGRAPH_PARENT_EVENT=event-abc
HTMLGRAPH_PARENT_QUERY_EVENT=query-123
HTMLGRAPH_PARENT_AGENT=orchestrator

# Agent inherits context automatically
gemini-spawner.py -p "Task"
```

This enables session continuity and proper event linking in HtmlGraph.

### Troubleshooting Spawner Agents

See [Multi-AI Orchestration Troubleshooting Guide](#multi-ai-orchestration-troubleshooting) below for:
- Installing required CLIs
- Debugging missing CLI errors
- Fallback strategies
- Testing agent availability
- Performance tips

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

## Multi-AI Orchestration Troubleshooting

### Installing Required CLIs

#### Gemini CLI
**Purpose**: Execute Google Gemini 2.0-Flash spawner agent

**Installation:**
```bash
# Using npm (recommended)
npm install -g @google/generative-ai-cli

# Verify installation
gemini --version
```

**Setup & Authentication:**
```bash
# Set your API key
export GOOGLE_API_KEY="your-api-key-here"

# Or configure persistently
gemini config set api_key "your-api-key-here"

# Verify authentication
gemini chat "Hello"
```

**Get API Key:**
1. Go to https://aistudio.google.com/app/apikeys
2. Create new API key
3. Copy and save securely

#### Codex CLI
**Purpose**: Execute OpenAI Codex spawner agent

**Installation:**
```bash
# Using npm
npm install -g @openai/codex-cli

# Or using pip (if available)
pip install openai-codex-cli

# Verify installation
codex --version
```

**Setup & Authentication:**
```bash
# Set your API key
export OPENAI_API_KEY="sk-..."

# Or configure persistently
codex config set api_key "sk-..."

# Verify authentication
codex chat "Hello"
```

**Get API Key:**
1. Go to https://platform.openai.com/account/api-keys
2. Create new API key
3. Copy and save securely

#### GitHub Copilot CLI (gh)
**Purpose**: Execute GitHub Copilot spawner agent for git operations

**Installation:**
```bash
# Using Homebrew (macOS)
brew install gh

# Using apt (Ubuntu/Debian)
sudo apt update
sudo apt install gh

# Using Chocolatey (Windows)
choco install gh

# Verify installation
gh --version
```

**Setup & Authentication:**
```bash
# Authenticate with GitHub
gh auth login

# Follow prompts:
# 1. Select protocol: HTTPS or SSH
# 2. Authenticate: browser login
# 3. Git credential helper: yes (recommended)

# Verify authentication
gh auth status
```

### Troubleshooting: CLI Not Found Error

**Error Message:**
```json
{
  "success": false,
  "error": "Gemini CLI not found. Install with: npm install -g @google/generative-ai-cli",
  "agent": "gemini-2.0-flash"
}
```

**Solution:**

1. **Check if CLI is installed:**
   ```bash
   # For Gemini
   which gemini
   gemini --version

   # For Codex
   which codex
   codex --version

   # For GitHub CLI
   which gh
   gh --version
   ```

2. **Install missing CLI** - Use commands above for your platform

3. **Verify PATH includes CLI location:**
   ```bash
   echo $PATH
   # Should include: /usr/local/bin, ~/.local/bin, etc.
   ```

4. **For npm-installed tools, verify npm bin directory:**
   ```bash
   npm bin -g
   # Make sure this directory is in PATH
   ```

5. **Retry spawner agent:**
   ```python
   Task(
       subagent_type="gemini",
       prompt="Your task here"
   )
   ```

### Testing Agent Availability

**Check which agents are available:**

```python
from htmlgraph import SDK

sdk = SDK(agent="orchestrator")

# Query plugin configuration
import json
with open("packages/claude-plugin/.claude-plugin/plugin.json") as f:
    config = json.load(f)

print("Available agents:")
for agent_name, agent_config in config["agents"].items():
    requires_cli = agent_config.get("requires_cli")
    print(f"  - {agent_name}: requires '{requires_cli}' CLI")
```

**Test each agent's CLI availability:**

```bash
#!/bin/bash
# test-spawner-availability.sh

echo "=== Checking Spawner Agent Availability ==="

# Gemini
if command -v gemini &> /dev/null; then
    echo "✅ Gemini CLI: available"
    gemini --version
else
    echo "❌ Gemini CLI: NOT FOUND"
    echo "   Install: npm install -g @google/generative-ai-cli"
fi

# Codex
if command -v codex &> /dev/null; then
    echo "✅ Codex CLI: available"
    codex --version
else
    echo "❌ Codex CLI: NOT FOUND"
    echo "   Install: npm install -g @openai/codex-cli"
fi

# GitHub CLI
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI: available"
    gh --version
else
    echo "❌ GitHub CLI: NOT FOUND"
    echo "   Install: brew install gh (or use apt/choco)"
fi
```

### Fallback Strategies

**Strategy 1: Check Agent Before Delegating**

```python
from htmlgraph import SDK, Task
import subprocess

sdk = SDK(agent="orchestrator")

def is_cli_available(cli_name):
    """Check if CLI tool is available."""
    try:
        subprocess.run([cli_name, "--version"],
                      capture_output=True,
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

# Try Gemini first (FREE)
if is_cli_available("gemini"):
    result = Task(
        subagent_type="gemini",
        prompt="Explore codebase"
    )
else:
    # Fallback to Codex
    print("⚠️  Gemini not available, trying Codex...")
    result = Task(
        subagent_type="codex",
        prompt="Explore codebase"
    )
```

**Strategy 2: Cost-Based Fallback**

```python
def delegate_with_cost_optimization(task_type, prompt):
    """Delegate to cheapest available agent."""

    cost_preference = ["gemini", "copilot", "codex"]  # FREE → INCLUDED → PAID

    for agent_type in cost_preference:
        try:
            result = Task(
                subagent_type=agent_type,
                prompt=prompt
            )
            if result.get("success"):
                return result
        except Exception as e:
            print(f"⚠️  {agent_type} failed: {e}")
            continue

    # All agents failed
    raise RuntimeError("No spawner agents available")

# Use it
result = delegate_with_cost_optimization(
    "exploration",
    "Find all API endpoints"
)
```

**Strategy 3: Provide User Guidance**

```python
def delegate_with_fallback(agent_type, prompt):
    """Delegate with helpful error messages."""

    try:
        result = Task(subagent_type=agent_type, prompt=prompt)

        if not result.get("success"):
            error = result.get("error", "Unknown error")

            if "CLI not found" in error:
                print(f"\n⚠️  {agent_type} CLI not installed")

                # Provide installation instructions
                cli_instructions = {
                    "gemini": "npm install -g @google/generative-ai-cli",
                    "codex": "npm install -g @openai/codex-cli",
                    "copilot": "brew install gh (or apt install gh / choco install gh)"
                }

                if agent_type in cli_instructions:
                    print(f"\nInstall with: {cli_instructions[agent_type]}")

                print(f"\nTrying fallback agent...")
                # Recurse with different agent
                fallback_agents = {
                    "gemini": "codex",
                    "codex": "copilot",
                    "copilot": "gemini"
                }

                if agent_type in fallback_agents:
                    return delegate_with_fallback(
                        fallback_agents[agent_type],
                        prompt
                    )

        return result

    except Exception as e:
        print(f"Error: {e}")
        raise
```

### Performance Tips

**1. Cache Agent Availability Check**
```python
import functools
import subprocess

@functools.lru_cache(maxsize=3)
def is_cli_available(cli_name):
    """Cache result for 1 hour (or process lifetime)."""
    try:
        subprocess.run([cli_name, "--version"],
                      capture_output=True,
                      check=True)
        return True
    except:
        return False
```

**2. Batch Tasks for Same Agent**
```python
# ❌ BAD: 3 separate Task calls
Task(subagent_type="gemini", prompt="Task 1")
Task(subagent_type="gemini", prompt="Task 2")
Task(subagent_type="gemini", prompt="Task 3")

# ✅ GOOD: Combine into single batch
Task(
    subagent_type="gemini",
    prompt="""
    Please complete:
    1. Task 1
    2. Task 2
    3. Task 3
    """
)
```

**3. Use Appropriate Agent for Task**
```python
# ❌ BAD: Use expensive Codex for exploration
Task(
    subagent_type="codex",
    prompt="Analyze codebase structure"  # Exploration = Gemini
)

# ✅ GOOD: Use FREE Gemini for exploration
Task(
    subagent_type="gemini",
    prompt="Analyze codebase structure"
)

# Save Codex for code generation
Task(
    subagent_type="codex",
    prompt="Implement new REST endpoint"  # Implementation = Codex
)
```

**4. Monitor Event Tracking**
```python
from htmlgraph import SDK

sdk = SDK(agent="orchestrator")

# Check delegation costs
sessions = sdk.sessions.all()
for session in sessions:
    events = session.get_events()

    for event in events:
        if event.get("event_type") == "delegation":
            agent = event.get("context", {}).get("spawner_type")
            cost = event.get("context", {}).get("cost")
            duration = event.get("execution_duration_seconds")

            print(f"{agent}: {cost} (duration: {duration}s)")
```

---

## Rules Reference

Detailed rules in `.claude/rules/`:
- `orchestration.md` - Complete orchestrator directives
- `code-hygiene.md` - Quality standards
- `deployment.md` - Release workflow
- `debugging.md` - Debug methodology
- `dogfooding.md` - Self-hosting context
