---
name: link-archiver
description: Save URLs with title extraction and summary. Use when user sends a URL or says "save link", "bookmark", or taps Save Link button.
triggers:
  - "🔗 Save Link"
  - save link
  - bookmark
  - archive url
---

# Link Archiver

Extract URL metadata and save to Memory Vault with summary.

## Instructions

1. Extract URL from message
2. Fetch page title and content
3. Generate one-sentence summary with AI
4. Save to Memory Vault with tags
5. Confirm archive

## Execute

```bash
#!/bin/bash
INPUT="$1"

# Extract URL
URL=$(echo "$INPUT" | grep -oP 'https?://[^\s<>"{}|\\^`\[\]]+')

if [ -z "$URL" ]; then
  echo "🔗 <b>Link Archiver</b>

Send me a URL to save!

Examples:
• https://example.com/article
• Bookmark this: https://docs.python.org
• Save link https://github.com/project

I'll extract the title and create a summary."
  exit 0
fi

echo "📥 Archiving: $URL"

# Fetch and extract metadata
ARCHIVE=$(python3 << PYCODE
import json
import urllib.request
import re

url = """$URL"""

try:
    # Fetch page
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    
    # Extract title
    title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else "No title found"
    
    # Extract meta description
    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)', html, re.IGNORECASE)
    description = desc_match.group(1) if desc_match else ""
    
    # Extract first paragraph as content sample
    content_match = re.search(r'<p>([^<]{50,300})', html)
    content = content_match.group(1) if content_match else description[:200]
    
    # Generate summary with AI
    api_key = os.getenv('OPENROUTER_API_KEY', '')
    summary = ""
    
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps({
                "model": "arcee-ai/trinity-large-preview:free",
                "messages": [{"role": "user", "content": f"Summarize this in one sentence: Title: {title}\\nContent: {content[:500]}"}],
                "max_tokens": 100
            }).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            summary = result['choices'][0]['message']['content'].strip()
    except:
        summary = f"Article about: {title}"
    
    print(f"{title}|{summary}|{url}")
    
except Exception as e:
    print(f"Error|Could not fetch page: {str(e)[:50]}|{url}")
PYCODE
)

TITLE=$(echo "$ARCHIVE" | cut -d'|' -f1)
SUMMARY=$(echo "$ARCHIVE" | cut -d'|' -f2)
LINK=$(echo "$ARCHIVE" | cut -d'|' -f3)

# Save to memory
python3 "$HOME/.zeroclaw/memory_system.py" capture "🔗 $TITLE

$SUMMARY

📎 $LINK" > /dev/null 2>&1

echo "🔗 <b>Link Archived!</b>

📄 $TITLE

📝 $SUMMARY

📎 $LINK

🏷️ Tags: bookmark, article
💾 Saved to Memory Vault"
```

## Output

Archived link with title, one-sentence summary, and URL.
