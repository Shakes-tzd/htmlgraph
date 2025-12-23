# HtmlGraph Skill for Codex

This skill enables HtmlGraph session tracking and work continuity in OpenAI Codex.

## Installation

### 1. Install Codex

```bash
npm install -g @openai/codex
```

### 2. Install HtmlGraph

```bash
pip install htmlgraph>=0.8.0
```

### 3. Install This Skill

```bash
# Copy skill to Codex skills directory
mkdir -p ~/.codex/skills/
cp -r packages/codex-skill ~/.codex/skills/htmlgraph
```

### 4. Verify Installation

```bash
codex
# Inside Codex:
$htmlgraph-status
```

## Usage

### Check Status
```bash
$htmlgraph-status
```

Shows:
- Current session information
- Active features
- Project progress
- Previous session summary

### Work with Features
```bash
# List features
$htmlgraph-feature list

# Start a feature
$htmlgraph-feature start feat-abc123

# Complete a feature
$htmlgraph-feature complete feat-abc123
```

### View Sessions
```bash
# List all sessions
$htmlgraph-session list

# View current session
$htmlgraph-session current
```

## Work Continuity Testing

This skill is designed to test HtmlGraph's work continuity across different AI assistants:

1. **Start work in Claude Code**:
   ```bash
   # Claude Code automatically tracks via htmlgraph-tracker skill
   ```

2. **Switch to Codex**:
   ```bash
   codex
   $htmlgraph-status  # See previous session context
   ```

3. **Continue work in Codex**:
   - All activity is tracked to `.htmlgraph/sessions/`
   - Feature attribution continues
   - Drift detection works across tools

4. **Switch back to Claude Code**:
   - Session continuity maintained
   - Full context preserved

## How It Works

HtmlGraph uses git hooks to track activity:

- **Pre-commit**: Captures file changes and commit context
- **Post-commit**: Records commit completion
- **Session tracking**: Automatic via `.htmlgraph/sessions/`

All tracking is tool-agnostic, so switching between Claude Code, Codex, and Gemini preserves full context.

## See Also

- [HtmlGraph Documentation](../../docs/)
- [SDK for AI Agents](../../docs/SDK_FOR_AI_AGENTS.md)
- [Workflow Guide](../../docs/WORKFLOW.md)
