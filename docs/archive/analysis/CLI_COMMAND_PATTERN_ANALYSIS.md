# HtmlGraph CLI Command Pattern Analysis

**Date:** 2026-01-05
**Scope:** Command structure, initialization, development mode, session continuation, and configuration patterns
**Focus:** Understanding how `htmlgraph claude --init/--dev/--continue` works and system prompt management

---

## Executive Summary

HtmlGraph uses **argparse-based CLI** with a sophisticated multi-level command hierarchy. The `claude` command is a specialized integration for Claude Code that supports:

1. **`--init`** - Install plugin + inject orchestrator system prompt
2. **`--dev`** - Load plugin from local development directory
3. **`--continue`** - Resume last session with plugin + orchestrator rules
4. **Default** - Start Claude with orchestrator rules only

The system prompt management uses:
- **File-based storage** - `orchestrator-system-prompt-optimized.txt` (packaged with Python library)
- **Plugin rules injection** - `packages/claude-plugin/rules/orchestration.md`
- **Subprocess delegation** - `subprocess.run(["claude", ...])` with `--append-system-prompt`

---

## 1. Command Structure & Architecture

### Entry Point

**Location:** `/Users/shakes/DevProjects/htmlgraph/src/python/htmlgraph/cli.py`

**pyproject.toml configuration:**
```toml
[project.scripts]
htmlgraph = "htmlgraph.cli:main"
htmlgraph-deploy = "htmlgraph.scripts.deploy:main"
```

This routes `htmlgraph` command → `cli.py:main()` function.

### Parser Architecture

The CLI uses **nested argparse with subparsers**:

```python
parser = argparse.ArgumentParser(description="HtmlGraph - HTML is All You Need")

# Global flags (work across ALL commands)
parser.add_argument("--format", choices=["text", "json"], default="text")
parser.add_argument("--quiet", "-q", action="store_true")
parser.add_argument("--verbose", "-v", action="count", default=0)

# Command routing via subparsers
subparsers = parser.add_subparsers(dest="command", help="Command to run")
```

**Key design principle:** Global flags work across all subcommands, individual subcommands have their own flags.

---

## 2. The `claude` Command in Detail

### Location & Definition

**Line 4150-4395** in `/src/python/htmlgraph/cli.py`

**Parser setup (line 5869-5889):**
```python
claude_parser = subparsers.add_parser(
    "claude", help="Start Claude Code with HtmlGraph integration"
)
claude_group = claude_parser.add_mutually_exclusive_group()
claude_group.add_argument("--init", action="store_true", ...)
claude_group.add_argument("--continue", dest="continue_session", action="store_true", ...)
claude_group.add_argument("--dev", action="store_true", ...)
claude_parser.set_defaults(func=cmd_claude)
```

### Command Invocations

| Command | Purpose | What It Does |
|---------|---------|--------------|
| `htmlgraph claude` | Default start | Launches Claude + injects orchestrator rules only |
| `htmlgraph claude --init` | Fresh setup | Install/upgrade plugin + inject orchestrator system prompt |
| `htmlgraph claude --continue` | Resume session | Reload plugin + inject orchestrator rules |
| `htmlgraph claude --dev` | Dev mode | Load plugin from `packages/claude-plugin/.claude-plugin` |

---

## 3. System Prompt Management

### Storage Locations

**Primary system prompt file:**
```
src/python/htmlgraph/orchestrator-system-prompt-optimized.txt
```

**Location in code:**
```python
prompt_file = (
    Path(__file__).parent / "orchestrator-system-prompt-optimized.txt"
)
if prompt_file.exists():
    system_prompt = prompt_file.read_text(encoding="utf-8")
```

**Orchestration rules (secondary source):**
```
packages/claude-plugin/rules/orchestration.md
```

