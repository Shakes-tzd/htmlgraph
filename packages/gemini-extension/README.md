# HtmlGraph Tracker Extension for Gemini CLI

This extension enables HtmlGraph tracking in Google Gemini CLI, ensuring proper activity attribution and continuous work tracking.

## Prerequisites

1. **Gemini CLI** installed:
   ```bash
   npm install -g @google/gemini-cli
   ```

2. **HtmlGraph** installed:
   ```bash
   uv pip install htmlgraph
   ```

3. **Python 3.10+** with `uv` package manager

## Installation

### Option 1: Install from GitHub (Recommended)

```bash
gemini extensions install https://github.com/Shakes-tzd/htmlgraph/tree/main/packages/gemini-extension
```

### Option 2: Clone and Link (For Development)

```bash
# Clone the HtmlGraph repository
git clone https://github.com/Shakes-tzd/htmlgraph.git
cd htmlgraph

# Link the extension to Gemini
gemini extensions link packages/gemini-extension
```

### Option 3: Copy to Gemini Extensions Directory

```bash
# Create extensions directory if it doesn't exist
mkdir -p ~/.gemini/extensions

# Copy the extension
cp -r packages/gemini-extension ~/.gemini/extensions/htmlgraph
```

## Features

This extension provides:

### ✅ **Automatic Session Management**

Unlike Codex CLI, Gemini CLI has a comprehensive hooks system that enables automatic tracking:

- **SessionStart Hook** - Automatically initializes HtmlGraph session when you start Gemini
- **AfterTool Hook** - Automatically tracks all tool usage for activity attribution
- **SessionEnd Hook** - Automatically finalizes session when you exit Gemini

### ✅ **SDK-First Approach**

All operations use the HtmlGraph Python SDK via Bash:

```python
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='gemini')
with sdk.features.edit('feat-123') as f:
    f.steps[0].completed = True
"
```

### ✅ **Feature Creation Decision Framework**

Automatic guidance on when to create features:
- >30 minutes? → Create feature
- 3+ files? → Create feature
- Needs tests? → Create feature
- Simple fix? → Direct commit OK

### ✅ **Continuous Tracking Reminders**

The extension ensures you:
- Start features before coding
- Mark steps complete as you finish them
- Update progress in real-time
- Complete features only when all steps are done

## Usage

Once installed, Gemini will automatically use this extension when working on HtmlGraph-tracked projects.

### Initialize HtmlGraph in Your Project

```bash
cd your-project
uv run htmlgraph init --install-hooks
```

### Start Gemini

```bash
gemini
```

Gemini will:
1. Detect the `.htmlgraph` directory
2. Load the htmlgraph-tracker extension
3. Automatically start a session
4. Show you project status and reminders
5. Track your work continuously

### Manual Extension Commands

You can also manage the extension manually:

```bash
# List installed extensions
gemini extensions list

# Enable/disable extension
gemini extensions enable htmlgraph
gemini extensions disable htmlgraph

# Uninstall extension
gemini extensions uninstall htmlgraph
```

## What This Extension Does

The htmlgraph-tracker extension ensures Gemini:

- ✅ Uses the **Python SDK** for all HtmlGraph operations (never direct file edits)
- ✅ **Automatically manages sessions** via hooks (start, track, end)
- ✅ **Checks status** and shows feature awareness at session start
- ✅ **Tracks all work** continuously, not just at the end
- ✅ **Marks steps complete** immediately after finishing them
- ✅ **Creates features** for non-trivial work using the decision framework
- ✅ **Verifies completion** before marking features done

## Extension Structure

```
gemini-extension/
├── gemini-extension.json    # Extension manifest
├── GEMINI.md               # Instructions for Gemini AI
├── hooks/
│   ├── hooks.json          # Hook configuration
│   └── scripts/
│       ├── session-start.sh  # SessionStart hook
│       ├── post-tool.sh     # AfterTool hook
│       └── session-end.sh   # SessionEnd hook
└── README.md              # This file
```

## Hook Events

The extension uses Gemini CLI's native hooks system:

### SessionStart Hook
- **Event:** Triggered when Gemini session starts
- **Action:** Initializes HtmlGraph session, shows project status
- **Timeout:** 5 seconds

### AfterTool Hook
- **Event:** Triggered after every tool execution
- **Action:** Tracks tool usage for activity attribution
- **Timeout:** 3 seconds
- **Matcher:** `*` (all tools)

### SessionEnd Hook
- **Event:** Triggered when Gemini session ends
- **Action:** Finalizes session and shows summary
- **Timeout:** 5 seconds

## Configuration

The extension works out of the box, but you can customize hooks by editing:

```bash
# Edit hook configuration
code ~/.gemini/extensions/htmlgraph/hooks/hooks.json

# Edit hook scripts
code ~/.gemini/extensions/htmlgraph/hooks/scripts/
```

## Troubleshooting

### Extension Not Loading

Check if extensions are enabled:
```bash
gemini extensions list
gemini extensions enable htmlgraph
```

### HtmlGraph Not Found

Ensure HtmlGraph is installed in your environment:
```bash
uv pip install htmlgraph
uv run htmlgraph --version
```

### Hooks Not Executing

Check hook permissions:
```bash
chmod +x ~/.gemini/extensions/htmlgraph/hooks/scripts/*.sh
```

Verify hooks are registered:
```bash
gemini hooks list
```

### Sessions Not Tracking

Manually check session status:
```bash
uv run htmlgraph session list
uv run htmlgraph status
```

## Differences from Other Platforms

### vs Claude Code Plugin
- **Similarity:** Both have automatic hooks
- **Difference:** Gemini uses shell scripts, Claude uses Python
- **Workflow:** Identical SDK-based approach

### vs Codex Skill
- **Similarity:** Both teach SDK usage
- **Difference:** Gemini has automatic session management, Codex requires manual
- **Benefit:** Less directive reminders needed in Gemini

## Documentation

- **HtmlGraph SDK Guide**: https://github.com/Shakes-tzd/htmlgraph/blob/main/docs/SDK_FOR_AI_AGENTS.md
- **HtmlGraph Project**: https://github.com/Shakes-tzd/htmlgraph
- **Gemini CLI Docs**: https://geminicli.com/docs/
- **Gemini CLI Hooks**: https://geminicli.com/docs/hooks/
- **Gemini Extensions**: https://geminicli.com/docs/extensions/

## Support

For issues or questions:
- **HtmlGraph Issues**: https://github.com/Shakes-tzd/htmlgraph/issues
- **Gemini CLI Issues**: https://github.com/google-gemini/gemini-cli/issues

## License

MIT - Same as HtmlGraph

## Contributing

Contributions welcome! Please ensure any changes:
1. Follow the SDK-first principle
2. Maintain the decision framework
3. Keep hooks lightweight (<5s execution)
4. Test with actual Gemini CLI
5. Update hook scripts for both session and tool tracking

---

**Note**: This extension follows the dogfooding principle - we use HtmlGraph to track HtmlGraph development, so this extension represents our actual workflow with automatic hook-based tracking.
