#!/usr/bin/env python3
"""
Trading Bot Launcher
====================
Launches all components:
- Unified Dashboard
- Trading Bot (paper or live mode)
- Telegram Bot (if configured)
- ZeroClaw Pipeline (if enabled)
"""

import argparse
import json
import os
import sys
import time
import signal
from threading import Thread
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment with encryption support (before other imports)
try:
    from secure_env_loader import load_env, init_bot_with_security
    load_env(verbose=False)
except ImportError:
    # Fallback to regular dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

# Global flag for shutdown
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    global shutdown_requested
    print("\n\n🛑 Shutdown requested...")
    shutdown_requested = True
    
    # Create stop signal file
    with open("bot_stop.signal", "w") as f:
        f.write(datetime.now().isoformat())


def load_config():
    """Load configuration"""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except:
        print("⚠️  Could not load config.json, using defaults")
        return {
            "bot": {"mode": "PAPER", "monitor_interval": 60},
            "dashboard": {"enabled": True, "port": 8080},
            "alerts": {"telegram": {"enabled": False}},
            "zeroclaw": {"enabled": False}
        }


def start_dashboard(config, port=None):
    """Start the unified dashboard"""
    from unified_dashboard import run_dashboard
    
    dashboard_config = config.get("dashboard", {})
    if not dashboard_config.get("enabled", True):
        print("📊 Dashboard disabled in config")
        return None
    
    dashboard_port = port or dashboard_config.get("port", 8080)
    
    print(f"🌐 Starting Dashboard on port {dashboard_port}...")
    
    # Run in thread so we can start other components
    thread = Thread(target=run_dashboard, kwargs={
        "host": "0.0.0.0",
        "port": dashboard_port,
        "debug": False
    }, daemon=True)
    thread.start()
    
    return thread


def start_telegram_bot(config):
    """Start the enhanced Telegram bot"""
    telegram_config = config.get("alerts", {}).get("telegram", {})
    
    if not telegram_config.get("enabled", False):
        print("📱 Telegram bot disabled")
        return None
    
    try:
        from telegram_bot_enhanced import get_bot
        bot = get_bot()
        
        if not bot.enabled:
            print("📱 Telegram bot not properly configured")
            return None
        
        print("📱 Starting Telegram Bot...")
        bot.run_async()
        return bot
    except Exception as e:
        print(f"📱 Telegram bot error: {e}")
        return None


