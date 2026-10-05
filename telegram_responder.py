"""Interactive Telegram responder for the trading bot.

alerts.py covers one-way pushes (fills, settlements, halts). This module
adds the missing direction: it polls getUpdates and replies to commands
from the configured chat (TELEGRAM_CHAT_ID).

Commands (case-insensitive, any of these words):
    /start /help help ?        -> command list
    status | "bot status"      -> all-systems status
    balance                    -> Polymarket pUSD cash + orders + ledger
    paper                      -> paper-lab slots
    scan | signals             -> top quick-wins from the last cached scan
    test | ping                -> liveness check

Security: only messages whose chat id equals TELEGRAM_CHAT_ID are answered.
First run (no saved offset): older queued messages are skipped and only the
most recent one is answered — avoids a spam burst of back-dated replies.

Telegram message limit is 4096 chars; replies longer than that are split.
"""

import json
import os
import time

import requests

TG = "https://api.telegram.org/bot{}"
MSG_LIMIT = 4096
CHUNK = 3900

_STATE_PATH = os.path.join("data", "telegram_updates.json")


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


def _chat_id() -> str:
    return os.getenv("TELEGRAM_CHAT_ID", "").strip()


def configured() -> bool:
    tok, chat = _token(), _chat_id()
    bad = ("", "YOUR_BOT_TOKEN", "your_bot_token",
           "YOUR_CHAT_ID", "your_chat_id")
    return bool(tok) and bool(chat) and tok not in bad and chat not in bad


# ---------------------------------------------------------------------------
# update-id state (so we never answer the same message twice)
# ---------------------------------------------------------------------------

def load_offset() -> int:
    try:
        with open(_STATE_PATH) as f:
            return int(json.load(f).get("last_update_id", 0))
    except (OSError, ValueError, TypeError):
        return 0


def save_offset(update_id: int) -> None:
    os.makedirs("data", exist_ok=True)
    tmp = _STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"last_update_id": int(update_id),
                   "updated_ts": int(time.time())}, f)
    os.replace(tmp, _STATE_PATH)


# ---------------------------------------------------------------------------
# Telegram API
# ---------------------------------------------------------------------------

def _api_call(method: str, params: dict = None,
              timeout: int = 45):
    """GET {method}. Returns (ok, data_or_error_string). Never raises."""
    tok = _token()
    if not tok:
        return False, "TELEGRAM_BOT_TOKEN not set"
    url = TG.format(tok) + "/" + method
    try:
        r = requests.get(url, params=params or {}, timeout=timeout)
        if r.status_code != 200:
            return False, "HTTP {}".format(r.status_code)
        d = r.json()
        return (True, d.get("result")) if d.get("ok") else \
            (False, d.get("description", "api error"))
    except requests.RequestException as e:
        return False, str(e)[:160]
    except ValueError:
        return False, "non-JSON response"


def send_text(text: str, chat_id: str = None) -> str:
    """Send a (possibly long) message. Returns '' on success, error otherwise.
    Splits text into chunks <= 3900 chars to stay under the 4096 limit."""
    chat_id = chat_id or _chat_id()
    tok = _token()
    if not tok or not chat_id:
        return "telegram not configured"
    url = TG.format(tok) + "/sendMessage"
    for i in range(0, len(text), CHUNK):
        chunk = text[i:i + CHUNK]
        try:
            r = requests.post(url, json={
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            }, timeout=20)
            if r.status_code == 200 and r.json().get("ok"):
                continue
            if r.status_code == 429:
                retry = r.headers.get("Retry-After")
                try:
                    time.sleep(min(int(retry), 30))
                except (ValueError, TypeError):
                    time.sleep(5)
                r = requests.post(url, json={
                    "chat_id": chat_id, "text": chunk,
                    "disable_web_page_preview": True}, timeout=20)
                if r.status_code == 200 and r.json().get("ok"):
                    continue
            return "send failed HTTP {}: {}".format(
                r.status_code, (r.text or "")[:160])
        except requests.RequestException as e:
            return "send failed: " + str(e)[:160]
    return ""


# ---------------------------------------------------------------------------
# Command handlers (pure text in -> text out; errors are rendered, not raised)
# ---------------------------------------------------------------------------

