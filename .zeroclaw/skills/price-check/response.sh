#!/bin/bash
# Price Check Response Script
# Returns plain text for Telegram

cd /root/trading-bot/.zeroclaw
python3 skills/price-check/handler.py "$1" 2>&1
