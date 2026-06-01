#!/bin/bash
# Quick test script for all trading bot modules.
# Run from trading-bot root if Python dependencies are available.

set -e

echo "═══════════════════════════════════════════"
echo "  TRADING BOT — MODULE TEST SUITE"
echo "═══════════════════════════════════════════"

FAILED=0

test_module() {
    local name="$1"
    local file="$2"
    echo ""
    echo "--- Testing: $name ---"
    python3 -c "import ast; ast.parse(open('$file').read()); print('  ✅ Syntax OK')" 2>&1 || {
        echo "  ❌ Syntax FAILED"
        FAILED=1
    }
}

# Core modules
test_module "strategy_interface" "strategy_interface.py"
test_module "strategies" "strategies.py"
test_module "hyperopt_engine" "hyperopt_engine.py"
test_module "trade_database" "trade_database.py"
test_module "metrics" "metrics.py"

# New modules
test_module "remote_control_api" "remote_control_api.py"
test_module "social_sentiment" "social_sentiment.py"
test_module "multi_strategy_orchestrator" "multi_strategy_orchestrator.py"
test_module "discord_notifier" "discord_notifier.py"
test_module "event_logger" "event_logger.py"

# Existing modules
test_module "risk_manager" "risk_manager.py"
test_module "execution_layer" "execution_layer.py"
test_module "security" "security.py"

echo ""
echo "═══════════════════════════════════════════"
if [ $FAILED -eq 0 ]; then
    echo "  ALL MODULES PASS ✅"
else
    echo "  SOME MODULES FAILED ❌"
    exit 1
fi
echo "═══════════════════════════════════════════"
