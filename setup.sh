#!/bin/bash
# Trading Bot Setup Script
# Run this to set up the bot on a fresh system

set -e

echo "=============================================="
echo "🤖 Trading Bot Setup"
echo "=============================================="

# Check Python version
echo "[1] Checking Python..."
python3 --version || { echo "Python 3 not found!"; exit 1; }

# Install dependencies
echo "[2] Installing dependencies..."
pip3 install --user -r requirements.txt

# Create .env from example if not exists
echo "[3] Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "   Created .env file - EDIT THIS FILE with your API keys!"
fi

# Create necessary directories
echo "[4] Creating directories..."
mkdir -p logs
mkdir -p data

# Run tests
echo "[5] Running tests..."
python3 -m pytest tests/ -v || echo "Some tests failed - check output"

# First run (paper mode)
echo ""
echo "[6] Testing bot (paper mode)..."
python3 trading_bot.py --mode paper --config config.json

echo ""
echo "=============================================="
echo "✅ Setup Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run paper trading: python3 trading_bot.py --monitor 60"
echo "3. Start dashboard: python3 trading_bot.py --dashboard"
echo "4. For 24/7 operation: sudo cp trading-bot.service /etc/systemd/system/"
echo ""
echo "Happy trading! 🚀"
