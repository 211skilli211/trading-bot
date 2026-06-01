#!/usr/bin/env python3
"""
Trading Bot — Unified Entry Point (Render Deployment)
=====================================================
Combines:
1. REST API (Flask via remote_control_api)
2. Trading bot loop (paper or live)
3. Scheduled tasks (daily summary, weekly reports)

This single-process architecture keeps Render costs minimal.

Usage:
    python app.py                          # Start API + bot + scheduler
    python app.py --api-only               # Start REST API only
    python app.py --bot-only               # Start bot loop only
    python app.py --scheduler-only         # Start scheduler only
"""

import argparse
import os
import sys
import time
import logging
import threading
from datetime import datetime, timezone

# Configure logging
LOG_DIR = os.environ.get("BOT_LOG_DIR", "/tmp/logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, "app.log"), mode="a")
    ]
)
logger = logging.getLogger("trading_bot_app")


def start_rest_api():
    """Start the Flask REST API in a background thread."""
    try:
        from remote_control_api import app as flask_app
        port = int(os.environ.get("BOT_API_PORT", os.environ.get("PORT", 10000)))
        logger.info(f"🌐 Starting REST API on port {port}")

        def run_api():
            flask_app.run(host="0.0.0.0", port=port, threaded=True, debug=False)

        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        logger.info("🌐 REST API started (background thread)")
        return api_thread
    except Exception as e:
        logger.error(f"❌ Failed to start REST API: {e}")
        return None


def start_trading_loop():
    """Start the trading monitor loop in a background thread."""
    try:
        from trading_bot import TradingBot
        interval = int(os.environ.get("MONITOR_INTERVAL", 30))
        mode = os.environ.get("TRADING_MODE", "paper")
        logger.info(f"📊 Starting trading loop (mode={mode}, interval={interval}s)")

        bot = TradingBot()

        def run_bot():
            if hasattr(bot, 'run_monitor'):
                bot.run_monitor(interval=interval)
            elif hasattr(bot, 'start'):
                bot.start()
            else:
                # Fallback: run_once in a loop
                logger.info("Using run_once loop")
                while True:
                    try:
                        if hasattr(bot, 'run_once'):
                            bot.run_once()
                    except Exception as e:
                        logger.error(f"Bot loop error: {e}")
                    time.sleep(interval)

        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        logger.info("📊 Trading loop started (background thread)")
        return bot_thread
    except Exception as e:
        logger.error(f"❌ Failed to start trading loop: {e}")
        import traceback
        traceback.print_exc()
        return None


def start_scheduler():
    """Start scheduled tasks via APScheduler."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from discord_notifier import DiscordNotifier
        from event_logger import EventLogger

        logger.info("📅 Starting scheduler")
        scheduler = BackgroundScheduler()
        scheduler.start()

        # Daily summary at 9 AM UTC
        def daily_summary():
            try:
                logger.info("Generating daily summary")
                # Placeholder: implement actual summary logic
                logger.info("Daily summary generated")
            except Exception as e:
                logger.error(f"Daily summary error: {e}")

        scheduler.add_job(daily_summary, "cron", hour=9, minute=0, id="daily_summary")
        logger.info("📅 Scheduler started (daily summary at 9AM UTC)")
        return scheduler
    except ImportError:
        logger.warning("APScheduler not available, skipping scheduler")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Trading Bot — Unified App")
    parser.add_argument("--api-only", action="store_true", help="Run REST API only")
    parser.add_argument("--bot-only", action="store_true", help="Run trading loop only")
    parser.add_argument("--scheduler-only", action="store_true", help="Run scheduler only")
    args = parser.parse_args()

    # Default: run everything unless specified otherwise
    run_all = not (args.api_only or args.bot_only or args.scheduler_only)

    logger.info("=" * 60)
    logger.info("  IBT Trading Bot — Unified Deployment")
    logger.info(f"  Time: {datetime.now(timezone.utc).isoformat()}Z")
    logger.info(f"  Mode: {os.environ.get('TRADING_MODE', 'paper')}")
    logger.info("=" * 60)

    threads = []

    # Start REST API
    if run_all or args.api_only:
        t = start_rest_api()
        if t:
            threads.append(t)

    # Start trading loop
    if run_all or args.bot_only:
        # Small delay to let API start first
        time.sleep(2)
        t = start_trading_loop()
        if t:
            threads.append(t)

    # Start scheduler
    if run_all or args.scheduler_only:
        t = start_scheduler()
        if t:
            threads.append(t)

    if not threads:
        logger.error("❌ Nothing started! Check dependencies and config.")
        sys.exit(1)

    logger.info(f"✅ {len(threads)} component(s) running. Press Ctrl+C to stop.")

    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
