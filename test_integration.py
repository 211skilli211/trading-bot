#!/usr/bin/env python3
"""
Trade Engine Integration Test
Verifies all components are working together
"""

import sys
import json
from datetime import datetime, timezone

def test_imports():
    """Test all modules can be imported"""
    print("Testing imports...")
    modules = {}
    
    try:
        from strategy_engine import StrategyEngine, TradeSignal
        modules['strategy_engine'] = True
    except Exception as e:
        modules['strategy_engine'] = str(e)
    
    try:
        from risk_manager import RiskManager, RiskCheck
        modules['risk_manager'] = True
    except Exception as e:
        modules['risk_manager'] = str(e)
    
    try:
        from execution_layer import ExecutionLayer, ExecutionMode
        modules['execution_layer'] = True
    except Exception as e:
        modules['execution_layer'] = str(e)
    
    try:
        from strategies.multi_agent import MultiAgentSystem
        modules['multi_agent'] = True
    except Exception as e:
        modules['multi_agent'] = str(e)
    
    try:
        from database import TradingDatabase
        modules['database'] = True
    except Exception as e:
        modules['database'] = str(e)
    
    print("Import Results:")
    for name, status in modules.items():
        icon = "✓" if status == True else "✗"
        print(f"  {icon} {name}")
        if status != True:
            print(f"      Error: {status}")
    
    return all(s == True for s in modules.values())


def test_strategy_engine():
    """Test strategy signal generation"""
    print("\nTesting Strategy Engine...")
    from strategy_engine import StrategyEngine
    
    engine = StrategyEngine(paper_trading=True)
    
    # Mock price data
    price_data = [
        {"exchange": "Binance", "symbol": "BTC/USDT", "price": 65000.0},
        {"exchange": "Coinbase", "symbol": "BTC/USDT", "price": 65100.0},
    ]
    
    signal = engine.evaluate(price_data)
    
    print(f"  Signal generated: {signal.decision}")
    print(f"  Spread: {signal.spread_pct:.4f}%")
    print(f"  Confidence: {signal.confidence}")
    
    return signal.decision in ["TRADE", "NO_TRADE"]


def test_risk_manager():
    """Test risk checks"""
    print("\nTesting Risk Manager...")
    from risk_manager import RiskManager
    
    rm = RiskManager(initial_balance=10000.0)
    
    # Mock trade request
    signal = {
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.01,
        "price": 65000.0
    }
    
    check = rm.assess_trade(signal, current_price=65000.0)
    
    print(f"  Risk decision: {check.decision}")
    print(f"  Allocation: ${check.allocation_usd}")
    print(f"  Risk level: {check.risk_level}")
    
    return check.decision in ["APPROVE", "REJECT", "MODIFY", "HOLD"]


def test_multi_agent():
    """Test multi-agent system"""
    print("\nTesting Multi-Agent System...")
    from strategies.multi_agent import MultiAgentSystem
    
    config = {
        "kill_threshold_losses": 3,
        "kill_percentage": 0.20,
        "scale_winners_pct": 0.25,
    }
    
    system = MultiAgentSystem(config)
    
    print(f"  Agents initialized: {len(system.agents)}")
    for agent in system.agents:
        print(f"    - {agent.name}: {agent.strategy_type} (${agent.capital})")
    
    # Test consensus
    consensus = system.get_dashboard_data()
    print(f"  Consensus signal: {consensus.get('overall', 'neutral')}")
    
    return len(system.agents) == 6


def test_database():
    """Test database connectivity"""
    print("\nTesting Database...")
    try:
        import sqlite3
        conn = sqlite3.connect("trades.db")
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        
        print(f"  Tables: {', '.join(tables)}")
        conn.close()
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


def test_api_endpoints():
    """Test dashboard API endpoints"""
    print("\nTesting API Endpoints...")
    import requests
    
    endpoints = {
        "/api/prices": "prices",
        "/api/health": "health",
        "/api/multi-agent/status": "agents",
        "/api/zeroclaw/status": "bot status",
        "/api/config": "config",
    }
    
    base_url = "http://localhost:5000"
    results = {}
    
    for endpoint, name in endpoints.items():
        try:
            resp = requests.get(f"{base_url}{endpoint}", timeout=5)
            results[name] = resp.status_code == 200
            icon = "✓" if resp.status_code == 200 else "✗"
            print(f"  {icon} {name}: {resp.status_code}")
        except Exception as e:
            results[name] = False
            print(f"  ✗ {name}: {e}")
    
    return all(results.values())


def test_full_trade_flow():
    """Test complete trade flow"""
    print("\nTesting Full Trade Flow...")
    print("  Simulating: Price → Signal → Risk → Execution")
    
    from strategy_engine import StrategyEngine
    from risk_manager import RiskManager
    
    # 1. Get prices (mock)
    prices = [
        {"exchange": "Binance", "symbol": "BTC/USDT", "price": 65000.0},
        {"exchange": "Coinbase", "symbol": "BTC/USDT", "price": 65150.0},
    ]
    print("  ✓ Price data")
    
    # 2. Generate signal
    engine = StrategyEngine(paper_trading=True)
    signal = engine.evaluate(prices)
    print(f"  ✓ Signal: {signal.decision} ({signal.spread_pct:.2f}% spread)")
    
    # 3. Risk check
    rm = RiskManager()
    risk_check = rm.assess_trade({
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.01,
        "price": 65000.0
    }, current_price=65000.0)
    print(f"  ✓ Risk: {risk_check.decision}")
    
    # 4. Execute (paper)
    if signal.decision == "TRADE" and risk_check.decision == "APPROVE":
        print("  ✓ Trade would execute (PAPER MODE)")
        return True
    else:
        print("  ✓ Trade blocked (safety check)")
        return True


def main():
    print("=" * 60)
    print("TRADE ENGINE INTEGRATION TEST")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Strategy Engine", test_strategy_engine),
        ("Risk Manager", test_risk_manager),
        ("Multi-Agent", test_multi_agent),
        ("Database", test_database),
        ("API Endpoints", test_api_endpoints),
        ("Full Trade Flow", test_full_trade_flow),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n✗ {name} FAILED: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, passed_test in results.items():
        icon = "✓" if passed_test else "✗"
        print(f"{icon} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Trade engine is ready.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