**Loading pattern:**
```python
rules_file = (
    Path(__file__).parent.parent.parent.parent
    / "packages"
    / "claude-plugin"
    / "rules"
    / "orchestration.md"
)
orchestration_rules = ""
if rules_file.exists():
    orchestration_rules = rules_file.read_text(encoding="utf-8")
```

### Prompt Combination Strategy

The system concatenates two sources:

```python
combined_prompt = system_prompt  # Primary (orchestrator-system-prompt-optimized.txt)
if orchestration_rules:
    combined_prompt = f"{system_prompt}\n\n---\n\n{orchestration_rules}"
```

**Result:** Complete prompt = optimized system prompt + detailed orchestration rules

### Fallback Behavior

If `orchestrator-system-prompt-optimized.txt` doesn't exist (for installations without source repo):

```python
else:
    # Fallback: provide minimal orchestrator guidance
    system_prompt = textwrap.dedent("""
        You are an AI orchestrator for HtmlGraph project development.

        CRITICAL DIRECTIVES:
        1. DELEGATE to subagents - do not implement directly
        2. CREATE work items before delegating (features, bugs, spikes)
        3. USE SDK for tracking - all work must be tracked in .htmlgraph/
        4. RESPECT dependencies - check blockers before starting
        ...
    """)
```

---

## 4. Claude Code Integration

### How It Launches Claude Code

All `claude` subcommands use subprocess to invoke the Claude CLI:

```python
try:
    subprocess.run(cmd, check=False)
except FileNotFoundError:
    print("Error: 'claude' command not found.", file=sys.stderr)
    print("Please install Claude Code CLI: https://code.claude.com", file=sys.stderr)
    sys.exit(1)
```

### Command Construction

The command is built dynamically based on flags:

**Default (no flags):**
```python
cmd = ["claude"]
if orchestration_rules:
    cmd.extend(["--append-system-prompt", orchestration_rules])
```

**With `--init`:**
```python
install_htmlgraph_plugin(args)  # Step 1: Install plugin
system_prompt = # Load from file
combined_prompt = f"{system_prompt}\n\n---\n\n{orchestration_rules}"
cmd = ["claude", "--append-system-prompt", combined_prompt]
```

**With `--continue`:**
```python
install_htmlgraph_plugin(args)  # Step 1: Install plugin
cmd = ["claude", "--resume"]
if orchestration_rules:
    cmd.extend(["--append-system-prompt", orchestration_rules])
if plugin_dir.exists():
    cmd.extend(["--plugin-dir", str(plugin_dir)])
```

**With `--dev`:**
```python
plugin_dir = Path(__file__).parent.parent.parent.parent / "packages" / "claude-plugin" / ".claude-plugin"
system_prompt = # Load from file
combined_prompt = f"{system_prompt}\n\n---\n\n{orchestration_rules}"
cmd = [
    "claude",
    "--plugin-dir", str(plugin_dir),
    "--append-system-prompt", combined_prompt,
]
```

### Plugin Installation Flow

**Location:** Lines 4068-4148 in `cli.py`

**Three-step process:**

1. **Update marketplace** (non-blocking):
   ```bash
   claude plugin marketplace update htmlgraph
   ```

2. **Try update first** (for already-installed plugins):
   ```bash
   claude plugin update htmlgraph
   ```

3. **Fallback to install** (if not installed):
   ```bash
   claude plugin install htmlgraph
   ```

---

## 5. Project Initialization (`--init` flag)

### Location & Definition

**Lines 150-400+** in `cli.py` (`cmd_init` function)

### Initialization Flow

```
htmlgraph init [DIR] [FLAGS]
    ├── Create .htmlgraph directory structure
    ├── Initialize features/, spikes/, sessions/, events/, tracks/ subdirectories
    ├── Create analytics index (index.sqlite)
    ├── Update .gitignore with HtmlGraph cache entries
    ├── Install Git hooks (optional: --install-hooks)
    ├── Generate documentation (AGENTS.md, CLAUDE.md, GEMINI.md)
    └── Create initial configuration
```

### What Gets Created

