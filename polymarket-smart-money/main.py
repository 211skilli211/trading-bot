"""
Polymarket Smart Money Module — Main Orchestrator
Runs the full pipeline: scan → track → score → alert.
"""
import logging
import sys
import os
import time
from datetime import datetime, timezone

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from database import init_db
from scanner import MarketScanner, run_scan
from wallet_tracker import WalletTracker, run_wallet_scan
from smart_money import SmartMoneyScorer, run_scoring
from alerts_whatsapp import run_alerts, send_daily_summary

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "..", "logs", "polymarket_smart_money.log")
        )
    ]
)
logger = logging.getLogger(__name__)


def run_full_pipeline():
    """Run the complete smart money pipeline."""
    logger.info("=" * 60)
    logger.info("Starting Polymarket Smart Money Pipeline")
    logger.info("=" * 60)
    
    start = time.time()
    
    # Step 1: Initialize database
    logger.info("Step 1: Initializing database...")
    init_db()
    
    # Step 2: Scan markets
    logger.info("Step 2: Scanning markets...")
    scan_result = run_scan()
    logger.info(f"Markets: {scan_result['markets_stored']} stored")
    
    # Step 3: Track wallets
    logger.info("Step 3: Tracking wallets...")
    wallet_result = run_wallet_scan()
    logger.info(f"Wallets: {wallet_result['unique_wallets']} found, {wallet_result['smart_wallets']} smart")
    
    # Step 4: Score wallets
    logger.info("Step 4: Scoring wallets...")
    score_result = run_scoring()
    logger.info(f"Signals: {score_result['signals_generated']} generated")
    
    # Step 5: Send alerts
    logger.info("Step 5: Sending alerts...")
    alerts = run_alerts()
    logger.info(f"Alerts: {len(alerts)} sent")
    
    duration = time.time() - start
    
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(duration, 2),
        "markets_scanned": scan_result["markets_stored"],
        "wallets_tracked": wallet_result["unique_wallets"],
        "smart_wallets": wallet_result["smart_wallets"],
        "signals_generated": score_result["signals_generated"],
        "alerts_sent": len(alerts),
        "top_signals": score_result.get("top_signals", [])[:3]
    }
    
    logger.info("=" * 60)
    logger.info(f"Pipeline complete in {duration:.1f}s")
    logger.info(f"Summary: {summary}")
    logger.info("=" * 60)
    
    return summary


def run_quick_scan():
    """Quick scan — just markets and recent trades."""
    init_db()
    scan_result = run_scan()
    wallet_result = run_wallet_scan()
    return {
        "markets": scan_result["markets_stored"],
        "wallets": wallet_result["unique_wallets"],
        "smart_wallets": wallet_result["smart_wallets"]
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Polymarket Smart Money Bot")
    parser.add_argument("--mode", choices=["full", "quick", "score", "alerts", "daily"],
                       default="full", help="Run mode")
    args = parser.parse_args()
    
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "logs"), exist_ok=True)
    
    if args.mode == "full":
        result = run_full_pipeline()
    elif args.mode == "quick":
        result = run_quick_scan()
    elif args.mode == "score":
        init_db()
        result = run_scoring()
    elif args.mode == "alerts":
        init_db()
        alerts = run_alerts()
        result = {"alerts_sent": len(alerts)}
    elif args.mode == "daily":
        init_db()
        msg = send_daily_summary()
        result = {"summary_sent": msg is not None}
    
    print(f"\nResult: {result}")
