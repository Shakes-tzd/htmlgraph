# HtmlGraph Session Tracking

**Description**: HtmlGraph session tracking and work continuity for Codex. Ensures proper activity attribution, feature awareness, and continuous work tracking across sessions.

**Commands**:
- `$htmlgraph-status` - Check current session and feature status
- `$htmlgraph-feature` - List, start, or complete features
- `$htmlgraph-session` - View session history and current work

**Usage**:

Check project status:
```bash
$htmlgraph-status
```

Start working on a feature:
```bash
$htmlgraph-feature start feat-abc123
```

Complete a feature:
```bash
$htmlgraph-feature complete feat-abc123
```

View session history:
```bash
$htmlgraph-session list
```

**Features**:
- Automatic session tracking via git hooks
- Feature-based work attribution
- Cross-session continuity
- Session resume detection
- Drift detection for file changes

**Requirements**:
- Python 3.10+
- HtmlGraph installed (`pip install htmlgraph>=0.8.0`)
- Git repository with `.htmlgraph/` directory

**Installation**:

1. Install HtmlGraph:
```bash
pip install htmlgraph>=0.8.0
```

2. Initialize in your project:
```bash
cd your-project
htmlgraph init
```

3. Copy this skill to Codex skills directory:
```bash
mkdir -p ~/.codex/skills/htmlgraph
cp -r packages/codex-skill/* ~/.codex/skills/htmlgraph/
```

**Session Workflow**:

1. **Session Start** - Automatically detected when you begin working
2. **Feature Attribution** - Activity linked to in-progress features
3. **Session Continuity** - Resume context from previous sessions
4. **Session End** - Auto-tracked via git hooks

**Work Continuity**:

HtmlGraph maintains state across sessions:
- Previous session summary
- Active features and their progress
- File change tracking (drift detection)
- Decision history and context

This enables seamless handoffs between:
- Different AI assistants (Claude Code ↔ Codex ↔ Gemini)
- Different sessions
- Different agents/developers

**See Also**:
- Full documentation: `docs/WORKFLOW.md`
- Python SDK: `docs/SDK_FOR_AI_AGENTS.md`
- Session management: `uv run htmlgraph session --help`