**Directory structure:**
```
.htmlgraph/
├── features/              # Feature tracking
├── spikes/               # Research spikes
├── sessions/             # Session tracking
├── events/               # Event log (one .jsonl per day)
├── tracks/               # Track/conductor-style planning
├── index.sqlite          # Analytics cache (if --no-index not set)
└── orchestrator-mode.json # Orchestrator configuration
```

**Git hooks installed:**
- `post-commit` - Track commits
- `post-merge` - Track merges
- Custom hooks from Claude plugin

**Documentation generated:**
- `AGENTS.md` - SDK/API documentation
- `CLAUDE.md` - Claude Code platform notes
- `GEMINI.md` - Gemini platform notes

### Configuration Options

```bash
htmlgraph init [DIR]                    # Basic init
htmlgraph init --interactive            # Interactive wizard
htmlgraph init --no-index               # Skip analytics cache
htmlgraph init --no-update-gitignore    # Don't update .gitignore
htmlgraph init --install-hooks          # Install Git hooks
```

---

## 6. Development Mode (`--dev` flag)

### Purpose

Load the Claude plugin from **local development directory** instead of installed package.

### Plugin Directory Resolution

```python
plugin_dir = (
    Path(__file__).parent.parent.parent.parent  # src/python/htmlgraph/
    / "packages"
    / "claude-plugin"
    / ".claude-plugin"
)
```

**Resolves to:** `packages/claude-plugin/.claude-plugin/`

This directory contains:
- `plugin.json` - Plugin manifest
- `marketplace.json` - Marketplace configuration
- Commands, agents, hooks, skills (symlinks to actual files)

### How Dev Mode Works

```python
if args.dev:
    if not plugin_dir.exists():
        error: "Plugin directory not found"

    # Load system prompt
    system_prompt = load_optimized_prompt()
    combined_prompt = f"{system_prompt}\n\n---\n\n{orchestration_rules}"

    # Build command with plugin directory
    cmd = [
        "claude",
        "--plugin-dir", str(plugin_dir),  # Load plugin from here
        "--append-system-prompt", combined_prompt,
    ]
    subprocess.run(cmd)
```

### User Feedback

When starting in dev mode:
```
============================================================
🔧 HtmlGraph Development Mode
============================================================

Loading plugin from: packages/claude-plugin/.claude-plugin
  ✓ Skills, agents, and hooks will be loaded from local files
  ✓ Orchestrator system prompt will be appended
  ✓ Multi-AI delegation rules will be injected
  ✓ Changes to plugin files will take effect after restart
```

---

## 7. Session Continuation (`--continue` flag)

### Purpose

Resume the last Claude Code session with:
1. Plugin automatically loaded
2. Orchestrator rules injected
3. Full session context restored

### Implementation

```python
elif args.continue_session:
    install_htmlgraph_plugin(args)  # Step 1: Ensure plugin is up-to-date

    plugin_dir = ... / "packages" / "claude-plugin" / ".claude-plugin"

    cmd = ["claude", "--resume"]

    # Inject orchestration rules
    if orchestration_rules:
        cmd.extend(["--append-system-prompt", orchestration_rules])

    # Load plugin if available
    if plugin_dir.exists():
        cmd.extend(["--plugin-dir", str(plugin_dir)])

    subprocess.run(cmd)
```

---

## 8. Configuration & State Management

### `.htmlgraph/` Directory

**Central state directory** for all HtmlGraph operations.

**Key files:**

```
.htmlgraph/
├── orchestrator-mode.json     # Orchestrator configuration
├── index.sqlite               # Analytics cache (rebuilt daily)
├── features/                  # Feature files (.html)
├── spikes/                    # Spike files (.html)
├── sessions/                  # Session tracking (.html)
├── events/                    # Event logs (.jsonl)
└── tracks/                    # Track definitions (.html)
```

### Configuration Sources (Priority Order)

