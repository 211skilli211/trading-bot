#!/usr/bin/env python3
"""
Schedule Tool - Integrated with bot's systems
No external processes needed - checks on every message
"""

import json
import os
from datetime import datetime, timedelta

SCHEDULE_FILE = "/tmp/trading_zeroclaw/.zeroclaw/scheduled_posts.json"
BOT_TOKEN = "8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
DEFAULT_CHANNEL = "-1003637413591"

class ScheduleTool:
    """Tool for scheduling posts - integrated with handler"""
    
    @staticmethod
    def load_posts():
        if os.path.exists(SCHEDULE_FILE):
            try:
                with open(SCHEDULE_FILE, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    @staticmethod
    def save_posts(posts):
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump(posts, f, indent=2)
    
    @staticmethod
    def parse_time(when: str) -> datetime:
        """Parse natural time"""
        now = datetime.now()
        when_lower = when.lower().strip()
        
        # "in X minutes"
        import re
        match = re.search(r'(\d+)\s*min', when_lower)
        if match:
            return now + timedelta(minutes=int(match.group(1)))
        
        # "in X hours"
        match = re.search(r'(\d+)\s*hour', when_lower)
        if match:
            return now + timedelta(hours=int(match.group(1)))
        
        # "tomorrow"
        if "tomorrow" in when_lower:
            tomorrow = now + timedelta(days=1)
            for hour in range(24):
                if f"{hour}am" in when_lower or f"{hour}:00am" in when_lower:
                    return tomorrow.replace(hour=hour, minute=0, second=0)
                if f"{hour}pm" in when_lower or f"{hour}:00pm" in when_lower:
                    hour_24 = hour + 12 if hour != 12 else 12
                    return tomorrow.replace(hour=hour_24, minute=0, second=0)
            return tomorrow.replace(hour=9, minute=0, second=0)
        
        # Try ISO format
        try:
            return datetime.fromisoformat(when)
        except:
            pass
        
        return None
    
    @staticmethod
    def schedule(message: str, when: str, user_id: str) -> dict:
        """Schedule a post"""
        scheduled_time = ScheduleTool.parse_time(when)
        if not scheduled_time:
            return {"success": False, "error": f"Can't understand time: '{when}'"}
        
        posts = ScheduleTool.load_posts()
        post_id = f"post_{int(datetime.now().timestamp())}_{user_id}"
        
        post = {
            "id": post_id,
            "message": message,
            "scheduled_time": scheduled_time.isoformat(),
            "user_id": user_id,
            "channel": DEFAULT_CHANNEL,
            "created_at": datetime.now().isoformat(),
            "sent": False
        }
        
        posts.append(post)
        ScheduleTool.save_posts(posts)
        
        return {
            "success": True,
            "post_id": post_id,
            "scheduled_time": scheduled_time.strftime("%A, %B %d at %I:%M %p"),
            "message_preview": message[:50] + "..." if len(message) > 50 else message
        }
    
    @staticmethod
    def check_and_send():
        """Check for due posts and send them - CALL THIS ON EVERY MESSAGE"""
        posts = ScheduleTool.load_posts()
        now = datetime.now()
        changed = False
        sent_posts = []
        
        for post in posts:
            if post.get("sent"):
                continue
            
            try:
                scheduled = datetime.fromisoformat(post["scheduled_time"])
                if scheduled <= now:
                    # Send it
                    if ScheduleTool._send_to_telegram(post["message"], post["channel"]):
                        post["sent"] = True
                        post["sent_at"] = now.isoformat()
                        changed = True
                        sent_posts.append(post["message"][:40])
            except Exception as e:
                print(f"[ScheduleTool] Error: {e}")
        
        if changed:
            ScheduleTool.save_posts(posts)
        
        return sent_posts
    
    @staticmethod
    def _send_to_telegram(message: str, channel: str) -> bool:
        """Send message to Telegram"""
        try:
            import urllib.request
            payload = {
                'chat_id': channel,
                'text': message,
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
            print(f"[ScheduleTool] Send error: {e}")
            return False
    
    @staticmethod
    def list_user_posts(user_id: str) -> list:
        """List posts for a user"""
        posts = ScheduleTool.load_posts()
        return [p for p in posts if p["user_id"] == user_id and not p.get("sent")]
    
    @staticmethod
    def cancel(post_id: str, user_id: str) -> bool:
        """Cancel a post"""
        posts = ScheduleTool.load_posts()
        original_len = len(posts)
        posts = [p for p in posts if not (p["id"] == post_id and p["user_id"] == user_id)]
        if len(posts) < original_len:
            ScheduleTool.save_posts(posts)
            return True
        return False

# Make it available as a skill
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "check":
            sent = ScheduleTool.check_and_send()
            print(f"Sent {len(sent)} posts")
        elif command == "schedule" and len(sys.argv) >= 5:
            result = ScheduleTool.schedule(sys.argv[2], sys.argv[3], sys.argv[4])
            print(json.dumps(result))
