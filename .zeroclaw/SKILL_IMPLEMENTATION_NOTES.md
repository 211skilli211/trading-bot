# ZeroClaw Skill Implementation Notes

## How ZeroClaw Executes Skills

### Architecture Overview

ZeroClaw executes skills by combining AI model reasoning with pre-packaged instructions in SKILL.md files:

1. **Discovery**: At startup, ZeroClaw scans skill directories (`~/.zeroclaw/skills/`) and reads metadata (name, description) from SKILL.md frontmatter to build an index.

2. **Selection via LLM**: When a user makes a request, the LLM determines which skill to use based on the description in the frontmatter (NOT keyword matching).

3. **On-Demand Loading**: Only when the LLM decides to use a skill is the complete SKILL.md content loaded and injected into the context.

4. **Execution**: The SKILL.md contains procedural instructions that tell the agent what steps to take, often involving:
   - Bash commands (curl, etc.)
   - Node.js scripts
   - References to handler.py files

## SKILL.md Format

### Required Structure

```markdown
---
name: skill-name-kebab-case
description: "Clear description. Use when: (1) trigger 1, (2) trigger 2, (3) trigger 3"
---

# Skill Title

Brief description of what this skill does.

## Steps to execute

1. Step 1 description
2. Step 2 description

```bash
# Executable bash code
curl -s "https://api.example.com" | jq '.field'
```

## Example

User: "Example query"
→ What to do
→ Expected output

## Output format

Always return in this format:
```
Formatted output with emojis
```
```

### Key Points

1. **YAML Frontmatter is CRITICAL**: The `description` field tells the LLM WHEN to use the skill
   - Must include "Use when..." with specific triggers
   - The LLM uses this to decide which skill to invoke

2. **Step-by-step Instructions**: The body must contain clear procedural steps

3. **Executable Code**: Include working bash/Node.js examples in code blocks

4. **Output Format**: Specify exactly how to format the response

## Installation

### Method 1: CLI Installation

```bash
export HOME=/tmp/trading_zeroclaw
zeroclaw skills install /path/to/skill/directory
```

### Method 2: Direct Copy

Copy skill directory to `~/.zeroclaw/skills/`:
```
~/.zeroclaw/skills/
└── skill-name/
    ├── SKILL.md          # Main skill file (REQUIRED)
    ├── skill.toml        # Metadata (optional)
    └── handler.py        # Executable handler (optional)
```

## Channel-Specific Configuration

### Telegram Bot (No AI Mode)

To use skills directly without AI processing (recommended for trading bots):

```toml
[channels_config.telegram]
bot_token = "YOUR_BOT_TOKEN"
allowed_users = ["USER_ID"]

[channels_config.telegram.handler]
type = "script"
script = "/path/to/handler.sh"
disable_ai = true    # <-- IMPORTANT: Disables AI, uses script directly
```

Handler script example:
```bash
#!/bin/bash
MESSAGE=$(cat)
python3 /path/to/executor.py "$MESSAGE"
```

### Webhook Mode

```toml
[gateway.webhook]
enabled = true
handler = "/path/to/webhook_handler.sh"
```

Note: Webhook handler executes BEFORE AI processing unless `disable_ai` is set.

## Troubleshooting

### AI Not Using Skills

1. Check skill is installed: `zeroclaw skills list`
2. Verify SKILL.md has proper YAML frontmatter
3. Ensure description includes clear "Use when..." triggers
4. Check that bash code is properly formatted in code blocks

### Empty Responses

1. Check handler script exists and is executable
2. Verify handler outputs to stdout
3. Check logs: `tail -f ~/.zeroclaw/zeroclaw.log`

### Skill Not Found

1. Skills must be in `~/.zeroclaw/skills/` or `~/.zeroclaw/workspace/skills/`
2. Directory name must match `name` in YAML frontmatter
3. File must be named exactly `SKILL.md`

## Example Working Skills

### Price Check Skill

```markdown
---
name: price-check
description: Fetch live cryptocurrency prices from CoinGecko. Use when the user asks about BTC, ETH, SOL prices, crypto prices, or wants to check coin values.
---

# Price Check

Fetch live cryptocurrency prices from CoinGecko API.

## Steps to execute

1. Identify which coin the user is asking about:
   - BTC, Bitcoin → use "bitcoin"
   - ETH, Ethereum → use "ethereum"  
   - SOL, Solana → use "solana"

2. Call CoinGecko API:

```bash
curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true" | python3 -c "
import json, sys
data = json.load(sys.stdin)
price = data['bitcoin']['usd']
change = data['bitcoin'].get('usd_24h_change', 0)
print(f'💰 BTC/USDT')
print(f'💵 Price: \${price:,.2f}')
print(f'📈 24h Change: {change:+.2f}%')
"
```

3. Return the formatted price information.

## Output format

```
💰 COIN/USDT
💵 Price: $XX,XXX.XX
📈 24h Change: +X.XX%
```
```

## Important Configuration Files

### Main Config
- Location: `~/.zeroclaw/config.toml`
- Key settings:
  - `default_model`: Which AI model to use
  - `require_pairing = false`: Disable pairing for testing
  - `channels_config.telegram.handler`: Direct script handler

### Skill Locations
- Global: `~/.zeroclaw/skills/`
- Workspace: `~/.zeroclaw/workspace/skills/` (symlinks to global)

### Logs
- Location: `~/.zeroclaw/zeroclaw.log`
- Check for skill loading and execution errors

## Testing Skills

### Test via Agent Mode
```bash
export HOME=/tmp/trading_zeroclaw
zeroclaw agent -m "Your test message"
```

### Test via Webhook
```bash
curl -X POST http://127.0.0.1:3001/webhook \
  -H "Content-Type: application/json" \
  -d '{"message": "Your test message"}'
```

## References

- Open Skills Template: `/tmp/trading_zeroclaw/open-skills/SKILL_TEMPLATE.md`
- Contributing Guide: `/tmp/trading_zeroclaw/open-skills/CONTRIBUTING.md`
- Working Examples: `/tmp/trading_zeroclaw/open-skills/skills/`
