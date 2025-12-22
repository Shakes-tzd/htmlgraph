# AI CLI Platforms Comparison

HtmlGraph supports three major AI CLI platforms: **Claude Code**, **Codex CLI**, and **Gemini CLI**. This document compares their capabilities and how HtmlGraph integrates with each.

---

## Quick Comparison Matrix

| Feature | Claude Code | Codex CLI | Gemini CLI |
|---------|-------------|-----------|------------|
| **Automatic Hooks** | ✅ Yes | ❌ No | ✅ Yes |
| **Session Management** | Automatic | Manual | Automatic |
| **Integration Type** | Plugin | Skill | Extension |
| **Hook Events** | Pre/PostToolUse, SessionStart | N/A | SessionStart, AfterTool, SessionEnd |
| **SDK Access** | Bash tool | Bash tool | Bash tool |
| **Context Format** | SKILL.md | SKILL.md | GEMINI.md |
| **Installation** | Plugin marketplace | Skill directory | Extension system |
| **MCP Support** | Yes | Yes | Yes |

---

## Platform Details

### 1. Claude Code (by Anthropic)

**Integration:** Plugin via marketplace

**Hooks System:** ✅ **Comprehensive**
- `PreToolUse` - Before any tool execution
- `PostToolUse` - After any tool execution
- `SessionStart` - When session begins
- Plugin-level hooks in `.claude-plugin/hooks/`

**Session Management:** ✅ **Automatic**
- Hooks handle session start/end automatically
- Activities tracked to in-progress features
- No manual intervention needed

**Installation:**
```bash
# From official marketplace
/plugin install htmlgraph

# From local marketplace (development)
/plugin marketplace add .
/plugin install htmlgraph@htmlgraph-dev
```

**Setup Command:**
```bash
htmlgraph setup claude
```

**Best For:**
- Production use with automatic tracking
- Teams using Claude Code as primary IDE
- Projects requiring zero manual overhead

**Package Location:** `packages/claude-plugin/`

---

### 2. Codex CLI (by OpenAI)

**Integration:** Skill via `.codex/skills/`

**Hooks System:** ❌ **Not Available**
- No plugin/extension hooks
- No lifecycle events
- Skills are prompt-based only

**Session Management:** ❌ **Manual**
- Agents must explicitly start sessions
- Agents must explicitly end sessions
- Skill contains mandatory session lifecycle instructions

**Manual Session Commands:**
```bash
# START OF EVERY SESSION
uv run htmlgraph session start --agent codex

# END OF EVERY SESSION
uv run htmlgraph session end <session-id>
```

**Installation:**
```bash
# Option 1: Link from repo
ln -s /path/to/htmlgraph/packages/codex-skill ~/.codex/skills/htmlgraph-tracker

# Option 2: Copy
cp -r packages/codex-skill ~/.codex/skills/htmlgraph-tracker

# Option 3: From GitHub
git clone https://github.com/Shakes-tzd/htmlgraph.git
cp -r htmlgraph/packages/codex-skill ~/.codex/skills/htmlgraph-tracker
```

**Setup Command:**
```bash
htmlgraph setup codex [--auto-install]
```

**Best For:**
- Codex-only workflows
- Developers comfortable with manual session management
- Projects where Codex is the only AI tool

**Package Location:** `packages/codex-skill/`

**Important Notes:**
- Skill uses very directive language to remind agent to manage sessions
- Session start/end are FIRST and LAST steps in workflow checklist
- Forgetting to manage sessions = lost attribution
- Think of sessions like Git commits - always required

---

### 3. Gemini CLI (by Google)

**Integration:** Extension via `.gemini/extensions/`

**Hooks System:** ✅ **Comprehensive**
- `SessionStart` - Initialize when session begins
- `SessionEnd` - Cleanup when session ends
- `BeforeTool` / `AfterTool` - Validate and track tool execution
- `BeforeModel` / `AfterModel` - Modify LLM requests/responses
- `BeforeAgent` / `AfterAgent` - Intercept agent planning
- `PreCompress` - Save state before context compression
- Extensions bundle hooks via `hooks/hooks.json`

**Session Management:** ✅ **Automatic**
- SessionStart hook auto-starts HtmlGraph session
- AfterTool hook tracks all tool usage
- SessionEnd hook auto-finalizes on exit
- Same automatic workflow as Claude Code!

**Installation:**
```bash
# From GitHub
gemini extensions install https://github.com/Shakes-tzd/htmlgraph/tree/main/packages/gemini-extension

# Link from repo
gemini extensions link packages/gemini-extension

# Copy manually
cp -r packages/gemini-extension ~/.gemini/extensions/htmlgraph
```

**Setup Command:**
```bash
htmlgraph setup gemini [--auto-install]
```

**Best For:**
- Production use with automatic tracking
- Teams using Gemini CLI as primary tool
- Projects requiring Google ecosystem integration
- Developers who want Claude Code-like automation

**Package Location:** `packages/gemini-extension/`

**Hook Configuration:**
```json
{
  "SessionStart": [{
    "name": "htmlgraph-session-start",
    "type": "command",
    "command": "./hooks/scripts/session-start.sh",
    "timeout": 5000
  }],
  "AfterTool": [{
    "name": "htmlgraph-track-activity",
    "type": "command",
    "command": "./hooks/scripts/post-tool.sh",
    "timeout": 3000,
    "matcher": "*"
  }],
  "SessionEnd": [{
    "name": "htmlgraph-session-end",
    "type": "command",
    "command": "./hooks/scripts/session-end.sh",
    "timeout": 5000
  }]
}
```

