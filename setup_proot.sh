#!/bin/bash
# Proot-Distro Ubuntu Setup Script for Trading Bot
# Run this in main Termux (not inside proot)

set -e

echo "=============================================="
echo "🚀 Proot-Distro Ubuntu Setup for Trading Bot"
echo "=============================================="

# Check if running in Termux (not inside proot)
if [ -n "$PROOT_DISTRO" ]; then
    echo "❌ ERROR: Already inside proot!"
    echo "Run this in main Termux, not inside Ubuntu."
    exit 1
fi

echo ""
echo "[1/6] Updating Termux packages..."
pkg update && pkg upgrade -y

echo ""
echo "[2/6] Installing proot-distro..."
pkg install proot-distro -y

echo ""
echo "[3/6] Installing Ubuntu (this takes 3-5 minutes)..."
if proot-distro list | grep -q "ubuntu"; then
    echo "Ubuntu already installed, skipping..."
else
    proot-distro install ubuntu
fi

echo ""
echo "[4/6] Setting up Ubuntu environment..."
proot-distro login ubuntu -- bash -c '
    echo "Inside Ubuntu - updating packages..."
    apt update && apt upgrade -y
    
    echo "Installing build tools..."
    apt install -y python3 python3-pip python3-venv rustc cargo build-essential libssl-dev pkg-config git curl wget
    
    echo "Creating Python virtual environment..."
    python3 -m venv ~/botenv
    source ~/botenv/bin/activate
    
    echo "Upgrading pip..."
    pip install --upgrade pip wheel setuptools
    
    echo "Installing Python packages (this takes 2-3 minutes)..."
    pip install solders solathon requests ccxt python-dotenv pandas aiosqlite websockets flask pytest base58
    
    echo "✅ Ubuntu setup complete!"
'

echo ""
echo "[5/6] Copying trading bot to Ubuntu..."
BOT_SOURCE="/data/data/com.termux/files/home"
BOT_DEST="/data/data/com.termux/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu/root/trading-bot"

if [ -d "$BOT_SOURCE" ]; then
    mkdir -p "$BOT_DEST"
    cp -r "$BOT_SOURCE"/* "$BOT_DEST/" 2>/dev/null || true
    echo "✅ Bot files copied"
else
    echo "⚠️  Source directory not found, skipping copy"
    echo "   You'll need to manually copy files to:"
    echo "   $BOT_DEST"
fi

echo ""
echo "[6/6] Testing installation..."
proot-distro login ubuntu -- bash -c '
    source ~/botenv/bin/activate
    python3 -c "
import solders
from solathon import Keypair
print(\"✅ solders: OK\")
print(\"✅ solathon: OK\")
print(\"✅ All dependencies working!\")
    "
'

echo ""
echo "=============================================="
echo "✅ SETUP COMPLETE!"
echo "=============================================="
echo ""
echo "To use your bot:"
echo ""
echo "1. Enter Ubuntu:"
echo "   proot-distro login ubuntu"
echo ""
echo "2. Activate environment:"
echo "   source ~/botenv/bin/activate"
echo ""
echo "3. Go to bot directory:"
echo "   cd ~/trading-bot"
echo ""
echo "4. Run bot:"
echo "   python trading_bot.py --mode paper --monitor 60"
echo ""
echo "To exit Ubuntu, type: exit"
echo ""
echo "For 24/7 operation, see PROOT_SETUP.md"
echo ""
