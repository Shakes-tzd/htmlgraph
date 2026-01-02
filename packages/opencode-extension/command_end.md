### /htmlgraph:end

End the current session and record work summary

**Usage:** `/htmlgraph:end
`

**Parameters:**
None

**Examples:**
```bash
/htmlgraph:end
```
Gracefully end the current session and show work summary



**Implementation:**
Execute the following HtmlGraph commands:

```bash
htmlgraph session list --limit 1
htmlgraph session end
```



---
