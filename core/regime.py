#!/usr/bin/env python3
"""
Market Regime Detector
=====================
Detects market regime based on macro liquidity signals.

Regimes:
- DEFENSIVE: Low liquidity, risk-off, tight risk controls
- NEUTRAL: Balanced conditions, normal risk
- RISK_ON: High liquidity, risk-on, expanded opportunities

Signals:
- USDT Dominance (fear/greed proxy)
- Stablecoin Supply (liquidity proxy)
- Macro Event Calendar (volatility avoidance)
"""

import requests
import logging
from datetime import datetime, timezone
from typing import Literal, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MarketRegime = Literal['DEFENSIVE', 'NEUTRAL', 'RISK_ON']


@dataclass
class RegimeData:
    """Current market regime data"""
    regime: MarketRegime
    usdt_dominance: float
    stablecoin_supply: float
    timestamp: str
    config: Dict


class RegimeDetector:
    """
    Detects market regime based on macro liquidity signals.
    
    Usage:
        detector = RegimeDetector()
        regime = detector.detect_regime()
        config = detector.get_regime_config(regime)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize regime detector.
        
        Args:
            config: Optional configuration override
        """
        self.config = config or {}
        
        # Thresholds for regime detection
        self.usdt_dom_defensive = self.config.get('usdt_dom_defensive', 8.5)  # >8.5% = defensive
        self.usdt_dom_risk_on = self.config.get('usdt_dom_risk_on', 7.0)      # <7% = risk-on
        self.stable_supply_threshold = self.config.get('stable_supply_threshold', 150)  # Billions
        
        # Cache
        self._last_regime: Optional[MarketRegime] = None
        self._last_check: Optional[str] = None
        
        logger.info(f"[RegimeDetector] Initialized")
        logger.info(f"  DEFENSIVE threshold: USDT dominance >{self.usdt_dom_defensive}%")
        logger.info(f"  RISK_ON threshold: USDT dominance <{self.usdt_dom_risk_on}%")
    
    def get_usdt_dominance(self) -> float:
        """
        Fetch USDT dominance from CoinGecko.
        
        USDT dominance > 8.5% indicates fear/distribution (defensive)
        USDT dominance < 7% indicates risk-on/accumulation
        
        Returns:
            USDT dominance percentage (0-100)
        """
        try:
            # Fetch global crypto market data
            resp = requests.get(
                'https://api.coingecko.com/api/v3/global',
                timeout=10
            )
            data = resp.json()
            
            # Get USDT market cap and calculate dominance
            usdt_data = data.get('data', {}).get('market_cap_percentage', {})
            usdt_dominance = usdt_data.get('usdt', 0)
            
            logger.debug(f"[RegimeDetector] USDT dominance: {usdt_dominance:.2f}%")
            return float(usdt_dominance)
            
        except Exception as e:
            logger.warning(f"[RegimeDetector] Error fetching USDT dominance: {e}")
            # Return neutral default
            return 7.5
    
    def get_stablecoin_supply(self) -> float:
        """
        Fetch total stablecoin market cap (proxy for liquidity).
        
        Growing stablecoin supply = liquidity incoming (risk-on)
        Shrinking stablecoin supply = liquidity leaving (defensive)
        
        Returns:
            Total stablecoin market cap in billions
        """
        try:
            # Fetch major stablecoins
            stablecoins = ['tether', 'usd-coin', 'dai', 'binance-usd']
            ids = ','.join(stablecoins)
            
            resp = requests.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={
                    'ids': ids,
                    'vs_currencies': 'usd',
                    'include_market_cap': 'true'
                },
                timeout=10
            )
            data = resp.json()
            
            total_supply = sum(
                coin.get('usd_market_cap', 0) / 1e9  # Convert to billions
                for coin in data.values()
            )
            
            logger.debug(f"[RegimeDetector] Stablecoin supply: ${total_supply:.1f}B")
            return total_supply
            
        except Exception as e:
            logger.warning(f"[RegimeDetector] Error fetching stablecoin supply: {e}")
            # Return neutral default
            return 140.0
    
    def detect_regime(self) -> MarketRegime:
        """
        Determine current market regime.
        
        Logic:
        - DEFENSIVE: High USDT dominance (>8.5%) = fear, distribution
        - RISK_ON: Low USDT dominance (<7%) + growing stablecoins = greed, accumulation
        - NEUTRAL: Everything else
        
        Returns:
            MarketRegime: 'DEFENSIVE', 'NEUTRAL', or 'RISK_ON'
        """
        try:
            usdt_dom = self.get_usdt_dominance()
            stable_supply = self.get_stablecoin_supply()
            
            # DEFENSIVE: High USDT dominance indicates fear
            if usdt_dom > self.usdt_dom_defensive:
                regime = 'DEFENSIVE'
            
            # RISK_ON: Low USDT dominance + high stablecoin supply
            elif usdt_dom < self.usdt_dom_risk_on and stable_supply > self.stable_supply_threshold:
                regime = 'RISK_ON'
            
            # NEUTRAL: Mixed signals
            else:
                regime = 'NEUTRAL'
            
            # Log regime change
            if regime != self._last_regime:
                logger.info(f"[RegimeDetector] Regime changed: {self._last_regime} -> {regime}")
                logger.info(f"  USDT dominance: {usdt_dom:.2f}%")
                logger.info(f"  Stablecoin supply: ${stable_supply:.1f}B")
                self._last_regime = regime
            
            self._last_check = datetime.now(timezone.utc).isoformat()
            return regime
            
        except Exception as e:
            logger.error(f"[RegimeDetector] Error detecting regime: {e}")
            return 'NEUTRAL'  # Safe default
    
    def get_regime_config(self, regime: Optional[MarketRegime] = None) -> Dict:
        """
        Get trading configuration for current regime.
        
        Args:
            regime: Optional regime override (uses current if None)
            
        Returns:
            Configuration dict with position sizes, stops, etc.
        """
        if regime is None:
            regime = self.detect_regime()
        
        configs = {
            'DEFENSIVE': {
                'name': 'DEFENSIVE',
                'description': 'Risk-off, tight risk controls',
                'max_position_pct': 0.005,      # 0.5% max position
                'max_daily_risk_pct': 0.01,     # 1% daily risk limit
                'stop_loss_pct': 0.05,          # 5% stop loss
                'take_profit_pct': 0.10,        # 10% take profit
                'max_daily_trades': 5,
                'leverage_max': 1.0,            # No leverage
                'strategies_enabled': ['binary_arbitrage', 'low_risk_only'],
                'pause_before_macro': True,
                'accumulation_only': True,      # Only buy in accumulation zones
                'avoid_new_positions': True     # Close existing, no new
            },
            'NEUTRAL': {
                'name': 'NEUTRAL',
                'description': 'Balanced conditions',
                'max_position_pct': 0.01,       # 1% max position
                'max_daily_risk_pct': 0.03,     # 3% daily risk limit
                'stop_loss_pct': 0.07,          # 7% stop loss
                'take_profit_pct': 0.15,        # 15% take profit
                'max_daily_trades': 15,
                'leverage_max': 2.0,
                'strategies_enabled': ['binary_arbitrage', 'sniper', 'momentum', 'pairs'],
                'pause_before_macro': True,
                'accumulation_only': False,
                'avoid_new_positions': False
            },
            'RISK_ON': {
                'name': 'RISK_ON',
                'description': 'High liquidity, expanded opportunities',
                'max_position_pct': 0.015,      # 1.5% max position
                'max_daily_risk_pct': 0.05,     # 5% daily risk limit
                'stop_loss_pct': 0.10,          # 10% stop loss
                'take_profit_pct': 0.25,        # 25% take profit
                'max_daily_trades': 30,
                'leverage_max': 3.0,
                'strategies_enabled': ['all'],
                'pause_before_macro': False,
                'accumulation_only': False,
                'avoid_new_positions': False
            }
        }
        
        return configs.get(regime, configs['NEUTRAL'])
    
    def get_full_status(self) -> RegimeData:
        """Get complete regime status with data"""
        regime = self.detect_regime()
        return RegimeData(
            regime=regime,
            usdt_dominance=self.get_usdt_dominance(),
            stablecoin_supply=self.get_stablecoin_supply(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            config=self.get_regime_config(regime)
        )
    
    def should_trade(self) -> tuple[bool, str]:
        """
        Check if trading should be allowed.
        
        Returns:
            (should_trade, reason)
        """
        regime = self.detect_regime()
        config = self.get_regime_config(regime)
        
        if config.get('avoid_new_positions'):
            return False, f"Regime {regime}: Avoiding new positions"
        
        return True, f"Regime {regime}: Trading allowed"


# Simple test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("MARKET REGIME DETECTOR TEST")
    print("=" * 60)
    
    detector = RegimeDetector()
    
    # Get current regime
    regime = detector.detect_regime()
    config = detector.get_regime_config(regime)
    
    print(f"\nCurrent Regime: {regime}")
    print(f"Description: {config['description']}")
    print(f"\nTrading Parameters:")
    print(f"  Max Position: {config['max_position_pct']*100:.2f}%")
    print(f"  Stop Loss: {config['stop_loss_pct']*100:.0f}%")
    print(f"  Take Profit: {config['take_profit_pct']*100:.0f}%")
    print(f"  Max Daily Trades: {config['max_daily_trades']}")
    print(f"  Max Leverage: {config['leverage_max']}x")
    print(f"\nStrategies Enabled: {', '.join(config['strategies_enabled'])}")
    
    # Check if should trade
    should_trade, reason = detector.should_trade()
    print(f"\nTrading Status: {'✅ ALLOWED' if should_trade else '❌ PAUSED'}")
    print(f"Reason: {reason}")
    
    print("\n" + "=" * 60)
