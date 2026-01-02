### /htmlgraph:feature-complete

Mark a feature as complete

**Usage:** `/htmlgraph:feature-complete [feature-id]
`

**Parameters:**
- `feature-id` (optional): The feature ID to complete. If not provided, completes the current active feature.


**Examples:**
```bash
/htmlgraph:feature-complete feature-001
```
Complete a specific feature

```bash
/htmlgraph:feature-complete
```
Complete the current active feature



**Implementation:**
Execute the following HtmlGraph commands:

```bash
htmlgraph feature list --status in-progress
htmlgraph feature complete {feature_id}
htmlgraph status
htmlgraph feature list
```



---
