#!/bin/bash
# System Diagnostic Response Script

cd /root/trading-bot/.zeroclaw
python3 skills/system-diagnostic/handler.py 2>&1