def start_trading_bot(config, mode="paper", monitor_interval=None):
    """Start the main trading bot"""
    try:
        from trading_bot import TradingBot
        
        bot_mode = mode or config.get("bot", {}).get("mode", "PAPER")
        interval = monitor_interval or config.get("bot", {}).get("monitor_interval", 60)
        
        print(f"🤖 Starting Trading Bot in {bot_mode.upper()} mode...")
        print(f"   Monitor interval: {interval}s")
        
        bot = TradingBot(mode=bot_mode, config=config)
        
        # Run monitor in background thread
        thread = Thread(target=bot.run_monitor, args=(interval,), daemon=True)
        thread.start()
        
        return bot, thread
    except Exception as e:
        print(f"🤖 Trading bot error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def check_requirements():
    """Check if all requirements are met"""
    print("=" * 60)
    print("🔍 Checking Requirements")
    print("=" * 60)
    
    # Check Python version
    import sys
    print(f"✓ Python {sys.version.split()[0]}")
    
    # Check database
    if os.path.exists("trades.db"):
        print("✓ Database (trades.db)")
    else:
        print("⚠️  Database not found, will be created")
    
    # Check config
    if os.path.exists("config.json"):
        print("✓ Configuration (config.json)")
    else:
        print("⚠️  Config not found, defaults will be used")
    
    # Check security module
    try:
        from security import CRYPTO_AVAILABLE
        if CRYPTO_AVAILABLE:
            print("✓ Security module (API key encryption)")
        else:
            print("⚠️  Security module loaded but cryptography not installed")
    except ImportError:
        print("⚠️  Security module not available")
    
    # Check optional dependencies
    try:
        import flask
        print("✓ Flask (dashboard)")
    except ImportError:
        print("❌ Flask not installed: pip install flask")
    
    try:
        import ccxt
        print("✓ CCXT (exchange trading)")
    except ImportError:
        print("⚠️  CCXT not installed (live trading disabled): pip install ccxt")
    
    try:
        from telegram import Bot
        print("✓ python-telegram-bot")
    except ImportError:
        print("⚠️  python-telegram-bot not installed: pip install python-telegram-bot")
    
    # Check for encrypted .env
    if os.path.exists(".env"):
        try:
            with open(".env", 'r') as f:
                content = f.read()
                if 'ENC:' in content:
                    if CRYPTO_AVAILABLE:
                        print("✓ Encrypted API keys detected (will auto-decrypt)")
                    else:
                        print("⚠️  Encrypted API keys found but cryptography not installed!")
                else:
                    print("ℹ️  API keys in .env are not encrypted")
        except Exception:
            pass
    
    print()


def main():
    """Main launcher"""
    parser = argparse.ArgumentParser(
        description="Trading Bot Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_bot.py                      # Start dashboard + bot (paper mode)
  python launch_bot.py --live               # Start in live mode (requires funding)
  python launch_bot.py --dashboard-only     # Dashboard only, no trading
  python launch_bot.py --port 9000          # Use custom port
        """
    )
    
    parser.add_argument("--mode", choices=["paper", "live"], default="paper",
                       help="Trading mode (default: paper)")
    parser.add_argument("--live", action="store_true",
                       help="Shortcut for --mode live")
    parser.add_argument("--dashboard-only", action="store_true",
                       help="Start only the dashboard")
    parser.add_argument("--no-telegram", action="store_true",
                       help="Disable Telegram bot")
    parser.add_argument("--port", type=int, default=None,
                       help="Dashboard port (default from config)")
    parser.add_argument("--interval", type=int, default=None,
                       help="Trading monitor interval in seconds")
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Clear old stop signal
    if os.path.exists("bot_stop.signal"):
        os.remove("bot_stop.signal")
    
    # Print banner
    print("=" * 60)
    print("🤖 211SKILLI TRADING BOT")
    print("=" * 60)
    print()
    
    # Check requirements
    check_requirements()
    
    # Load config
    config = load_config()
    
    # Determine mode
    mode = "live" if args.live else args.mode
    
    # Warn about live mode
    if mode == "live":
        print("⚠️  LIVE MODE SELECTED - REAL MONEY AT RISK!")
        print()
        # Check for API keys
        if not os.getenv("BINANCE_API_KEY"):
            print("❌ BINANCE_API_KEY not set")
        if not os.getenv("SOLANA_PRIVATE_KEY"):
            print("❌ SOLANA_PRIVATE_KEY not set")
        print()
        confirm = input("Type 'LIVE' to confirm: ")
        if confirm != "LIVE":
            print("Cancelled - starting in paper mode instead")
            mode = "paper"
        print()
    
    # Start components
    threads = []
    
    # 1. Start Dashboard
    dashboard_thread = start_dashboard(config, args.port)
    if dashboard_thread:
        threads.append(("Dashboard", dashboard_thread))
        time.sleep(1)  # Let dashboard start
    
    # 2. Start Telegram Bot
    if not args.no_telegram:
        telegram_bot = start_telegram_bot(config)
    
    # 3. Start Trading Bot
    if not args.dashboard_only:
        trading_bot, bot_thread = start_trading_bot(config, mode, args.interval)
        if bot_thread:
            threads.append(("Trading Bot", bot_thread))
    else:
        print("📊 Dashboard-only mode - trading bot not started")
    
    # Summary
    print()
    print("=" * 60)
    print("✅ COMPONENTS STARTED")
    print("=" * 60)
    print()
    print("Dashboard: http://localhost:{}".format(args.port or config.get("dashboard", {}).get("port", 8080)))
    print("Mode: {}".format(mode.upper()))
    print("Press Ctrl+C to stop")
    print()
    
    # Keep main thread alive
    try:
        while not shutdown_requested:
            time.sleep(1)
            
            # Check for stop signal file
            if os.path.exists("bot_stop.signal"):
                print("\n🛑 Stop signal detected")
                break
                
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    
    # Cleanup
    print("\n👋 Shutting down...")
    print("Goodbye!")


if __name__ == "__main__":
    main()
