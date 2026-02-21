# System Diagnostic Skill

## Purpose
Comprehensive health check and diagnostic tool for the entire trading bot ecosystem.

## When to Use
- Bot seems unresponsive
- Trades not executing
- Suspected connectivity issues
- Regular health monitoring
- Before important trading sessions

## Diagnostics Performed

### 1. Exchange Connectivity
- Tests Binance API
- Tests Coinbase API  
- Tests Kraken API
- Validates API key permissions

### 2. ZeroClaw Status
- Personal instance (port 3000)
- Trading instance (port 3001)
- Telegram bot responsiveness

### 3. Dashboard Health
- Web interface availability
- API endpoints responding
- Database connection

### 4. System Resources
- Disk space (alerts if < 10%)
- Memory usage
- CPU load
- Process status

### 5. Log Analysis
- Recent errors
- Warning patterns
- Unusual activity

## Output Example
```
🔍 SYSTEM DIAGNOSTIC REPORT

⏰ Timestamp: 2026-02-21 10:30:15 UTC
📊 Overall Status: ✅ HEALTHY

EXCHANGE CONNECTIONS:
✅ Binance: Connected (latency: 45ms)
✅ Coinbase: Connected (latency: 120ms)
⚠️  Kraken: Slow response (latency: 890ms)

ZEROCLAW INSTANCES:
✅ Personal (3000): Running, paired
✅ Trading (3001): Running, paired

DASHBOARD: ✅ Running on port 8080

SYSTEM RESOURCES:
✅ Disk: 45% used (55GB free)
✅ Memory: 62% used (1.2GB free)
⚠️  CPU: High load (78%)

RECENT ERRORS:
- 1 warning: Kraken API slow (2 min ago)
- No critical errors

RECOMMENDATIONS:
1. Monitor Kraken connection
2. Consider restarting if CPU stays high
3. All systems operational for trading
```

## Automatic Alerts
The diagnostic skill runs automatically every 30 minutes and sends Telegram alerts if:
- Any exchange is down
- ZeroClaw instances are unresponsive
- Disk space < 10%
- Critical errors in logs