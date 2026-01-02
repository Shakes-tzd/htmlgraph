### /htmlgraph:deploy

Deploy new version to PyPI using deploy-all.sh script

**Usage:** `/htmlgraph:deploy <version>
`

**Parameters:**
- `version` (required): Version number (e.g., 0.12.1, 0.13.0, 1.0.0)
- `skip_confirm` (optional) (default: True): Skip confirmation prompts (recommended for AI agents)


**Examples:**
```bash
/htmlgraph:deploy 0.12.1
```
Deploy patch release (bug fixes)

```bash
/htmlgraph:deploy 0.13.0
```
Deploy minor release (new features)

```bash
/htmlgraph:deploy 1.0.0
```
Deploy major release (breaking changes)



**Implementation:**
Execute the following HtmlGraph commands:

```bash
./scripts/deploy-all.sh {version} --no-confirm
```



---
