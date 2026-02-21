# ZeroClaw Trading Bot - Complete Setup Guide

## 🎯 Overview
This is a **self-improving, multi-agent trading system** with:
- **11 specialized skills** (trading, diagnostics, development)
- **Hybrid architecture** (copilot + autonomous modes)
- **Self-diagnostic capabilities**
- **Zero-downtime skill development**

---

## 📁 File Structure

```
/root/trading-bot/.zeroclaw/
├── config.toml              # Main configuration
├── TRADING_PERSONA.md       # Bot personality & routing rules
├── SKILLS_GUIDE.md          # User skill reference
├── SETUP_GUIDE.md           # This file
├── executor.py              # Command router
├── webhook_handler.py       # Telegram integration
└── skills/
    ├── orchestrator/        # Central conductor
    ├── price-check/         # Crypto prices
    ├── arbitrage-scan/      # Cross-exchange spreads
    ├── trade-execute/       # Order execution
    ├── market-analyst/      # TA & patterns
    ├── portfolio-check/     # Portfolio monitoring
    ├── system-diagnostic/   # Health checks
    ├── debugger/            # Error tracing
    ├── log-analyzer/        # Activity analysis
    ├── performance-monitor/ # P&L tracking
    ├── config-optimizer/    # Settings improvement
    └── bot-developer/       # Self-improvement
```

---

## 🚀 Quick Start

### 1. Start Both ZeroClaw Instances

**Terminal 1 - Personal Bot (Port 3000):**
```bash
HOME=/tmp/personal_zeroclaw zeroclaw daemon
```

**Terminal 2 - Trading Bot (Port 3001):**
```bash
HOME=/tmp/trading_zeroclaw zeroclaw daemon
```

### 2. Verify Health
```bash
curl http://localhost:3000/health
curl http://localhost:3001/health
```

### 3. Test Skills

In Telegram, message your **trading bot**:
```
Check price of BTC
System status
Performance report
Help
```

---

## 🤖 How It Works

### Command Flow
```
User (Telegram)
    ↓
ZeroClaw Trading Bot (Port 3001)
    ↓
Orchestrator Skill (routes command)
    ↓
Skill Handler (executor.py)
    ↓
Response to User
```

### Skill Categories

| Category | Skills | Purpose |
|----------|--------|---------|
| **Trading** | price-check, arbitrage-scan, trade-execute, market-analyst | Execute trades & analysis |
| **Diagnostics** | system-diagnostic, debugger, log-analyzer | Health checks & debugging |
| **Analysis** | performance-monitor, config-optimizer | Performance tracking & optimization |
| **Development** | bot-developer | Self-improvement |

---

## 🔧 Skill Routing

The orchestrator automatically routes commands based on keywords:

| You Say | Routed To |
|---------|-----------|
| "price of BTC" | price-check |
| "system status" | system-diagnostic |
| "debug error" | debugger |
| "performance" | performance-monitor |
| "optimize config" | config-optimizer |
| "add feature" | bot-developer |

---

## 🛠️ Development Mode

### Creating New Skills

1. Create skill directory:
```bash
mkdir /root/trading-bot/.zeroclaw/skills/my-skill
```

2. Create `skill.toml`:
```toml
[skill]
name = "My Skill"
description = "What it does"
version = "1.0.0"

[triggers]
patterns = ["keyword1", "keyword2"]

[tools]
allowed = ["shell", "file_read"]
```

3. Create `handler.py`:
```python
#!/usr/bin/env python3
if __name__ == "__main__":
    print("✅ My skill executed!")
```

4. Add to config:
```toml
[[skills.loaded]]
name = "my-skill"
enabled = true
```

5. Restart ZeroClaw

---

## 📊 Monitoring

### Automatic Diagnostics
- Health checks every 30 minutes
- Telegram alerts on issues
- Performance reports daily at 20:00

### Manual Commands
```
"System status"       → Full health check
"Debug error"         → Trace issues
"Analyze logs"        → Recent activity
"Performance report"  → Trading stats
```

---

## 🔐 Safety Features

### Approval Required For:
- Trade execution
- Config changes
- Code modifications
- Git commits

### Forbidden Operations:
- Core engine changes
- Credential modifications
- Database deletion
- Unauthorized withdrawals

### Automatic Backups:
- Created before any change
- Stored in `.backup/`
- Easy rollback if needed

---

## 🐛 Troubleshooting

### Bot Not Responding
```bash
# Check if running
curl http://localhost:3001/health

# Restart if needed
pkill -f "HOME=/tmp/trading_zeroclaw"
HOME=/tmp/trading_zeroclaw zeroclaw daemon
```

### Skill Not Working
```bash
# Check handler exists
ls /root/trading-bot/.zeroclaw/skills/NAME/handler.py

# Test manually
python3 /root/trading-bot/.zeroclaw/skills/NAME/handler.py "test"
```

### Telegram Not Receiving
```bash
# Check bot token
grep bot_token /root/trading-bot/.zeroclaw/config.toml

# Verify webhook
HOME=/tmp/trading_zeroclaw zeroclaw channel bind-telegram YOUR_USER_ID
```

---

## 📝 Logs

| Log File | Purpose |
|----------|---------|
| `/root/trading-bot/bot.log` | Main trading activity |
| `/root/trading-bot/dashboard.log` | Web dashboard |
| `/tmp/trading_zeroclaw/zeroclaw.log` | ZeroClaw trading bot |
| `/tmp/personal_zeroclaw/zeroclaw.log` | ZeroClaw personal bot |

---

## 🎓 Learning Resources

- **Skill Development**: See `SKILL.md` files in each skill directory
- **Architecture**: Read `TRADING_PERSONA.md`
- **Command Reference**: See `SKILLS_GUIDE.md`

---

## 🔄 Self-Improvement Loop

The bot can improve itself:

1. **Monitor** → performance-monitor tracks results
2. **Diagnose** → debugger finds issues
3. **Optimize** → config-optimizer suggests improvements
4. **Develop** → bot-developer implements changes
5. **Test** → Validate improvements
6. **Deploy** → Apply to live system

---

*Last Updated: 2026-02-21*
*Version: 1.0*