HELP = (
    "🤖 trading-bot commands\n"
    "• /status — all systems (paper · Polymarket · cTrader)\n"
    "• /balance — Polymarket USDC, orders, ledger P&L\n"
    "• /paper — paper-lab slots\n"
    "• /scan — top quick-wins from the last scan\n"
    "• /test — ping me\n"
    "You'll also get automatic pings: PM fills, settlements (with P&L), "
    "and daily-loss halts.")


def _paper_lines() -> str:
    try:
        import paper_lab
        state = paper_lab.load_state()
    except Exception as e:
        return "   paper: unavailable ({})".format(str(e)[:60])
    if not state or not state.get("slots"):
        return "   paper: no state yet (run --paper-run)"
    parts = []
    for name, slot in state["slots"].items():
        eq = float(slot.get("equity", 0) or 0)
        init = float(slot.get("initial_capital", 0) or 0)
        pnl = eq - init
        pos = slot.get("position")
        label = "in position" if pos else "flat"
        parts.append("{} ${:,.0f} ({:+.0f}, {})".format(name, eq, pnl, label))
    return "   paper: " + " · ".join(parts)


def _pm_lines(compact: bool = True) -> str:
    """Polymarket status. compact=True -> one line for /status;
    compact=False -> the full balance_report."""
    try:
        import polymarket_executor as pme
        trader = pme.PmTrader()
        if compact:
            cash = trader.usdc_balance()
            s = pme.ledger_summary(pme.load_ledger())
            return ("   Polymarket: USDC ${:.2f} · {} open "
                    "(${:.2f}) · {} settled {}W/{}L, realized ${:+.2f}"
                    .format(cash, s["open_count"], s["open_cost"],
                            s["settled_count"], s["wins"], s["losses"],
                            s["realized_total"]))
        return pme.balance_report(trader).replace("💰 Polymarket", "   Polymarket")
    except Exception as e:
        return "   Polymarket: ❌ " + str(e)[:120]


def _ctrader_lines() -> str:
    try:
        with open(os.path.join("data", "ctrader_credentials.json")) as f:
            c = json.load(f)
    except OSError:
        return "   cTrader: not connected (no credentials)"
    live = c.get("account_id")
    demo = c.get("account_id_demo")
    parked = "🔒 PARKED" if c.get("live_parked") else "armed"
    exp = c.get("access_token_expires_at") or 0
    days = (int(exp) - int(time.time())) / 86400
    token = "token {}d left".format(max(0, int(days))) \
        if days >= 0 else "token EXPIRED — re-auth"
    out = "   cTrader: live {} [{}], demo {}, {}".format(
        live, parked, demo or "none", token)
    return out


def _last_scan_lines() -> str:
    try:
        with open(os.path.join("data", "polymarket_last_scan.json")) as f:
            d = json.load(f)
    except OSError:
        return "   last scan: none yet (run --polymarket-scan)"
    age_h = (int(time.time()) - int(d.get("ts", 0))) / 3600
    return ("   last scan: {}h ago, {} opportunities"
            .format(round(age_h, 1), d.get("count", 0)))


def cmd_status() -> str:
    return ("📊 Bot status\n"
            + _paper_lines() + "\n"
            + _pm_lines(compact=True) + "\n"
            + _ctrader_lines() + "\n"
            + _last_scan_lines())


def cmd_balance() -> str:
    return _pm_lines(compact=False)


def cmd_paper() -> str:
    return "📈 Paper lab\n" + _paper_lines()


def cmd_scan() -> str:
    try:
        with open(os.path.join("data", "polymarket_last_scan.json")) as f:
            d = json.load(f)
    except OSError:
        return ("No cached scan yet — I can't run one from Telegram "
                "(it takes ~40s). Run on the phone:\n"
                "  python3 trading_bot.py --polymarket-quickwins")
    opps = sorted(d.get("opportunities", []),
                  key=lambda o: o.get("score", 0), reverse=True)[:3]
    if not opps:
        return "Last scan: 0 opportunities ({} markets).".format(
            d.get("count", 0))
    lines = ["📡 Last scan ({}h ago) — top {}".format(
        round((int(time.time()) - int(d.get("ts", 0))) / 3600, 1), len(opps))]
    for o in opps:
        lines.append(
            "{} · {} — buy {} @ {:.3f} · {:.1f}h to end\n"
            "   {} shares (${:.2f}) → expected ${:+.2f}".format(
                o.get("id", "?"),
                str(o.get("question", "?"))[:52],
                o.get("outcome", "?"),
                float(o.get("price", 0) or 0),
                float(o.get("time_to_end_h", 0) or 0),
                o.get("shares", 0),
                float(o.get("stake_usd", 0) or 0),
                float(o.get("expected_profit_usd", 0) or 0)))
    lines.append("\nFull list: python3 trading_bot.py --polymarket-quickwins")
    return "\n".join(lines)


