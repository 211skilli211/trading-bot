#!/usr/bin/env python3
"""
ZeroClaw Webhook Handler
Processes incoming Telegram messages and routes to skills
"""
import sys
import json
import subprocess
import os

# Add skill directory to path
sys.path.insert(0, '/root/trading-bot/.zeroclaw')

def handle_message(message_text, user_id=None):
    """Handle incoming message from Telegram"""
    
    # Remove bot mentions
    text = message_text.replace('@YourBotName', '').strip()
    
    # Route to executor
    try:
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/executor.py', text],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"⚠️ Error: {result.stderr[:500]}"
    except Exception as e:
        return f"❌ Handler error: {str(e)}"

def main():
    """Main entry point for webhook"""
    # Read input from stdin (JSON from ZeroClaw)
    try:
        input_data = sys.stdin.read()
        data = json.loads(input_data)
        
        message = data.get('message', '')
        user_id = data.get('user_id')
        
        response = handle_message(message, user_id)
        
        # Output response as JSON
        print(json.dumps({
            "response": response,
            "type": "text"
        }))
        
    except json.JSONDecodeError:
        # Direct command mode
        if len(sys.argv) > 1:
            response = handle_message(' '.join(sys.argv[1:]))
            print(response)
        else:
            print(json.dumps({
                "response": "🤖 Ready! Send me a command.",
                "type": "text"
            }))
    except Exception as e:
        print(json.dumps({
            "response": f"❌ Error: {str(e)}",
            "type": "text"
        }))

if __name__ == "__main__":
    main()
