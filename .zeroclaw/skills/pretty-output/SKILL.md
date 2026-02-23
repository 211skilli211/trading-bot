---
name: pretty-output
description: Formats skill and tool output for professional display to users.
triggers:
  - output
  - format
  - display
---

# Pretty Output Formatter

Converts raw JSON/tool output to professional human-readable format.

## Execute

```bash
#!/bin/bash
# Strip JSON artifacts and format cleanly
sed 's/<tool_call>//g; s/<\/tool_call>//g' | \
sed 's/{"name":"[^"]*","arguments":{[^}]*}}//g' | \
sed 's/\\n/\n/g' | \
grep -v '^$' | head -30
```