---

## Common Features Across All Platforms

### ✅ **SDK-First Approach**

All platforms use the Python SDK via Bash to avoid MCP context bloat:

```bash
# All platforms use identical commands
uv run htmlgraph status
uv run htmlgraph feature start feat-123

# SDK via Python
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='claude')  # or 'codex' or 'gemini'
with sdk.features.edit('feat-123') as f:
    f.steps[0].completed = True
"
```

### ✅ **Feature Creation Decision Framework**

All platforms include the same decision framework:

**Create FEATURE if ANY apply:**
- >30 minutes work
- 3+ files
- New tests needed
- Multi-component impact
- Hard to revert
- Needs docs

**Implement DIRECTLY if ALL apply:**
- Single file
- <30 minutes
- Trivial change
- Easy to revert
- No tests needed

### ✅ **Continuous Tracking**

All platforms emphasize:
- Start features before coding
- Mark steps complete immediately
- Update progress in real-time
- Complete features only when verified

### ✅ **Unified Workflow**

All platforms follow the same core workflow:
1. Check status at session start
2. Start/resume feature
3. Mark steps complete as you work
4. Verify completion (tests, attribution, clean code)
5. Complete feature
6. Git commit with feature ID

---

## Installation Summary

### One-Command Setup

```bash
# Set up for specific platform
htmlgraph setup claude
htmlgraph setup codex
htmlgraph setup gemini

# Set up for ALL platforms
htmlgraph setup all
```

The setup command:
- Checks if CLI is installed
- Verifies current installation status
- Provides installation options
- Auto-installs with `--auto-install` flag
- Shows next steps

---

## Architecture Comparison

### Claude Code Plugin

```
.claude-plugin/
├── plugin.json              # Plugin manifest
├── skills/
│   └── htmlgraph-tracker/
│       └── SKILL.md        # Agent instructions
├── commands/
│   └── start.md            # /start command
└── hooks/
    └── scripts/
        ├── session-start.py
        ├── track-event.py
        └── session-end.py
```

**Language:** Python
**Execution:** Automatic via Claude hooks
**Agent Name:** `claude`

### Codex Skill

```
.codex/skills/htmlgraph-tracker/
├── SKILL.md                # Agent instructions
└── README.md              # Installation guide
```

**Language:** Markdown (instructions only)
**Execution:** Manual by agent following instructions
**Agent Name:** `codex`

### Gemini Extension

```
.gemini/extensions/htmlgraph/
├── gemini-extension.json   # Extension manifest
├── GEMINI.md              # Agent instructions
├── hooks/
│   ├── hooks.json         # Hook configuration
│   └── scripts/
│       ├── session-start.sh
│       ├── post-tool.sh
│       └── session-end.sh
└── README.md              # Installation guide
```

**Language:** Shell scripts
**Execution:** Automatic via Gemini hooks
**Agent Name:** `gemini`

---

## Recommendations

### For New Projects

**Use:** Claude Code or Gemini CLI

**Reason:** Automatic session management via hooks eliminates manual overhead and ensures perfect attribution.

### For Existing Codex Projects

**Use:** Codex skill with manual sessions

**Reason:** Works with your existing setup, but requires disciplined session management.

### For Multi-Platform Teams

**Use:** `htmlgraph setup all`

**Reason:** Install all integrations, let each developer use their preferred CLI. The SDK is identical across all platforms.

### For Maximum Automation

**Use:** Claude Code (most mature) or Gemini CLI (newest, most feature-rich hooks)

**Reason:** Both provide comprehensive hook systems with automatic tracking.

---

## Migration Guide

### From Manual Tracking → Automatic (Claude Code or Gemini)

1. Install plugin/extension
2. Remove manual session commands from workflow
3. Hooks handle everything automatically
4. Focus on feature management only

### From Codex → Claude Code

1. Install Claude Code plugin
2. Update agent name: `agent='codex'` → `agent='claude'`
3. Remove manual session management
4. Everything else stays the same

### From Claude Code → Gemini

1. Install Gemini extension
2. Update agent name: `agent='claude'` → `agent='gemini'`
3. Hook behavior is nearly identical
4. Shell scripts vs Python (under the hood, not visible to user)

---

## Future Platforms

HtmlGraph is designed to support any AI CLI with:
- Bash tool access (for SDK usage)
- Context file support (SKILL.md, GEMINI.md, etc.)
- Optional: Hooks system (for automatic tracking)

**Planned:**
- GitHub Copilot CLI integration
- Cursor IDE integration
- Windsurf integration
- Any AI tool with CLI + Bash access

---

## Support

- **Documentation:** https://github.com/Shakes-tzd/htmlgraph
- **SDK Guide:** https://github.com/Shakes-tzd/htmlgraph/blob/main/docs/SDK_FOR_AI_AGENTS.md
- **Issues:** https://github.com/Shakes-tzd/htmlgraph/issues

---

## Summary

| Platform | Session Mgmt | Best For | Maturity |
|----------|-------------|----------|----------|
| **Claude Code** | ✅ Automatic | Production, Teams | Mature |
| **Codex CLI** | ❌ Manual | Codex-only | Experimental |
| **Gemini CLI** | ✅ Automatic | Production, Google ecosystem | New |

**Bottom Line:**
- Want automation? → Claude Code or Gemini CLI
- Using Codex? → Manual sessions work, but require discipline
- Multi-platform team? → Install all three, same SDK everywhere
