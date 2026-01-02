### /htmlgraph:recommend

Get smart recommendations on what to work on next

**Usage:** `/htmlgraph:recommend [--count N] [--check-bottlenecks]
`

**Parameters:**
- `--count` (optional) (default: 3): Number of recommendations to show
- `--check-bottlenecks` (optional) (default: True): Also show bottlenecks


**Examples:**
```bash
/htmlgraph:recommend
```
Get top 3 recommendations with bottleneck check

```bash
/htmlgraph:recommend --count 5
```
Get top 5 recommendations

```bash
/htmlgraph:recommend --no-check-bottlenecks
```
Recommendations only, skip bottleneck analysis



**Implementation:**
Execute the following HtmlGraph commands:

```bash

```



---
