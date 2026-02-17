#!/bin/bash
# Quick script to apply mobile-optimized dashboard

echo "🚀 Applying Mobile Dashboard Fix v2..."

# Copy files to Ubuntu
cp /data/data/com.termux/files/home/PRO_DASHBOARD_V2.md /data/data/com.termux/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu/root/trading-bot/

# Instructions
echo ""
echo "✅ Fix files ready!"
echo ""
echo "To apply in Ubuntu, run:"
echo "  cd ~/trading-bot"
echo "  mkdir -p templates static/css static/js"
echo "  cat PRO_DASHBOARD_V2.md | grep -A 1000 'Step 1' | head -150 > templates/base.html"
echo ""
echo "OR manually copy the code blocks from PRO_DASHBOARD_V2.md"
echo ""
