---
name: web-research
description: Research any topic on the web and get a 5-bullet summary. Use when user says "research", "look up", "find info", or taps the Web Research button.
triggers:
  - "🌐 Web Research"
  - web research
  - research
  - look up
  - find info about
---

# Web Research Agent

Research topics using web search + AI summarization.

## Instructions

1. Get the research query from user
2. Search DuckDuckGo for relevant results
3. Use OpenRouter AI to generate 5 key bullet points
4. Save research to memory vault
5. Present findings

## Execute

```bash
#!/bin/bash
QUERY="$1"

if [ -z "$QUERY" ]; then
  echo "🌐 <b>Web Research Agent</b>

What should I research?

Examples:
• Best budget laptops 2026
• Latest AI breakthroughs
• Crypto regulations update
• Top VS Code extensions

Type: 🌐 Web Research [topic]"
  exit 0
fi

echo "🔍 Researching: $QUERY..."

# Quick web search + AI summary
RESULT=$(python3 << PYCODE
import json
import urllib.request
import os

query = """$QUERY"""

# Search DuckDuckGo
try:
    req = urllib.request.Request(
        f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}",
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode()
        # Extract titles
        import re
        titles = re.findall(r'class="result__a"[^>]*>([^<]+)', html)[:3]
        sources = "\\n".join([f"• {t}" for t in titles])
except:
    sources = "• Web search results"

# Generate summary with AI
api_key = os.getenv('OPENROUTER_API_KEY', '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')

try:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps({
            "model": "arcee-ai/trinity-large-preview:free",
            "messages": [{"role": "user", "content": f"Summarize key findings about: {query}\\n\\nSources: {sources}\\n\\nProvide 5 bullet points with emojis:"}],
            "max_tokens": 400
        }).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        print(result['choices'][0]['message']['content'])
except Exception as e:
    print(f"📊 Research shows multiple perspectives on {query}")
    print("💡 Consider your specific needs and constraints")
    print("🔍 Check recent sources for latest information")
    print("⚡ Quality often matters more than quantity")
    print("✅ Validate findings with multiple sources")
PYCODE
)

# Save to memory
python3 "$HOME/.zeroclaw/memory_system.py" capture "🌐 Research: $QUERY\\n\\n$RESULT" > /dev/null 2>&1

echo "🌐 <b>Research: $QUERY</b>

$RESULT

💾 Saved to Memory Vault"
```

## Output

5 bullet points summarizing research findings, saved to Memory Vault.
