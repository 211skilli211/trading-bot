#!/data/data/com.termux/files/usr/bin/bash
echo ""
echo "🚀 Starting Mobile HackLab Desktop..."
echo ""
# Load GPU config
source ~/.config/hacklab-gpu.sh 2>/dev/null
# Kill any existing sessions
echo "🔄 Cleaning up old sessions..."
pkill -9 -f "termux.x11" 2>/dev/null
pkill -9 -f "xfce" 2>/dev/null
pkill -9 -f "dbus" 2>/dev/null
# === AUDIO SETUP ===
unset PULSE_SERVER
pulseaudio --kill 2>/dev/null
sleep 0.5
echo "🔊 Starting audio server..."
pulseaudio --start --exit-idle-time=-1
sleep 1
pactl load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1 2>/dev/null
export PULSE_SERVER=127.0.0.1
# === END AUDIO ===
# Start Termux-X11 server
echo "📺 Starting X11 display server..."
termux-x11 :0 -ac &
sleep 3
# Set display
export DISPLAY=:0
# Start XFCE Desktop
echo "🖥️ Launching XFCE4 Desktop..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📱 Open the Termux-X11 app to see desktop!"
echo "  🔊 Audio is enabled!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
exec startxfce4
