### /htmlgraph:feature-start

Start working on a feature (moves it to in-progress)

**Usage:** `/htmlgraph:feature-start [feature-id]
`

**Parameters:**
- `feature-id` (optional): The feature ID to start working on. If not provided, lists available features.


**Examples:**
```bash
/htmlgraph:feature-start feature-001
```
Start working on feature-001

```bash
/htmlgraph:feature-start
```
List available features and prompt for selection



**Implementation:**
Execute the following HtmlGraph commands:

```bash
htmlgraph feature list --status todo
htmlgraph feature start <feature-id>
```



---
