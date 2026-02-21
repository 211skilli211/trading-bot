#!/bin/bash
# Performance Monitor Response Script

cd /root/trading-bot/.zeroclaw
python3 skills/performance-monitor/handler.py 2>&1
