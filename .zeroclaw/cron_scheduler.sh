#!/bin/bash
# Simple cron-based scheduler - runs every minute

SCHEDULE_FILE="/tmp/trading_zeroclaw/.zeroclaw/scheduled_posts.json"
BOT_TOKEN="8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
DEFAULT_CHANNEL="-1003637413591"

if [ ! -f "$SCHEDULE_FILE" ]; then
    exit 0
fi

NOW=$(date '+%Y-%m-%dT%H:%M')

# Check each post
python3 << PYCODE
import json
import urllib.request
from datetime import datetime

try:
    with open('$SCHEDULE_FILE', 'r') as f:
        posts = json.load(f)
    
    now = datetime.now()
    changed = False
    
    for post in posts:
        if post.get('sent'):
            continue
        
        scheduled = datetime.fromisoformat(post['scheduled_time'])
        if scheduled <= now:
            # Send the post
            payload = {
                'chat_id': post['channel'],
                'text': post['message'],
                'parse_mode': 'HTML'
            }
            
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot$BOT_TOKEN/sendMessage',
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read().decode())
                    if result.get('ok'):
                        post['sent'] = True
                        post['sent_at'] = now.isoformat()
                        changed = True
                        print(f"[Scheduler] Sent: {post['message'][:40]}...")
            except Exception as e:
                print(f"[Scheduler] Failed to send: {e}")
    
    if changed:
        with open('$SCHEDULE_FILE', 'w') as f:
            json.dump(posts, f, indent=2)
            
except Exception as e:
    print(f"[Scheduler] Error: {e}")
PYCODE
