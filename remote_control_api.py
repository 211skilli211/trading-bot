#!/usr/bin/env python3
"""
Remote Control REST API (Freqtrade-style)
==========================================
HTTP API for remote bot management:
- Start/stop/restart trading bot
- View bot status & performance
- Modify configuration
- View trade history
- Trigger manual trades

Security: JWT token auth, rate limiting, IP whitelist
Runs alongside trading_bot.py - communicate via shared state files.

Usage:
    python remote_control_api.py --port 8080 --token YOUR_SECRET_JWT_TOKEN
"""

import os
import sys
import json
import time
import hashlib
import secrets
import threading
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, Tuple

# Optional JWT
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# ── Bot State Manager (shared via JSON file) ──────────────────────

class BotStateManager:
    """Manages bot state via shared JSON file for cross-process communication."""

    def __init__(self, state_file: str = "bot_state.json"):
        self.state_file = state_file
        self.lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.state_file):
            self._write({
                "status": "stopped",
                "mode": "paper",
                "started_at": None,
                "last_tick": None,
                "config": {},
                "stats": {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "total_pnl": 0.0,
                    "uptime_seconds": 0,
                }
            })

    def _read(self) -> Dict:
        try:
            with open(self.state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write(self, state: Dict):
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def get_state(self) -> Dict:
        with self.lock:
            return self._read()

    def update(self, updates: Dict) -> Dict:
        with self.lock:
            state = self._read()
            state.update(updates)
            self._write(state)
            return state

    def set_status(self, status: str, **kwargs):
        updates = {"status": status, **kwargs}
        self.update(updates)


# ── JWT Auth ──────────────────────────────────────────────────────

class JWTAuth:
    def __init__(self, secret: str, algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm

    def generate_token(self, payload: Dict, expires_hours: int = 24) -> str:
        if not JWT_AVAILABLE:
            # Fallback: simple HMAC-based token
            return self._fallback_token(payload, expires_hours)
        payload = {**payload, "exp": datetime.now(timezone.utc) + timedelta(hours=expires_hours)}
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def validate_token(self, token: str) -> Optional[Dict]:
        if not JWT_AVAILABLE:
            return self._fallback_validate(token)
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    def _fallback_token(self, payload: Dict, expires_hours: int) -> str:
        payload_str = json.dumps(payload, sort_keys=True)
        expiry = int(time.time()) + (expires_hours * 3600)
        sig = hashlib.sha256(f"{payload_str}{expiry}{self.secret}".encode()).hexdigest()[:16]
        import base64
        return base64.urlsafe_b64encode(
            json.dumps({"p": payload, "e": expiry, "s": sig}).encode()
        ).decode()

    def _fallback_validate(self, token: str) -> Optional[Dict]:
        import base64
        try:
            data = json.loads(base64.urlsafe_b64decode(token.encode()))
            if data["e"] < time.time():
                return None
            payload_str = json.dumps(data["p"], sort_keys=True)
            expected_sig = hashlib.sha256(f"{payload_str}{data['e']}{self.secret}".encode()).hexdigest()[:16]
            if data["s"] != expected_sig:
                return None
            return data["p"]
        except (KeyError, json.JSONDecodeError):
            return None


# ── Rate Limiter ──────────────────────────────────────────────────

class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: Dict[str, list] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        with self._lock:
            if client_id not in self._requests:
                self._requests[client_id] = []
            # Prune old
            self._requests[client_id] = [
                t for t in self._requests[client_id] if now - t < self.window
            ]
            if len(self._requests[client_id]) >= self.max_requests:
                return False
            self._requests[client_id].append(now)
            return True


# ── REST API Handler ──────────────────────────────────────────────

class BotAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for bot remote control."""

    # Class-level (set by server)
    auth: JWTAuth = None
    rate_limiter: RateLimiter = None
    state_manager: BotStateManager = None
    ip_whitelist: list = None
    require_auth: bool = True

    def log_message(self, format, *args):
        """Silent logging to avoid spam."""
        pass

    def _client_id(self) -> str:
        return self.client_address[0]

    def _is_whitelisted(self) -> bool:
        if self.ip_whitelist is None:
            return True
        return self._client_id() in self.ip_whitelist

    def _check_rate(self) -> bool:
        if self.rate_limiter is None:
            return True
        return self.rate_limiter.is_allowed(self._client_id())

    def _get_auth_token(self) -> Optional[Dict]:
        if not self.require_auth:
            return {"role": "admin"}
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return self.auth.validate_token(auth_header[7:])
        return None

    def _send_json(self, data: Dict, status: int = 200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str, status: int = 400):
        self._send_json({"status": "error", "message": message}, status)

    def _read_body(self) -> Dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    # ─── CORS preflight ────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    # ─── GET routes ────────────────────────────────────────────

    def do_GET(self):
        if not self._is_whitelisted():
            return self._send_error("IP not whitelisted", 403)
        if not self._check_rate():
            return self._send_error("Rate limit exceeded", 429)
        token = self._get_auth_token()
        if token is None:
            return self._send_error("Unauthorized", 401)

        path = urlparse(self.path).path
        routes = {
            "/api/v1/status": self._handle_status,
            "/api/v1/config": self._handle_get_config,
            "/api/v1/trades": self._handle_trades,
            "/api/v1/strategies": self._handle_strategies,
            "/api/v1/performance": self._handle_performance,
            "/api/v1/logs": self._handle_logs,
        }
        handler = routes.get(path)
        if handler:
            return handler(token)
        # Default fallback for /api/v1/status
        if path == "/" or path == "":
            return self._handle_status(token)
        self._send_error("Not found", 404)

    # ─── POST routes ───────────────────────────────────────────

    def do_POST(self):
        if not self._is_whitelisted():
            return self._send_error("IP not whitelisted", 403)
        if not self._check_rate():
            return self._send_error("Rate limit exceeded", 429)
        token = self._get_auth_token()
        if token is None:
            return self._send_error("Unauthorized", 401)

        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/api/v1/start":
            return self._handle_start(token, body)
        if path == "/api/v1/stop":
            return self._handle_stop(token, body)
        if path == "/api/v1/restart":
            return self._handle_restart(token, body)
        if path == "/api/v1/trade":
            return self._handle_manual_trade(token, body)
        self._send_error("Not found", 404)

    # ─── PUT routes ────────────────────────────────────────────

    def do_PUT(self):
        if not self._is_whitelisted():
            return self._send_error("IP not whitelisted", 403)
        token = self._get_auth_token()
        if token is None:
            return self._send_error("Unauthorized", 401)

        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/api/v1/config":
            return self._handle_update_config(token, body)
        self._send_error("Not found", 404)

    # ─── Route Handlers ────────────────────────────────────────

    def _handle_status(self, token):
        state = self.state_manager.get_state()
        self._send_json({
            "status": "ok",
            "bot_status": state.get("status", "unknown"),
            "mode": state.get("mode", "paper"),
            "started_at": state.get("started_at"),
            "last_tick": state.get("last_tick"),
            "stats": state.get("stats", {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _handle_get_config(self, token):
        state = self.state_manager.get_state()
        config = state.get("config", {})
        # Mask secrets
        for key in list(config.keys()):
            if "key" in key.lower() or "secret" in key.lower() or "password" in key.lower():
                config[key] = "***MASKED***"
        self._send_json({"status": "ok", "config": config})

    def _handle_trades(self, token):
        try:
            from trade_database import TradeDatabase
            db = TradeDatabase()
            limit = int(parse_qs(urlparse(self.path).query).get("limit", ["50"])[0])
            offset = int(parse_qs(urlparse(self.path).query).get("offset", ["0"])[0])
            trades = db.get_trades(limit=limit, offset=offset)
            return self._send_json({"status": "ok", "trades": trades, "count": len(trades)})
        except ImportError:
            state = self.state_manager.get_state()
            return self._send_json({
                "status": "ok",
                "trades": [],
                "message": "TradeDatabase not available"
            })

    def _handle_strategies(self, token):
        try:
            from strategy_interface import StrategyRegistry
            strategies = StrategyRegistry.list()
            return self._send_json({"status": "ok", "strategies": strategies})
        except ImportError:
            return self._send_json({"status": "ok", "strategies": [], "message": "StrategyRegistry not available"})

    def _handle_performance(self, token):
        try:
            from trade_database import TradeDatabase
            db = TradeDatabase()
            analytics = db.get_analytics()
            return self._send_json({"status": "ok", "performance": analytics})
        except ImportError:
            state = self.state_manager.get_state()
            return self._send_json({
                "status": "ok",
                "performance": state.get("stats", {})
            })

    def _handle_logs(self, token):
        limit = int(parse_qs(urlparse(self.path).query).get("limit", ["100"])[0])
        log_file = "bot_state.json"
        try:
            with open(log_file) as f:
                logs = f.readlines()[-limit:]
            return self._send_json({"status": "ok", "logs": logs})
        except FileNotFoundError:
            return self._send_json({"status": "error", "message": "No log file found"}, 404)

    def _handle_start(self, token, body):
        mode = body.get("mode", "paper")
        config = body.get("config", {})
        self.state_manager.set_status(
            status="running",
            mode=mode,
            started_at=datetime.now(timezone.utc).isoformat(),
            config=config,
        )
        self._send_json({
            "status": "ok",
            "message": f"Bot started in {mode} mode",
            "mode": mode,
            "started_at": datetime.now(timezone.utc).isoformat(),
        })

    def _handle_stop(self, token, body):
        self.state_manager.set_status(status="stopped")
        self._send_json({"status": "ok", "message": "Bot stopped"})

    def _handle_restart(self, token, body):
        mode = body.get("mode", "paper")
        self.state_manager.set_status(
            status="running",
            mode=mode,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._send_json({
            "status": "ok",
            "message": f"Bot restarted in {mode} mode",
            "mode": mode,
        })

    def _handle_manual_trade(self, token, body):
        pair = body.get("pair", "")
        side = body.get("side", "buy")
        amount = body.get("amount", 0.0)
        if not pair or amount <= 0:
            return self._send_error("Invalid trade params: pair and amount required")
        now = datetime.now(timezone.utc).isoformat()
        self.state_manager.update({
            "last_manual_trade": {
                "pair": pair, "side": side, "amount": amount, "time": now
            }
        })
        try:
            from trade_database import TradeDatabase
            db = TradeDatabase()
            db.open_trade(pair=pair, side=side, entry_price=0, quantity=amount, strategy="manual")
        except ImportError:
            pass
        self._send_json({
            "status": "ok",
            "message": f"Manual {side} order placed: {amount} {pair}",
            "trade": {"pair": pair, "side": side, "amount": amount, "time": now},
        })

    def _handle_update_config(self, token, body):
        if not isinstance(body, dict):
            return self._send_error("Config must be a JSON object")
        state = self.state_manager.get_state()
        new_config = {**state.get("config", {}), **body}
        self.state_manager.update({"config": new_config})
        self._send_json({"status": "ok", "message": "Config updated", "config": new_config})


# ── Server ────────────────────────────────────────────────────────

class BotAPIServer:
    def __init__(
        self,
        port: int = 8080,
        jwt_secret: Optional[str] = None,
        ip_whitelist: Optional[list] = None,
        require_auth: bool = True,
        state_file: str = "bot_state.json",
    ):
        self.port = port
        self.jwt_secret = jwt_secret or secrets.token_hex(32)
        self.ip_whitelist = ip_whitelist
        self.require_auth = require_auth
        self.state_file = state_file
        self._setup()

    def _setup(self):
        BotAPIHandler.auth = JWTAuth(self.jwt_secret)
        BotAPIHandler.rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
        BotAPIHandler.state_manager = BotStateManager(self.state_file)
        BotAPIHandler.ip_whitelist = self.ip_whitelist
        BotAPIHandler.require_auth = self.require_auth

    def generate_token(self, role: str = "admin") -> str:
        return BotAPIHandler.auth.generate_token({"role": role, "sub": "api-client"})

    def start(self):
        server = HTTPServer(("0.0.0.0", self.port), BotAPIHandler)
        print(f"🌐 Remote Control API listening on 0.0.0.0:{self.port}")
        print(f"   Auth: {'JWT' if JWT_AVAILABLE else 'HMAC-fallback'}")
        print(f"   Token: {self.generate_token()}")
        print(f"   Endpoints:")
        print(f"     GET  /api/v1/status      — Bot status")
        print(f"     GET  /api/v1/config      — Bot config")
        print(f"     GET  /api/v1/trades      — Trade history")
        print(f"     GET  /api/v1/strategies  — Active strategies")
        print(f"     GET  /api/v1/performance — Performance metrics")
        print(f"     POST /api/v1/start       — Start bot")
        print(f"     POST /api/v1/stop        — Stop bot")
        print(f"     POST /api/v1/restart     — Restart bot")
        print(f"     POST /api/v1/trade       — Manual trade")
        print(f"     PUT  /api/v1/config      — Update config")
        server.serve_forever()

    def start_threaded(self) -> threading.Thread:
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        return thread


# ── CLI ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Trading Bot Remote Control API")
    parser.add_argument("--port", type=int, default=8080, help="API port")
    parser.add_argument("--token", type=str, default=None, help="JWT secret (auto-generated if not set)")
    parser.add_argument("--no-auth", action="store_true", help="Disable authentication (dev only)")
    parser.add_argument("--whitelist", type=str, default=None, help="Comma-separated IP whitelist")
    parser.add_argument("--state-file", type=str, default="bot_state.json", help="Bot state file path")
    args = parser.parse_args()

    whitelist = args.whitelist.split(",") if args.whitelist else None
    server = BotAPIServer(
        port=args.port,
        jwt_secret=args.token,
        ip_whitelist=whitelist,
        require_auth=not args.no_auth,
        state_file=args.state_file,
    )
    server.start()
