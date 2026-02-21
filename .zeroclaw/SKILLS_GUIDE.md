# ZeroClaw Trading Bot - Skills Guide

## 🤖 Available Skills

### Trading Skills
| Skill | Status | Command Example |
|-------|--------|-----------------|
| **arbitrage-scan** | ✅ Active | "Find arbitrage opportunities" |
| **trade-execute** | ✅ Active | "Buy 0.1 BTC" (needs approval) |
| **price-check** | ✅ Active | "Check BTC price" |
| **portfolio-check** | ✅ Active | "Show my portfolio" |
| **market-analyst** | ✅ Active | "Analyze ETH chart" |

### Diagnostic Skills
| Skill | Status | Command Example |
|-------|--------|-----------------|
| **system-diagnostic** | ✅ Active | "System status" or "Health check" |
| **debugger** | ✅ Active | "Debug error" or "What went wrong" |
| **log-analyzer** | ✅ Active | "Analyze logs" or "Show activity" |

### Analysis Skills
| Skill | Status | Command Example |
|-------|--------|-----------------|
| **performance-monitor** | ✅ Active | "Performance report" or "How am I doing" |
| **config-optimizer** | ✅ Active | "Optimize config" or "Recommend changes" |

### Development Skills
| Skill | Status | Command Example |
|-------|--------|-----------------|
| **bot-developer** | ✅ Active | "Add feature" or "Create strategy" (needs approval) |

### Planned Skills
| Skill | Status | Description |
|-------|--------|-------------|
| **risk-guardian** | ⏸️ Planned | Advanced risk management |
| **portfolio-agent** | ⏸️ Planned | Rebalancing & allocation |
| **sentiment-scanner** | ⏸️ Planned | News & social sentiment |

---

## 🎯 Quick Commands

### Trading
```
"Check price of BTC"
"Analyze ETH support and resistance"
"Buy 0.05 ETH at market"
"Find arbitrage opportunities"
"Show my portfolio balance"
```

### Diagnostics
```
"System health check"
"Why isn't trading working?"
"Debug the error"
"Show me recent logs"
"What happened today?"
```

### Analysis
```
"How's my performance?"
"Show trading stats"
"What's my win rate?"
"Optimize my config"
"Recommend better settings"
```

### Development
```
"Add a new indicator"
"Create a momentum strategy"
"Improve the arbitrage scanner"
"Fix this bug"
"Implement stop loss trailing"
```

---

## 🔐 Safety Levels

### No Approval Needed
- Price checks
- Market analysis
- System diagnostics
- Log viewing
- Performance reports

### Requires Approval
- Trade execution
- Config changes
- Code modifications
- Feature development
- Git commits

### Forbidden
- Core engine changes
- Credential modifications
- Database deletion
- Unauthorized withdrawals

---

## 🚀 Getting Started

1. **Test Trading Skills**
   ```
   "Check price of BTC"
   "Analyze SOL trend"
   ```

2. **Run Diagnostics**
   ```
   "System status"
   "Health check"
   ```

3. **Check Performance**
   ```
   "Performance report"
   "How am I doing?"
   ```

4. **Request Improvements**
   ```
   "Optimize config"
   "Recommend changes"
   ```

---

## 📝 Skill Development

To add a new skill:

1. Create directory: `/root/trading-bot/.zeroclaw/skills/your-skill/`
2. Create `skill.toml` with triggers and capabilities
3. Create `SKILL.md` with documentation
4. Add to config: `[[skills.loaded]] name = "your-skill"`
5. Restart ZeroClaw

The bot can even help you create skills - just ask:
```
"Create a skill for monitoring gas prices"
```

---

## 🔄 Self-Improvement

The bot can:
- Diagnose its own issues
- Suggest config optimizations
- Develop new features
- Analyze its performance
- Learn from your feedback

This creates a feedback loop where the trading bot gets smarter over time!

---

*Last updated: 2026-02-21*
*Version: 1.0*
