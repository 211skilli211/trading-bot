#!/bin/bash
cd /sdcard/zeroclaw-workspace/trading-bot
/root/trading-bot-venv/bin/python dashboard.py 7777 > dashboard.log 2>&1 &
echo "Dashboard started on port 7777"
