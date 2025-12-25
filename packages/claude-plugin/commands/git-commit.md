# /htmlgraph:git-commit

Commit and push changes using git-commit-push.sh script

## Usage

```
/htmlgraph:git-commit <message>
```

## Parameters

- `message` (required): Commit message (supports multi-line with newlines)
- `skip_confirm` (optional) (default: True): Skip confirmation prompt (recommended for AI agents)


## Examples

```bash
/htmlgraph:git-commit "feat: add new feature"
```
Commit and push with simple message

```bash
/htmlgraph:git-commit "fix(parser): handle edge case"
```
Commit with multi-line message

```bash
/htmlgraph:git-commit "feat(feat-abc123): complete OAuth integration"
```
Commit with feature ID reference



## Instructions for Claude

This command uses the SDK's `None()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**IMPORTANT: This command executes the git-commit-push.sh script.**

**DO THIS:**

1. **Construct the commit message:**
   - Use conventional commit format (feat:, fix:, chore:, etc.)
   - Include feature ID if working on tracked feature
   - Add standard footer for HtmlGraph features:
     ```
     🤖 Generated with Claude Code
     Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
     ```

2. **Execute the script:**
   ```bash
   ./scripts/git-commit-push.sh "{commit_message}" --no-confirm
   ```

3. **Parse the output:**
   - Extract commit hash
   - Count files changed
   - Verify push succeeded

4. **Report success:**
   Use the output template to confirm the commit

**NEVER:**
- ❌ Commit without understanding what changed
- ❌ Use vague commit messages
- ❌ Skip the --no-confirm flag (causes interactive prompt)

**ALWAYS:**
- ✅ Include feature ID in message when working on tracked features
- ✅ Use conventional commit format
- ✅ Add HtmlGraph footer for tracked work
```

### Output Format:

✅ **Changes committed and pushed**

Commit: {commit_hash}
Files changed: {file_count}
Branch: main → origin/main
