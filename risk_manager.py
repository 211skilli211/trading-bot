#!/usr/bin/env python3
"""
Risk Management Module
Ensures trading bot doesn't over-expose or spiral into losses.
Part of the modular trading bot blueprint.

Core Responsibilities:
- Position Limits: Cap max exposure per asset
- Stop-Loss Rules: Auto-exit if losses exceed threshold
- Capital Allocation: Risk fixed % of balance per trade
- Audit Logging: Record every risk check
"""

import json
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Macro/Regime integration
try:
    from core.regime import RegimeDetector, MarketRegime
    REGIME_AVAILABLE = True
except ImportError:
    REGIME_AVAILABLE = False

try:
    from utils.event_calendar import should_pause_trading
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False
try:
    from core.accumulation import AccumulationMonitor
    ACCUMULATION_AVAILABLE = True
except ImportError:
    ACCUMULATION_AVAILABLE = False


class RiskDecision(Enum):
    """Risk management decision types."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY = "MODIFY"  # Reduce position size
    HOLD = "HOLD"


@dataclass
class RiskCheck:
    """Structured risk check output."""
    timestamp: str
    decision: str
    reason: str
    allocation_usd: float
    position_size_btc: float
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    max_position: float
    current_exposure: float
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class Position:
    """Track an open position for risk monitoring."""
    position_id: str
    timestamp: str
    exchange: str
    side: str  # LONG or SHORT
    entry_price: float
    quantity: float
    stop_loss_price: float
    take_profit_price: Optional[float]
    max_loss_pct: float
    status: str  # OPEN, STOPPED, CLOSED
    unrealized_pnl: float = 0.0
    close_price: Optional[float] = None
    close_timestamp: Optional[str] = None


class RiskManager:
    """
    Risk Management System for trading bot.
    
    Enforces:
    - Maximum position size per asset
    - Capital allocation limits per trade
    - Stop-loss and take-profit levels
    - Overall portfolio exposure limits
    """
    
    def __init__(
        self,
        max_position_btc: float = 0.05,      # Max 0.05 BTC per position
        stop_loss_pct: float = 0.02,          # 2% stop loss
        take_profit_pct: Optional[float] = None,  # Optional take profit
        capital_pct_per_trade: float = 0.05,  # Risk 5% of balance per trade
        max_total_exposure_pct: float = 0.30, # Max 30% of balance in open positions
        initial_balance: float = 10000.0,     # Starting balance in USD
        daily_loss_limit_pct: float = 0.05,   # Stop trading after 5% daily loss
        use_regime_detection: bool = True,     # Enable macro regime detection
        use_macro_calendar: bool = True,       # Enable macro event calendar
        use_accumulation_zones: bool = True    # Enable accumulation zone filtering
    ):
        """
        Initialize Risk Manager.
        
        Args:
            max_position_btc: Maximum position size in BTC
            stop_loss_pct: Stop loss percentage (e.g., 0.02 = 2%)
            take_profit_pct: Take profit percentage (optional)
            capital_pct_per_trade: Percentage of balance to risk per trade
            max_total_exposure_pct: Maximum total exposure as % of balance
            initial_balance: Starting account balance in USD
            daily_loss_limit_pct: Daily loss limit before halting
            use_regime_detection: Enable macro regime-based risk adjustment
            use_macro_calendar: Enable macro event pause
            use_accumulation_zones: Only allow trades in accumulation zones
        """
        # Store base parameters (will be overridden by regime if enabled)
        self._base_max_position_btc = max_position_btc
        self._base_stop_loss_pct = stop_loss_pct
        self._base_take_profit_pct = take_profit_pct
        self._base_capital_pct = capital_pct_per_trade
        
        # Initialize with base values
        self.max_position_btc = Decimal(str(max_position_btc))
        self.stop_loss_pct = Decimal(str(stop_loss_pct))
        self.take_profit_pct = Decimal(str(take_profit_pct)) if take_profit_pct else None
        self.capital_pct_per_trade = Decimal(str(capital_pct_per_trade))
        self.max_total_exposure_pct = Decimal(str(max_total_exposure_pct))
        self.balance = Decimal(str(initial_balance))
        self.initial_balance = Decimal(str(initial_balance))
        self.daily_loss_limit_pct = Decimal(str(daily_loss_limit_pct))
        
        # Macro/Regime settings
        self.use_regime_detection = use_regime_detection and REGIME_AVAILABLE
        self.use_macro_calendar = use_macro_calendar and CALENDAR_AVAILABLE
        self.use_accumulation_zones = use_accumulation_zones and ACCUMULATION_AVAILABLE
        
        # Initialize regime detector
        self.regime_detector = None
        self.current_regime = None
        self.regime_config = None
        
        if self.use_regime_detection:
            try:
                self.regime_detector = RegimeDetector()
                self._refresh_regime()
                print(f"[RiskManager] ✅ Regime detection enabled")
            except Exception as e:
                print(f"[RiskManager] ⚠️ Regime detection failed: {e}")
                self.use_regime_detection = False
        
        # Initialize accumulation monitor
        self.accumulation_monitor = None
        if self.use_accumulation_zones:
            try:
                self.accumulation_monitor = AccumulationMonitor()
                print(f"[RiskManager] ✅ Accumulation zones enabled")
            except Exception as e:
                print(f"[RiskManager] ⚠️ Accumulation zones failed: {e}")
                self.use_accumulation_zones = False
        
        # Position tracking
        self.positions: List[Position] = []
        self.position_counter = 0
        
        # Daily tracking
        self.daily_pnl = Decimal('0')
        self.daily_loss_limit_hit = False
        self.trading_halted = False
        
        # Statistics
        self.total_trades_approved = 0
        self.total_trades_rejected = 0
        self.stop_losses_triggered = 0
        
        print(f"[RiskManager] Initialized")
        if self.current_regime:
            print(f"  Current Regime: {self.current_regime}")
        print(f"  Max Position: {float(self.max_position_btc):.4f} BTC")
        print(f"  Stop Loss: {float(self.stop_loss_pct):.2%}")
        print(f"  Capital per Trade: {float(self.capital_pct_per_trade):.2%}")
        print(f"  Max Exposure: {float(self.max_total_exposure_pct):.2%}")
        print(f"  Daily Loss Limit: {float(self.daily_loss_limit_pct):.2%}")
    
    def _refresh_regime(self):
        """Refresh current market regime"""
        if not self.regime_detector:
            return
        
        new_regime = self.regime_detector.detect_regime()
        new_config = self.regime_detector.get_regime_config(new_regime)
        
        # Check if regime changed
        if new_regime != self.current_regime:
            self.current_regime = new_regime
            self.regime_config = new_config
            
            # Apply regime-based parameters
            self._apply_regime_config()
            
            logger.info(f"[RiskManager] Regime changed to {new_regime}")
    
    def _apply_regime_config(self):
        """Apply regime-based risk parameters"""
        if not self.regime_config:
            return
        
        # Override base parameters with regime values
        self.max_position_btc = Decimal(str(self.regime_config.get(
            'max_position_pct', self._base_max_position_btc
        )))
        self.stop_loss_pct = Decimal(str(self.regime_config.get(
            'stop_loss_pct', self._base_stop_loss_pct
        )))
        self.take_profit_pct = Decimal(str(self.regime_config.get(
            'take_profit_pct', self._base_take_profit_pct
        ))) if self.regime_config.get('take_profit_pct') else None
        self.capital_pct_per_trade = Decimal(str(self.regime_config.get(
            'max_position_pct', self._base_capital_pct  # Use same as max_position
        )))
        
        # Check if should pause trading
        if self.regime_config.get('avoid_new_positions'):
            self.trading_halted = True
            logger.warning(f"[RiskManager] Trading halted due to {self.current_regime} regime")
        else:
            self.trading_halted = False
    
    def assess_trade(
        self,
        trade_signal: Dict[str, Any],
        current_price: float,
        current_positions: Optional[List[Position]] = None,
        symbol: Optional[str] = None
    ) -> RiskCheck:
        """
        Assess trade against risk rules.
        
        Args:
            trade_signal: Strategy engine trade signal
            current_price: Current market price
            current_positions: List of current open positions
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
        
        Returns:
            RiskCheck with decision and details
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Refresh regime if using regime detection
        if self.use_regime_detection:
            self._refresh_regime()
        
        # Check macro event calendar
        if self.use_macro_calendar:
            should_pause, pause_reason = should_pause_trading()
            if should_pause:
                return RiskCheck(
                    timestamp=timestamp,
                    decision=RiskDecision.REJECT.value,
                    reason=f"Macro event pause: {pause_reason}",
                    allocation_usd=0.0,
                    position_size_btc=0.0,
                    stop_loss_price=None,
                    take_profit_price=None,
                    max_position=float(self.max_position_btc),
                    current_exposure=self._calculate_exposure(),
                    risk_level="CRITICAL"
                )
        
        # Check accumulation zones
        if self.use_accumulation_zones and symbol and self.regime_config:
            if self.regime_config.get('accumulation_only', False):
                base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
                if not self.accumulation_monitor.should_accumulate(base_symbol, current_price):
                    zone_status = self.accumulation_monitor.get_status(base_symbol, current_price)
                    if zone_status:
                        return RiskCheck(
                            timestamp=timestamp,
                            decision=RiskDecision.REJECT.value,
                            reason=f"Price ${current_price:,.2f} not in accumulation zone for {base_symbol} (${zone_status.zone_min:,.2f} - ${zone_status.zone_max:,.2f})",
                            allocation_usd=0.0,
                            position_size_btc=0.0,
                            stop_loss_price=None,
                            take_profit_price=None,
                            max_position=float(self.max_position_btc),
                            current_exposure=self._calculate_exposure(),
                            risk_level="MEDIUM"
                        )
        
        # Check if trading is halted
        if self.trading_halted:
            reason = f"Trading halted - {self.current_regime} regime" if self.current_regime else "Trading halted - daily loss limit exceeded"
            return RiskCheck(
                timestamp=timestamp,
                decision=RiskDecision.REJECT.value,
                reason=reason,
                allocation_usd=0.0,
                position_size_btc=0.0,
                stop_loss_price=None,
                take_profit_price=None,
                max_position=float(self.max_position_btc),
                current_exposure=self._calculate_exposure(),
                risk_level="CRITICAL"
            )
        
        # Check daily loss limit
        daily_loss_pct = abs(self.daily_pnl) / self.initial_balance
        if daily_loss_pct >= self.daily_loss_limit_pct:
            self.daily_loss_limit_hit = True
            self.trading_halted = True
            return RiskCheck(
                timestamp=timestamp,
                decision=RiskDecision.REJECT.value,
                reason=f"Daily loss limit hit: {float(daily_loss_pct):.2%}",
                allocation_usd=0.0,
                position_size_btc=0.0,
                stop_loss_price=None,
                take_profit_price=None,
                max_position=float(self.max_position_btc),
                current_exposure=self._calculate_exposure(),
                risk_level="CRITICAL"
            )
        
        # If no trade signal, return HOLD
        if trade_signal.get("decision") != "TRADE":
            return RiskCheck(
                timestamp=timestamp,
                decision=RiskDecision.HOLD.value,
                reason="No trade signal from strategy engine",
                allocation_usd=0.0,
                position_size_btc=0.0,
                stop_loss_price=None,
                take_profit_price=None,
                max_position=float(self.max_position_btc),
                current_exposure=self._calculate_exposure(),
                risk_level="LOW"
            )
        
        # Calculate capital allocation
        allocation = self.balance * self.capital_pct_per_trade
        position_size = allocation / Decimal(str(current_price))
        
        # Check position size against max
        if position_size > self.max_position_btc:
            # Reduce to max position
            position_size = self.max_position_btc
            allocation = position_size * Decimal(str(current_price))
            modification_reason = f"Position reduced to max {float(self.max_position_btc):.4f} BTC"
            decision = RiskDecision.MODIFY.value
        else:
            modification_reason = None
            decision = RiskDecision.APPROVE.value
        
        # Check total exposure
        current_exposure = self._calculate_exposure()
        new_exposure = current_exposure + (float(position_size) * current_price)
        max_exposure_usd = float(self.balance) * float(self.max_total_exposure_pct)
        
        if new_exposure > max_exposure_usd:
            # Reduce position to fit within exposure limit
            available_exposure = max_exposure_usd - current_exposure
            if available_exposure <= 0:
                self.total_trades_rejected += 1
                return RiskCheck(
                    timestamp=timestamp,
                    decision=RiskDecision.REJECT.value,
                    reason=f"Max exposure limit reached: ${current_exposure:,.2f}",
                    allocation_usd=0.0,
                    position_size_btc=0.0,
                    stop_loss_price=None,
                    take_profit_price=None,
                    max_position=float(self.max_position_btc),
                    current_exposure=current_exposure,
                    risk_level="HIGH"
                )
            
            # Reduce position to fit available exposure
            position_size = Decimal(str(available_exposure)) / Decimal(str(current_price))
            allocation = position_size * Decimal(str(current_price))
            decision = RiskDecision.MODIFY.value
            modification_reason = f"Reduced to fit exposure limit (${available_exposure:,.2f} available)"
        
        # Calculate stop-loss and take-profit prices
        buy_price = Decimal(str(current_price))
        stop_loss_price = float(buy_price * (Decimal('1') - self.stop_loss_pct))
        
        take_profit_price = None
        if self.take_profit_pct:
            take_profit_price = float(buy_price * (Decimal('1') + Decimal(str(self.take_profit_pct))))
        
        # Determine risk level
        if float(position_size) >= float(self.max_position_btc) * 0.9:
            risk_level = "HIGH"
        elif float(position_size) >= float(self.max_position_btc) * 0.5:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Build reason string
        if decision == RiskDecision.APPROVE.value:
            reason = f"Trade approved: {float(position_size):.4f} BTC @ ${current_price:,.2f}"
            reason += f", Stop-loss: ${stop_loss_price:,.2f} ({float(self.stop_loss_pct):.2%})"
        elif decision == RiskDecision.MODIFY.value:
            reason = modification_reason or "Position modified to meet risk limits"
        
        if decision in [RiskDecision.APPROVE.value, RiskDecision.MODIFY.value]:
            self.total_trades_approved += 1
            
            # Create position record
            self._create_position(
                exchange=trade_signal.get("buy_exchange", "Unknown"),
                side="LONG",
                entry_price=current_price,
                quantity=float(position_size),
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price
            )
        else:
            self.total_trades_rejected += 1
        
        return RiskCheck(
            timestamp=timestamp,
            decision=decision,
            reason=reason,
            allocation_usd=float(allocation),
            position_size_btc=float(position_size),
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            max_position=float(self.max_position_btc),
            current_exposure=self._calculate_exposure(),
            risk_level=risk_level
        )
    
    def _create_position(
        self,
        exchange: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss_price: float,
        take_profit_price: Optional[float]
    ) -> Position:
        """Create and track a new position."""
        self.position_counter += 1
        
        position = Position(
            position_id=f"POS_{self.position_counter:04d}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            exchange=exchange,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            max_loss_pct=float(self.stop_loss_pct),
            status="OPEN"
        )
        
        self.positions.append(position)
        
        print(f"\n📋 POSITION CREATED: {position.position_id}")
        print(f"   Exchange: {exchange}")
        print(f"   Side: {side}")
        print(f"   Size: {quantity:.4f} BTC @ ${entry_price:,.2f}")
        print(f"   Stop-Loss: ${stop_loss_price:,.2f}")
        if take_profit_price:
            print(f"   Take-Profit: ${take_profit_price:,.2f}")
        
        return position
    
    def check_stop_losses(self, current_prices: Dict[str, float]) -> List[Position]:
        """
        Check all open positions for stop-loss or take-profit triggers.
        
        Args:
            current_prices: Dict of exchange -> current price
        
        Returns:
            List of positions that were closed
        """
        closed_positions = []
        
        for position in self.positions:
            if position.status != "OPEN":
                continue
            
            current_price = current_prices.get(position.exchange)
            if not current_price:
                continue
            
            triggered = False
            trigger_reason = ""
            
            # Check stop-loss (for LONG positions)
            if position.side == "LONG":
                if current_price <= position.stop_loss_price:
                    triggered = True
                    trigger_reason = "STOP_LOSS"
                elif position.take_profit_price and current_price >= position.take_profit_price:
                    triggered = True
                    trigger_reason = "TAKE_PROFIT"
            
            # Check stop-loss (for SHORT positions)
            elif position.side == "SHORT":
                if current_price >= position.stop_loss_price:
                    triggered = True
                    trigger_reason = "STOP_LOSS"
                elif position.take_profit_price and current_price <= position.take_profit_price:
                    triggered = True
                    trigger_reason = "TAKE_PROFIT"
            
            if triggered:
                position.status = "CLOSED"
                position.close_price = current_price
                position.close_timestamp = datetime.now(timezone.utc).isoformat()
                
                # Calculate P&L
                if position.side == "LONG":
                    pnl = (current_price - position.entry_price) * position.quantity
                else:
                    pnl = (position.entry_price - current_price) * position.quantity
                
                position.unrealized_pnl = pnl
                self.daily_pnl += Decimal(str(pnl))
                
                if trigger_reason == "STOP_LOSS":
                    self.stop_losses_triggered += 1
                
                closed_positions.append(position)
                
                print(f"\n🚨 POSITION CLOSED: {position.position_id}")
                print(f"   Reason: {trigger_reason}")
                print(f"   Exit Price: ${current_price:,.2f}")
                print(f"   P&L: ${pnl:,.2f}")
        
        return closed_positions
    
    def _calculate_exposure(self) -> float:
        """Calculate total USD exposure from open positions."""
        exposure = 0.0
        for pos in self.positions:
            if pos.status == "OPEN":
                exposure += pos.quantity * pos.entry_price
        return exposure
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio risk summary."""
        open_positions = [p for p in self.positions if p.status == "OPEN"]
        closed_positions = [p for p in self.positions if p.status == "CLOSED"]
        
        total_pnl = sum(p.unrealized_pnl for p in self.positions)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "balance": float(self.balance),
            "initial_balance": float(self.initial_balance),
            "total_pnl": round(total_pnl, 2),
            "daily_pnl": float(self.daily_pnl),
            "daily_loss_limit_hit": self.daily_loss_limit_hit,
            "trading_halted": self.trading_halted,
            "open_positions": len(open_positions),
            "closed_positions": len(closed_positions),
            "total_exposure_usd": round(self._calculate_exposure(), 2),
            "max_exposure_usd": float(self.balance) * float(self.max_total_exposure_pct),
            "trades_approved": self.total_trades_approved,
            "trades_rejected": self.total_trades_rejected,
            "stop_losses_triggered": self.stop_losses_triggered,
            "positions": [asdict(p) for p in self.positions[-10:]]  # Last 10
        }
    
    def print_summary(self):
        """Print portfolio summary to console."""
        summary = self.get_portfolio_summary()
        
        print("\n" + "=" * 60)
        print("RISK MANAGEMENT PORTFOLIO SUMMARY")
        print("=" * 60)
        print(f"Balance:          ${summary['balance']:,.2f}")
        print(f"Total P&L:        ${summary['total_pnl']:+,.2f}")
        print(f"Daily P&L:        ${summary['daily_pnl']:+,.2f}")
        print(f"Open Positions:   {summary['open_positions']}")
        print(f"Exposure:         ${summary['total_exposure_usd']:,.2f} / ${summary['max_exposure_usd']:,.2f}")
        print(f"Trades Approved:  {summary['trades_approved']}")
        print(f"Trades Rejected:  {summary['trades_rejected']}")
        print(f"Stop Losses Hit:  {summary['stop_losses_triggered']}")
        if summary['trading_halted']:
            print("⚠️  TRADING HALTED - Daily loss limit exceeded")
        print("=" * 60)


# Example usage and testing
if __name__ == "__main__":
    print("Risk Manager - Test Mode")
    print("=" * 60)
    
    # Test 1: Normal trade approval
    print("\n[Test 1] Normal trade approval")
    print("-" * 40)
    
    rm = RiskManager(
        max_position_btc=0.05,
        stop_loss_pct=0.02,
        capital_pct_per_trade=0.05,
        initial_balance=10000
    )
    
    trade_signal = {
        "decision": "TRADE",
        "buy_exchange": "Binance",
        "sell_exchange": "Coinbase",
        "buy_price": 68000,
        "sell_price": 69000
    }
    
    result = rm.assess_trade(trade_signal, current_price=68000)
    print(f"\nDecision: {result.decision}")
    print(f"Reason: {result.reason}")
    print(f"Allocation: ${result.allocation_usd:,.2f}")
    print(f"Position Size: {result.position_size_btc:.4f} BTC")
    print(f"Stop-Loss: ${result.stop_loss_price:,.2f}")
    print(f"Risk Level: {result.risk_level}")
    
    # Test 2: Position exceeds max (should be modified)
    print("\n[Test 2] Position size reduction")
    print("-" * 40)
    
    rm2 = RiskManager(
        max_position_btc=0.01,  # Very small max
        stop_loss_pct=0.02,
        capital_pct_per_trade=0.50,  # But wants 50% of balance
        initial_balance=10000
    )
    
    result2 = rm2.assess_trade(trade_signal, current_price=68000)
    print(f"\nDecision: {result2.decision}")
    print(f"Reason: {result2.reason}")
    print(f"Position Size: {result2.position_size_btc:.4f} BTC")
    
    # Test 3: Stop-loss check
    print("\n[Test 3] Stop-loss trigger simulation")
    print("-" * 40)
    
    # Create a position first
    rm3 = RiskManager(
        max_position_btc=0.05,
        stop_loss_pct=0.02,
        initial_balance=10000
    )
    
    # Manually create a position
    rm3._create_position(
        exchange="Binance",
        side="LONG",
        entry_price=68000,
        quantity=0.01,
        stop_loss_price=66640,  # 2% below entry
        take_profit_price=None
    )
    
    # Check with price above stop-loss (should not trigger)
    print("\nPrice at $67,000 (above stop-loss):")
    closed = rm3.check_stop_losses({"Binance": 67000})
    print(f"Positions closed: {len(closed)}")
    
    # Check with price below stop-loss (should trigger)
    print("\nPrice at $66,000 (below stop-loss):")
    closed = rm3.check_stop_losses({"Binance": 66000})
    print(f"Positions closed: {len(closed)}")
    if closed:
        print(f"P&L: ${closed[0].unrealized_pnl:,.2f}")
    
    # Test 4: Daily loss limit
    print("\n[Test 4] Daily loss limit")
    print("-" * 40)
    
    rm4 = RiskManager(
        max_position_btc=0.05,
        stop_loss_pct=0.02,
        daily_loss_limit_pct=0.05,
        initial_balance=10000
    )
    
    # Simulate a big loss
    rm4.daily_pnl = Decimal('-600')  # $600 loss = 6%
    
    result4 = rm4.assess_trade(trade_signal, current_price=68000)
    print(f"\nDaily P&L: ${float(rm4.daily_pnl):,.2f}")
    print(f"Decision: {result4.decision}")
    print(f"Reason: {result4.reason}")
    print(f"Trading Halted: {rm4.trading_halted}")
    
    # Print summary
    rm.print_summary()