def handle_text(text: str) -> str:
    """Route an incoming message to its reply. Never raises."""
    t = (text or "").strip().lower()
    if t in ("/start", "/help", "help", "?", "commands"):
        return HELP
    if t in ("status", "bot status", "🤖 bot status", "/status",
             "🤖bot status"):
        return cmd_status()
    if t in ("balance", "/balance", "pm", "/pm", "usdc"):
        return cmd_balance()
    if t in ("paper", "/paper", "paper status"):
        return cmd_paper()
    if t in ("scan", "signals", "/scan", "📊 ai signals", "ai signals",
             "quick wins", "quickwins", "opps"):
        return cmd_scan()
    if t in ("test", "ping", "/test", "hello", "hi", "yo"):
        return "🏓 pong — bot is alive. Try /help"
    return ("I didn't get that. Commands:\n"
            "• /status  • /balance  • /paper  • /scan  • /test")


# ---------------------------------------------------------------------------
# update polling
# ---------------------------------------------------------------------------

def fetch_updates(since: int, long_poll_s: int = 0, limit: int = 50):
    """GET getUpdates. Returns (list_of_updates, error_or_None)."""
    ok, res = _api_call("getUpdates", {
        "offset": since + 1,
        "timeout": long_poll_s,
        "limit": limit,
    }, timeout=max(45, long_poll_s + 20))
    if not ok:
        return [], res
    return (res or []), None


def respond_once(long_poll_s: int = 0):
    """Poll for new messages and answer each from our chat.

    First run (no saved offset): only the most recent queued message is
    answered; older ones are skipped (offset jumps over them).

    Returns (replies, error_or_None).
    """
    if not configured():
        return 0, "telegram not configured"
    first_run = load_offset() == 0
    updates, err = fetch_updates(load_offset(), long_poll_s)
    if err:
        return 0, err
    if not updates:
        return 0, None
    if first_run:
        updates = updates[-1:]
    replies = 0
    for u in updates:
        m = u.get("message") or {}
        chat = m.get("chat") or {}
        if str(chat.get("id")) != str(_chat_id()):
            continue  # only answer our configured chat
        reply = handle_text(m.get("text") or "")
        err2 = send_text(reply)
        if err2:
            return replies, err2
        replies += 1
        save_offset(u["update_id"])
    if replies:
        save_offset(updates[-1]["update_id"])
    return replies, None


def cmd_listen(long_poll_s: int = 30, interval_s: int = 2):
    """Resident loop: long-poll getUpdates and answer commands.
    Returns the number of cycles processed."""
    if not configured():
        print("❌ Telegram not configured. Set TELEGRAM_BOT_TOKEN and "
              "TELEGRAM_CHAT_ID in .env")
        return 0
    print("👂 telegram listener active — send /help to the bot "
          "(@{}) to stop: Ctrl+C".format(
              _token()[:10] + "..."), flush=True)
    cycles = 0
    try:
        while True:
            n, err = respond_once(long_poll_s=long_poll_s)
            if err and "timeout" not in err.lower():
                print("⚠️ telegram: {}".format(err), flush=True)
            cycles += 1
            if n:
                print("   {} reply(ies) sent (cycle {})".format(
                    n, cycles), flush=True)
            if n == 0:
                time.sleep(interval_s)
    except KeyboardInterrupt:
        print("\n👋 telegram listener stopped after {} cycle(s)".format(
            cycles), flush=True)
    return cycles


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        print("configured:", configured())
        ups, err = fetch_updates(load_offset())
        print("pending:", len(ups), "err:", err)
        r, err2 = respond_once()
        print("replied:", r, "err:", err2)
    else:
        cmd_listen()
