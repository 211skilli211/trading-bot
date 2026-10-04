"""Tests for telegram_responder — command routing, chat allowlist,
first-run skip-older, long-message chunking, offset persistence.

All network is mocked (monkeypatched requests + _api_call); no real
Telegram calls in the suite.
"""
import json

import pytest

import telegram_responder as tr


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """Deterministic env + state path for every test."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token:xyz")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setattr(tr, "_STATE_PATH",
                        str(tmp_path / "updates.json"))
    yield


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------

def test_routing_help(monkeypatch):
    monkeypatch.setattr(tr, "cmd_status", lambda: "STATUS")
    for cmd in ("/start", "/help", "help", "?", "commands"):
        out = tr.handle_text(cmd)
        assert "trading-bot commands" in out
    # status routed to the handler
    assert tr.handle_text("status") == "STATUS"


@pytest.mark.parametrize("cmd,needle", [
    ("balance", "Polymarket"),
    ("paper", "Paper lab"),
    ("test", "pong"),
    ("yo", "pong"),
    ("/status", "Bot status"),
    ("🤖 Bot Status", "Bot status"),
    ("📊 AI Signals", "scan"),
    ("signals", "scan"),
])
def test_routing_commands(monkeypatch, cmd, needle):
    # isolate heavy status sources; routing is what's under test
    monkeypatch.setattr(tr, "cmd_status", lambda: "📊 Bot status\n   paper: x")
    monkeypatch.setattr(tr, "_pm_lines", lambda compact=True: "   Polymarket: $1")
    monkeypatch.setattr(tr, "cmd_paper", lambda: "📈 Paper lab\n   paper: x")
    monkeypatch.setattr(tr, "cmd_scan", lambda: "no cached scan yet")
    out = tr.handle_text(cmd)
    assert needle.lower() in out.lower()


def test_routing_unknown():
    out = tr.handle_text("what does this bot do")
    assert "I didn't get that" in out
    assert "/status" in out


def test_status_renders_without_network(monkeypatch):
    """cmd_status must never raise, even when subsystems are unavailable."""
    for fn in ("_paper_lines", "_pm_lines", "_ctrader_lines",
               "_last_scan_lines"):
        monkeypatch.setattr(tr, fn, lambda *a, **k: "   stub: ok")
    out = tr.cmd_status()
    assert out.count("stub: ok") == 4
    assert "Bot status" in out


# ---------------------------------------------------------------------------
# respond_once
# ---------------------------------------------------------------------------

def _updates(ids_texts_chats):
    return [{"update_id": i, "message": {"text": t,
                                         "chat": {"id": c}}}
            for i, t, c in ids_texts_chats]


def test_respond_once_answers_only_our_chat(monkeypatch):
    ups = _updates([
        (100, "status", "12345"),      # our chat -> answered
        (101, "status", "99999"),      # stranger -> ignored
        (102, "test", "12345"),        # our chat -> answered
    ])
    tr.save_offset(99)  # not first run: answer everything in the batch
    monkeypatch.setattr(tr, "fetch_updates", lambda *a, **k: (ups, None))
    sent = []
    monkeypatch.setattr(tr, "send_text",
                        lambda text, chat_id=None: sent.append(text) or "")
    n, err = tr.respond_once()
    assert err is None
    assert n == 2
    assert len(sent) == 2
    assert "Bot status" in sent[0]
    assert "pong" in sent[1]
    # offset saved past both answered updates
    assert tr.load_offset() == 102


def test_respond_once_first_run_skips_older(monkeypatch):
    """No saved offset: only the newest queued message gets a reply."""
    ups = _updates([
        (1, "old 1", "12345"),
        (2, "old 2", "12345"),
        (3, "test", "12345"),
    ])
    def fake_fetch(since=0, long_poll=0, **k):
        return (ups, None) if since == 0 else ([], None)
    monkeypatch.setattr(tr, "fetch_updates", fake_fetch)
    sent = []
    monkeypatch.setattr(tr, "send_text",
                        lambda text, chat_id=None: sent.append(text) or "")
    n, err = tr.respond_once()
    assert err is None
    assert n == 1
    assert "pong" in sent[0]
    assert tr.load_offset() == 3
    # next pass: nothing new
    assert tr.respond_once() == (0, None)


def test_respond_once_api_error(monkeypatch):
    monkeypatch.setattr(tr, "fetch_updates",
                        lambda *a, **k: ([], "HTTP 401: Unauthorized"))
    n, err = tr.respond_once()
    assert n == 0
    assert "401" in err


def test_respond_once_send_failure_stops_batch(monkeypatch):
    ups = _updates([(1, "test", "12345"), (2, "test", "12345")])
    monkeypatch.setattr(tr, "fetch_updates", lambda *a, **k: (ups, None))
    monkeypatch.setattr(tr, "send_text", lambda *a, **k: "send failed HTTP 400")
    n, err = tr.respond_once()
    assert n == 0
    assert "400" in err
    # offset not advanced — the message gets retried next pass
    assert tr.load_offset() == 0


# ---------------------------------------------------------------------------
# send_text chunking
# ---------------------------------------------------------------------------

def test_send_text_chunks_long_message(monkeypatch):
    posts = []

    def fake_post(url, json=None, timeout=None):
        posts.append(json["text"])

        class R:
            status_code = 200

            def json(self):
                return {"ok": True}
        return R()

    monkeypatch.setattr(tr.requests, "post", fake_post)
    long_text = "x" * 8000
    assert tr.send_text(long_text) == ""
    assert len(posts) == 3
    assert "".join(posts) == long_text
    assert all(len(p) <= tr.CHUNK for p in posts)


def test_send_text_unconfigured(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    assert tr.send_text("hi") == "telegram not configured"


def test_offset_roundtrip(monkeypatch, tmp_path):
    p = tmp_path / "u.json"
    monkeypatch.setattr(tr, "_STATE_PATH", str(p))
    assert tr.load_offset() == 0
    tr.save_offset(42)
    assert tr.load_offset() == 42
    assert json.loads(p.read_text())["last_update_id"] == 42
