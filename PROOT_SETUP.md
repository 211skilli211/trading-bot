# 🚀 Proot-Distro Ubuntu Setup for Full Auto Solana Trading

This runs a complete Ubuntu Linux inside Termux (no root required).
Inside Ubuntu, `solders` / `solathon` / `pynacl` install perfectly.

## Quick Setup (8-12 minutes)

### Step 1: Install proot-distro (in main Termux)
```bash
pkg update && pkg upgrade -y
pkg install proot-distro -y
proot-distro install ubuntu
```

### Step 2: Enter Ubuntu
```bash
proot-distro login ubuntu
```

You'll see `root@localhost` prompt — you're now in full Ubuntu.

### Step 3: One-time setup inside Ubuntu
```bash
apt update && apt upgrade -y
apt install python3 python3-pip python3-venv rustc cargo build-essential libssl-dev pkg-config git curl -y

python3 -m venv ~/botenv
source ~/botenv/bin/activate
pip install --upgrade pip wheel setuptools
pip install solders solathon requests ccxt python-dotenv pandas aiosqlite websockets flask pytest
```

### Step 4: Copy your bot
From another Termux session (new tab):
```bash
cp -r /data/data/com.termux/files/home/trading-bot /data/data/com.termux/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu/root/
```

Or inside Ubuntu:
```bash
mkdir -p /root/trading-bot
cd /root/trading-bot
# Clone or copy files here
```

### Step 5: Test
```bash
cd /root/trading-bot
source ~/botenv/bin/activate
python -c "import solders; from solathon import Keypair; print('✅ solders + solathon working!')"
```

## Usage

### Enter Ubuntu and run bot:
```bash
proot-distro login ubuntu
source ~/botenv/bin/activate
cd /root/trading-bot
python trading_bot.py --mode live --monitor 60
```

### Exit Ubuntu:
```bash
exit
# or Ctrl+D
```

## 24/7 Auto-Start

Create `~/.termux/boot/trading-bot`:
```bash
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
proot-distro login ubuntu -- /root/botenv/bin/python /root/trading-bot/trading_bot.py --mode live --monitor 60 > /root/bot.log 2>&1 &
```

Enable:
```bash
chmod +x ~/.termux/boot/trading-bot
mkdir -p ~/.termux/boot
```

## File Locations

| Location | Path |
|----------|------|
| Ubuntu root | `/data/data/com.termux/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu/` |
| Your bot | `/root/trading-bot/` (inside Ubuntu) |
| Python env | `/root/botenv/` (inside Ubuntu) |
| Logs | `/root/bot.log` (inside Ubuntu) |

## Troubleshooting

### "proot-distro: command not found"
```bash
pkg install proot-distro
```

### "No space left on device"
```bash
# Clean Termux
pkg clean
apt autoremove
```

### Slow performance
```bash
# Use proot fix
echo "PROOT_NO_SECCOMP=1" >> ~/.bashrc
```

## Benefits

✅ Full `solders` support (Rust builds work)
✅ Full `solathon` support (transaction signing)
✅ Full `pynacl` support (cryptography)
✅ 24/7 operation with wake-lock
✅ All Python packages install normally
✅ No desktop/VPS needed

## Next Steps

1. Complete setup above
2. Test wallet generation
3. Fund with 20 USDT + 0.1 SOL
4. Run paper mode first
5. Go live!