1. **Command-line arguments** (highest priority)
   - `--format json`, `--quiet`, `--verbose`
   - `--graph-dir .htmlgraph` (default)

2. **Environment variables** (medium priority)
   - Set by hooks for parent-child session linking
   - Used for orchestrator mode detection

3. **File defaults** (lowest priority)
   - `.htmlgraph/orchestrator-mode.json`
   - `.claude/` directory (Claude Code plugin settings)

### State Persistence

**Sessions are tracked via HtmlGraph SDK:**

```python
from htmlgraph import SDK
sdk = SDK(directory=".htmlgraph", agent="claude-code")

# Track session start
session = sdk.session_manager.start(
    agent="claude-code",
    context={"mode": "orchestrator"}
)

# Record activities during session
sdk.session_manager.add_activity(
    tool_name="Bash",
    summary="Deployed changes"
)
```

---

## 9. Command Parsing & Execution Flow

### Main Function Flow (Lines 4397-5920+)

```python
def main() -> None:
    # 1. Create parser with global flags
    parser = argparse.ArgumentParser(...)
    parser.add_argument("--format", ...)
    parser.add_argument("--quiet", ...)
    parser.add_argument("--verbose", ...)

    # 2. Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command")

    # 3. Define each command's parser
    serve_parser = subparsers.add_parser("serve", ...)
    init_parser = subparsers.add_parser("init", ...)
    claude_parser = subparsers.add_parser("claude", ...)
    # ... etc for session, feature, track, etc.

    # 4. Parse arguments
    args = parser.parse_args()

    # 5. Dispatch to handler
    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "claude":
        cmd_claude(args)
    # ... etc
```

### Argument Handling Pattern

**Each command function receives `argparse.Namespace`:**

```python
def cmd_claude(args: argparse.Namespace) -> None:
    # Access parsed arguments
    if args.init:
        # Handle --init
    elif args.continue_session:
        # Handle --continue
    elif args.dev:
        # Handle --dev
    else:
        # Handle default
```

---

## 10. Files & Locations Summary

### Core Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/python/htmlgraph/cli.py` | Main CLI module | ~6000 |
| `src/python/htmlgraph/cli_framework.py` | BaseCommand class | ~116 |
| `src/python/htmlgraph/cli_commands/feature.py` | Feature commands | 152 |
| `src/python/htmlgraph/orchestrator-system-prompt-optimized.txt` | System prompt | 299 |

### Plugin Files

| File | Purpose |
|------|---------|
| `packages/claude-plugin/.claude-plugin/plugin.json` | Plugin manifest |
| `packages/claude-plugin/rules/orchestration.md` | Orchestration rules |
| `packages/claude-plugin/commands/` | Slash commands |
| `packages/claude-plugin/agents/` | Specialized agents |
| `packages/claude-plugin/hooks/` | Claude Code hooks |
| `packages/claude-plugin/skills/` | Extended functionality |

### Configuration

| Location | Purpose |
|----------|---------|
| `.htmlgraph/orchestrator-mode.json` | Project orchestrator config |
| `.claude/settings.json` | Claude Code plugin settings |
| `.claude/hooks/` | Custom hooks directory |
| `.gitignore` | Excludes session tracking files |

---

## 11. System Prompt Management Architecture

### Design Pattern: File-Based + Subprocess Injection

**Why this approach?**
1. **Persistence** - Prompt stored in filesystem, survives reinstalls
2. **Distribution** - Packaged with Python library
3. **Subprocess isolation** - Child Claude process gets complete context
4. **Version control** - Tracked in git, synchronized via `sync-docs`

### Loading Hierarchy

```
1. Check for orchestrator-system-prompt-optimized.txt
   └─ Exists: Use it (primary source)
   └─ Missing: Use fallback prompt (minimal orchestrator guidance)

2. Load orchestration.md from plugin
   └─ Combine: {system_prompt}\n\n---\n\n{orchestration_rules}

3. Pass combined prompt to Claude via subprocess
   subprocess.run(["claude", "--append-system-prompt", combined_prompt])
```

