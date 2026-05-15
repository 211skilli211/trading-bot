"""
Polymarket Smart Money Module — Configuration
"""
import os
from dataclasses import dataclass, field
from typing import Optional

# Load from .env via the existing secure loader
def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


@dataclass
class PolymarketConfig:
    """Polymarket API configuration."""
    api_key: str = _env("POLYMARKET_API_KEY", "")
    api_secret: str = _env("POLYMARKET_API_SECRET", "")
    api_passphrase: str = _env("POLYMARKET_API_PASSPHRASE", "")
    private_key: str = _env("POLYMARKET_PRIVATE_KEY", "")
    relayer_api_key: str = _env("RELAYER_API_KEY", "")
    relayer_address: str = _env("RELAYER_ADDRESS", "")
    chain_id: int = 137  # Polygon


@dataclass
class SmartMoneyConfig:
    """Smart money detection thresholds."""
    # Whale detection
    whale_min_trade_size: float = 1000.0       # USD
    whale_min_total_volume: float = 10000.0    # USD
    
    # Win rate detection
    win_rate_min_trades: int = 20              # minimum trades to qualify
    win_rate_threshold: float = 0.70           # 70% win rate
    
    # Early bird detection
    early_bird_max_age_hours: int = 48         # market must be < 48h old
    early_bird_min_trade_size: float = 100.0   # USD
    
    # Scoring weights
    weight_whale: float = 0.4
    weight_win_rate: float = 0.35
    weight_early_bird: float = 0.25


@dataclass
class ScannerConfig:
    """Market scanner settings."""
    scan_interval_minutes: int = 15
    min_volume_usd: float = 1000.0
    max_markets_per_scan: int = 500
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    clob_api_url: str = "https://clob.polymarket.com"
    data_api_url: str = "https://data-api.polymarket.com"


@dataclass
class AlertConfig:
    """Alert settings."""
    enabled: bool = True
    whatsapp_enabled: bool = True
    telegram_enabled: bool = False
    min_signal_score: float = 60.0  # 0-100, only alert above this
    daily_summary_hour: int = 9     # 9 AM UTC
    cooldown_minutes: int = 30      # don't re-alert same wallet/market


@dataclass
class DatabaseConfig:
    """Database settings."""
    db_path: str = os.path.join(os.path.dirname(__file__), "..", "data", "polymarket_smart_money.db")


@dataclass
class ModuleConfig:
    """Master configuration for the Polymarket Smart Money module."""
    polymarket: PolymarketConfig = field(default_factory=PolymarketConfig)
    smart_money: SmartMoneyConfig = field(default_factory=SmartMoneyConfig)
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)


# Singleton
config = ModuleConfig()
