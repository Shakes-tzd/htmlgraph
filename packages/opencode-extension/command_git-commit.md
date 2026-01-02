### /htmlgraph:git-commit

Commit and push changes using git-commit-push.sh script

**Usage:** `/htmlgraph:git-commit <message>
`

**Parameters:**
- `message` (required): Commit message (supports multi-line with newlines)
- `skip_confirm` (optional) (default: True): Skip confirmation prompt (recommended for AI agents)


**Examples:**
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



**Implementation:**
Execute the following HtmlGraph commands:

```bash
./scripts/git-commit-push.sh "{message}" --no-confirm
```



---
