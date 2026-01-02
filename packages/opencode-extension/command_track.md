### /htmlgraph:track

Manually track an activity or note

**Usage:** `/htmlgraph:track <tool> <summary> [--files file1 file2]
`

**Parameters:**
- `tool` (required): The tool/action type (e.g., "Note", "Decision", "Research")
- `summary` (required): Description of the activity
- `files` (optional): Related files


**Examples:**
```bash
/htmlgraph:track "Decision" "Chose React over Vue for frontend" --files src/components/App.tsx
```
Track a decision with related files

```bash
/htmlgraph:track "Research" "Investigated auth options JWT vs sessions"
```
Track research activity

```bash
/htmlgraph:track "Note" "User prefers dark mode as default"
```
Track a general note



**Implementation:**
Execute the following HtmlGraph commands:

```bash
htmlgraph track {tool} {summary} --files {files}
```



---
