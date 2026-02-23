---
name: scheduler
description: Schedule posts to Telegram channel, check pending tasks, or restart the cron worker.
triggers:
  - schedule
  - pending posts
  - restart scheduler
---

# Scheduler Skill

Manage scheduled posts to your Telegram channel.

## Capabilities

1. **Schedule a post**: Add to SQLite database for automatic delivery
2. **Check pending**: View scheduled but unsent posts  
3. **Restart worker**: If scheduler stops, restart via PM2

## Execute

```bash
#!/bin/bash

# Schedule a new post
schedule_post() {
    sqlite3 /tmp/trading_zeroclaw/.zeroclaw/scheduler.db \
        "INSERT INTO scheduled_posts (id, message, scheduled_time, user_id, channel, sent) 
         VALUES ('post_' || CAST(strftime('%s','now') AS TEXT) || '_$USER_ID', '$1', datetime('now', '+$2'), '$USER_ID', '-1003637413591', 0);"
    echo "✅ Scheduled: $1"
}

# Check pending posts
check_pending() {
    sqlite3 /tmp/trading_zeroclaw/.zeroclaw/scheduler.db \
        "SELECT message, scheduled_time FROM scheduled_posts WHERE sent = 0 AND user_id = '$USER_ID' LIMIT 5;"
}

# Restart PM2 worker
restart_scheduler() {
    pm2 restart post-scheduler
    echo "✅ Scheduler restarted"
}

case "$1" in
    schedule)
        schedule_post "$2" "$3"
        ;;
    pending)
        check_pending
        ;;
    restart)
        restart_scheduler
        ;;
esac
```

## Usage

- "Schedule Buy BTC for in 2 minutes" → Adds to database
- "Check my pending posts" → Lists unsent posts
- "Restart scheduler" → Restarts PM2 worker

## Notes

- Posts are stored in SQLite (atomic writes)
- PM2 worker checks every 60 seconds
- Auto-restarts if Android kills process
