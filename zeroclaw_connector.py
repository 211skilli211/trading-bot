#!/usr/bin/env python3
"""
ZeroClaw Data Pipeline Connector
================================
Integrates ZeroClaw/OpenClaw as a data pipeline manager for:
- Price data ingestion
- Trade data storage
- Analytics processing
- Alert routing
"""

import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ZeroClawConnector:
    """
    Connector for ZeroClaw data pipeline.
    
    ZeroClaw (ClawDBot/OpenClaw) is a Rust-based data pipeline tool
    that can ingest, process, and route trading data.
    """
    
    def __init__(self, api_key: Optional[str] = None, instance_url: Optional[str] = None):
        """
        Initialize ZeroClaw connector.
        
        Args:
            api_key: ZeroClaw API key (or from config)
            instance_url: ZeroClaw instance URL (or from config)
        """
        self.config = self._load_config()
        self.api_key = api_key or self.config.get("api_key")
        self.instance_url = instance_url or self.config.get("instance_url", "http://localhost:8080")
        self.enabled = self.config.get("enabled", False) and bool(self.api_key)
        
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        
        if self.enabled:
            logger.info(f"[ZeroClaw] Connected to {self.instance_url}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load ZeroClaw configuration from config.json"""
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                return config.get("zeroclaw", {})
        except Exception as e:
            logger.debug(f"[ZeroClaw] Could not load config: {e}")
            return {}
    
    def health_check(self) -> bool:
        """Check if ZeroClaw is reachable"""
        if not self.enabled:
            return False
        
        try:
            response = self.session.get(f"{self.instance_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"[ZeroClaw] Health check failed: {e}")
            return False
    
    def ingest_price_data(self, prices: List[Dict[str, Any]]) -> bool:
        """
        Send price data to ZeroClaw for storage/processing.
        
        Args:
            prices: List of price data points
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "trading_bot",
                "data_type": "prices",
                "records": prices
            }
            
            response = self.session.post(
                f"{self.instance_url}/api/v1/ingest",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug(f"[ZeroClaw] Ingested {len(prices)} price records")
                return True
            else:
                logger.warning(f"[ZeroClaw] Ingest failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"[ZeroClaw] Error ingesting prices: {e}")
            return False
    
    def ingest_trade_data(self, trade: Dict[str, Any]) -> bool:
        """
        Send trade execution data to ZeroClaw.
        
        Args:
            trade: Trade execution record
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "trading_bot",
                "data_type": "trade",
                "record": trade
            }
            
            response = self.session.post(
                f"{self.instance_url}/api/v1/ingest",
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"[ZeroClaw] Error ingesting trade: {e}")
            return False
    
    def get_processed_data(self, query: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Retrieve processed/analytics data from ZeroClaw.
        
        Args:
            query: Query string or identifier
            params: Optional query parameters
            
        Returns:
            Processed data or None
        """
        if not self.enabled:
            return None
        
        try:
            payload = {
                "query": query,
                "params": params or {}
            }
            
            response = self.session.post(
                f"{self.instance_url}/api/v1/query",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"[ZeroClaw] Query error: {e}")
            return None
    
    def setup_pipeline(self, pipeline_config: Dict[str, Any]) -> bool:
        """
        Configure a data pipeline in ZeroClaw.
        
        Args:
            pipeline_config: Pipeline configuration
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            response = self.session.post(
                f"{self.instance_url}/api/v1/pipelines",
                json=pipeline_config,
                timeout=10
            )
            
            return response.status_code in [200, 201]
            
        except Exception as e:
            logger.error(f"[ZeroClaw] Pipeline setup error: {e}")
            return False
    
    def get_analytics_summary(self, days: int = 7) -> Optional[Dict[str, Any]]:
        """
        Get analytics summary from ZeroClaw.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Analytics data or None
        """
        return self.get_processed_data(
            "trading_analytics_summary",
            {"days": days}
        )
    
    def stream_alerts(self, alert_data: Dict[str, Any]) -> bool:
        """
        Stream alert data to ZeroClaw for routing.
        
        Args:
            alert_data: Alert information
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "trading_bot",
                "data_type": "alert",
                "record": alert_data
            }
            
            response = self.session.post(
                f"{self.instance_url}/api/v1/alerts",
                json=payload,
                timeout=5
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"[ZeroClaw] Alert streaming error: {e}")
            return False


class ZeroClawDataPipeline:
    """
    Higher-level data pipeline integration for the trading bot.
    Automatically sends data to ZeroClaw when available.
    """
    
    def __init__(self):
        self.connector = ZeroClawConnector()
        self._enabled = self.connector.enabled
    
    def on_price_update(self, prices: List[Dict[str, Any]]):
        """Called when new prices are fetched"""
        if self._enabled:
            self.connector.ingest_price_data(prices)
    
    def on_trade_executed(self, trade: Dict[str, Any]):
        """Called when a trade is executed"""
        if self._enabled:
            self.connector.ingest_trade_data(trade)
    
    def on_alert(self, alert: Dict[str, Any]):
        """Called when an alert is triggered"""
        if self._enabled:
            self.connector.stream_alerts(alert)
    
    def get_enhanced_analytics(self, days: int = 7) -> Optional[Dict[str, Any]]:
        """Get analytics from ZeroClaw if available, else None"""
        if self._enabled:
            return self.connector.get_analytics_summary(days)
        return None


def get_pipeline() -> ZeroClawDataPipeline:
    """Get singleton pipeline instance"""
    return ZeroClawDataPipeline()


if __name__ == "__main__":
    print("ZeroClaw Data Pipeline Connector - Test Mode")
    print("=" * 60)
    
    connector = ZeroClawConnector()
    
    print(f"\nConfiguration:")
    print(f"  Enabled: {connector.enabled}")
    print(f"  Instance: {connector.instance_url}")
    print(f"  API Key: {'✅ Set' if connector.api_key else '❌ Not set'}")
    
    if connector.enabled:
        print(f"\nHealth Check: {'✅ OK' if connector.health_check() else '❌ Failed'}")
        
        # Test price ingestion
        test_prices = [
            {"exchange": "binance", "symbol": "BTC/USDT", "price": 68000, "timestamp": datetime.utcnow().isoformat()},
            {"exchange": "coinbase", "symbol": "BTC/USD", "price": 68100, "timestamp": datetime.utcnow().isoformat()}
        ]
        
        print(f"\nTest Price Ingestion: ", end="")
        if connector.ingest_price_data(test_prices):
            print("✅ Success")
        else:
            print("❌ Failed")
    else:
        print("\nZeroClaw is not enabled. To enable:")
        print("  1. Update config.json with zeroclaw settings")
        print("  2. Set instance_url and api_key")
        print("  3. Set enabled: true")
