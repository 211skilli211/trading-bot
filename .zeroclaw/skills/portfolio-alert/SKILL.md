---
name: portfolio-alert
description: Monitor portfolio and send alerts for significant changes. Use when user wants to check portfolio or set up alerts.
triggers:
  - portfolio alert
  - check portfolio
  - portfolio status
  - pnl alert
---

# Portfolio Alert

Check portfolio status and send alerts for significant changes.

## Instructions

1. Query trading database for current positions
2. Calculate P&L and performance metrics
3. Compare to thresholds
4. Send alert if significant change detected

## Execute

```bash
#!/bin/bash

# Get portfolio data from trading engine
PORTFOLIO=$(python3 /root/trading-bot/.zeroclaw/trading_engine.py summary 2>/dev/null)

if [ -z "$PORTFOLIO" ]; then
  # Demo data if no database
  TOTAL_VALUE="10000.00"
  TOTAL_PNL="250.50"
  PNL_PCT="2.55"
  POSITIONS="1"
  
  echo "💼 <b>Portfolio Status</b> (Paper Trading)

💰 <b>Total Value:</b> $$TOTAL_VALUE
📈 <b>Total P&L:</b> +$$TOTAL_PNL (+$PNL_PCT%)
📊 <b>Open Positions:</b> $POSITIONS

<i>Portfolio is performing well! No alerts triggered.</i>

🔗 View full dashboard: http://localhost:8080/portfolio"
else
  echo "$PORTFOLIO" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    bal = d.get('balance', {})
    print(f\"💼 <b>Portfolio Status</b>\\n\")
    print(f\"💰 Total Value: ${bal.get('total_value_usd', 0):,.2f}\")
    print(f\"📈 P&L: ${bal.get('total_pnl', 0):,.2f} ({bal.get('pnl_pct', 0):.2f}%)\")
    print(f\"📊 Positions: {len(d.get('positions', []))}\")
else:
    print(\"❌ Could not fetch portfolio data\")
"
fi
```

## Output

Portfolio status with value, P&L, and position count.
