### /htmlgraph:serve

Start the dashboard server

**Usage:** `/htmlgraph:serve [port]
`

**Parameters:**
- `port` (optional) (default: 8080): Port number for the dashboard server


**Examples:**
```bash
/htmlgraph:serve
```
Start dashboard on default port 8080

```bash
/htmlgraph:serve 3000
```
Start dashboard on port 3000



**Implementation:**
Execute the following HtmlGraph commands:

```bash
htmlgraph serve --port ${port:-8080}
```



---