### Synchronization Strategy

The prompt is synchronized across platforms via `sync-docs` command:

```bash
uv run htmlgraph sync-docs
```

This keeps three files in sync:
- `AGENTS.md` (single source of truth)
- `CLAUDE.md` (Claude-specific notes)
- `GEMINI.md` (Gemini-specific notes)

---

## 12. Recommendations for System Prompt Management

### Current Design Strengths

✅ **File-based storage** - Survives reinstalls, version-controlled
✅ **Subprocess isolation** - Complete context passed to Claude
✅ **Fallback mechanism** - Works even if file missing
✅ **Extensible** - Orchestration rules combined with system prompt
✅ **Development-friendly** - Dev mode loads from local files

### Potential Improvements

1. **Separate Concerns**
   - System prompt (initialization, directives)
   - Orchestration rules (specific patterns, examples)
   - Platform-specific adaptations (Claude vs Gemini vs Copilot)

2. **Configuration Versioning**
   - Track prompt version in metadata
   - Support prompt rollback if needed

3. **Environment-Specific Prompts**
   - Different prompts for `--init` vs `--continue` vs `--dev`
   - Dynamic prompt generation based on project state

4. **Plugin Integration**
   - Consider storing prompt in plugin.json manifest
   - Allow plugin version to control prompt version

5. **Validation**
   - Validate prompt syntax before passing to Claude
   - Check for dangerous patterns or unintended modifications

---

## 13. Command Examples & Usage Patterns

### Example: Starting with Orchestrator

```bash
# Initialize project and start Claude with orchestrator mode
htmlgraph init
htmlgraph claude --init
```

**What happens:**
1. `init` creates `.htmlgraph/` structure
2. `claude --init` installs/upgrades plugin
3. Claude starts with orchestrator system prompt + rules

### Example: Development Workflow

```bash
# Start dev mode (load plugin from local files)
htmlgraph claude --dev

# Make changes to plugin files in packages/claude-plugin/
# Restart Claude to reload changes

htmlgraph claude --dev  # Changes take effect
```

### Example: Resuming Work

```bash
# Resume last session with plugin and rules
htmlgraph claude --continue
```

### Example: JSON Output

```bash
# Get session info in JSON format
htmlgraph session start-info --format json
```

---

## 14. Testing & Validation

### CLI Tests

Location: `tests/python/test_orchestrator_cli.py`

**Key test areas:**
- Parser argument handling
- Command dispatch
- System prompt loading
- Plugin installation
- Session continuation
- Development mode

### Manual Testing Commands

```bash
# Test --init
uv run htmlgraph init --interactive

# Test --dev
uv run htmlgraph claude --dev

# Test --continue
uv run htmlgraph claude --continue

# Test default (no flags)
uv run htmlgraph claude

# Test with JSON output
uv run htmlgraph session start-info --format json

# Test verbose
uv run htmlgraph claude --init --verbose
```

---

## Conclusion

HtmlGraph's CLI uses a **sophisticated but maintainable architecture** based on argparse with:

1. **Multi-level command hierarchy** - Main command + subcommands + nested subcommands
2. **Global flags** - `--format`, `--quiet`, `--verbose` work everywhere
3. **Specialized command handlers** - Each command is a separate function
4. **File-based configuration** - System prompts, orchestration rules stored on filesystem
5. **Subprocess delegation** - Claude Code invoked via subprocess with full context
6. **Plugin integration** - Plugin installed/upgraded via `claude plugin` commands
7. **Session tracking** - All work tracked in `.htmlgraph/` via HtmlGraph SDK

The system prompt management pattern is **clean and extensible**, supporting:
- File-based persistence
- Fallback mechanisms
- Subprocess isolation
- Platform-specific adaptation
- Development mode with local files

This design allows HtmlGraph to bootstrap orchestrator mode effectively while maintaining flexibility for different use cases.
