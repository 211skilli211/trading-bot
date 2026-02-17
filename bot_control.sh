#!/bin/bash
# 211Skilli Bot Control Script

case "$1" in
    start)
        echo "🚀 Starting bot..."
        ~/start-bot.sh
        ;;
    stop)
        echo "🛑 Stopping bot..."
        ~/stop-bot.sh
        ;;
    restart)
        echo "🔄 Restarting bot..."
        ~/stop-bot.sh
        sleep 2
        ~/start-bot.sh
        ;;
    status)
        echo "📊 Bot Status:"
        proot-distro login ubuntu -- bash -c "cd ~/trading-bot && source ~/botenv/bin/activate && python bot_status.py"
        ;;
    logs)
        echo "📜 Viewing logs (Ctrl+C to exit)..."
        ~/view-logs.sh
        ;;
    analytics)
        echo "📊 Running analytics..."
        proot-distro login ubuntu -- bash -c "cd ~/trading-bot && source ~/botenv/bin/activate && python -c 'from performance_analytics import get_analytics; print(get_analytics().generate_report(7))'"
        ;;
    dashboard)
        echo "🌐 Starting enhanced dashboard on port 8081..."
        proot-distro login ubuntu -- bash -c "cd ~/trading-bot && source ~/botenv/bin/activate && python dashboard_v2.py" &
        echo "Dashboard available at: http://127.0.0.1:8081"
        ;;
    telegram)
        echo "📱 Setting up Telegram alerts..."
        proot-distro login ubuntu -- bash -c "cd ~/trading-bot && source ~/botenv/bin/activate && python setup_telegram.py"
        ;;
    *)
        echo "211Skilli Bot Control"
        echo ""
        echo "Usage: ./bot_control.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start      - Start the trading bot"
        echo "  stop       - Stop the trading bot"
        echo "  restart    - Restart the trading bot"
        echo "  status     - Show bot status and analytics"
        echo "  logs       - View live logs"
        echo "  analytics  - Show performance report"
        echo "  dashboard  - Start enhanced dashboard"
        echo "  telegram   - Setup Telegram alerts"
        ;;
esac
