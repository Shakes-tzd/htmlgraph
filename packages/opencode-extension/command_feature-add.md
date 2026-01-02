### /htmlgraph:feature-add

Add a new feature to the backlog

**Usage:** `/htmlgraph:feature-add [title]
`

**Parameters:**
- `title` (optional): The feature title. If not provided, ask the user.


**Examples:**
```bash
/htmlgraph:feature-add User Authentication
```
Add a new feature with the title "User Authentication"

```bash
/htmlgraph:feature-add
```
Prompt the user for a feature title



**Implementation:**
Execute the following HtmlGraph commands:

```bash
htmlgraph feature add
htmlgraph feature list
```



---
