#!/usr/bin/env python3
"""
Reliable background scheduler - runs as standalone process
"""

import json
import os
import sys
import time
from datetime import datetime

SCHEDULE_FILE = "/tmp/trading_zeroclaw/.zeroclaw/scheduled_posts.json"
BOT_TOKEN = "8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
DEFAULT_CHANNEL = "-1003637413591"
PID_FILE = "/tmp/trading_zeroclaw/.zeroclaw/scheduler.pid"

def send_post(post):
    """Send post to Telegram"""
    try:
        import urllib.request
        payload = {
            'chat_id': post['channel'],
            'text': post['message'],
            'parse_mode': 'HTML'
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            return result.get('ok', False)
    except Exception as e:
        print(f"[Scheduler] Send error: {e}")
        return False

def check_and_send():
    """Check for due posts and send them"""
    if not os.path.exists(SCHEDULE_FILE):
        return
    
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            posts = json.load(f)
    except:
        return
    
    now = datetime.now()
    changed = False
    
    for post in posts:
        if post.get('sent'):
            continue
        
        try:
            scheduled = datetime.fromisoformat(post['scheduled_time'])
            if scheduled <= now:
                print(f"[Scheduler] Sending: {post['message'][:40]}...")
                if send_post(post):
                    post['sent'] = True
                    post['sent_at'] = now.isoformat()
                    changed = True
                    print(f"[Scheduler] Sent successfully!")
                else:
                    print(f"[Scheduler] Failed to send")
        except Exception as e:
            print(f"[Scheduler] Error processing post: {e}")
    
    if changed:
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump(posts, f, indent=2)

def main():
    """Main loop"""
    # Write PID file
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    print(f"[Scheduler] Started at {datetime.now()}")
    print(f"[Scheduler] PID: {os.getpid()}")
    
    try:
        while True:
            check_and_send()
            time.sleep(10)  # Check every 10 seconds
    except KeyboardInterrupt:
        print("[Scheduler] Stopped")
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

if __name__ == "__main__":
    main()
