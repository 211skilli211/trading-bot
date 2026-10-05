"""Polymarket pUSD on-chain funding (Polygon) — local signing, public RPC.

Background (verified on-chain 2026-10-05):
  - Polymarket settles in pUSD (0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB),
    not USDC anymore.
  - USDC sitting in our EOA must be wrapped to pUSD to be tradable.
  - Polymarket's bridge (bridge.polymarket.com) issues a per-wallet EVM
    deposit address; USDC arriving there is auto-wrapped to pUSD by
    Polymarket's relayer (their gas). Sending our own USDC to that address
    therefore costs us exactly ONE USDC transfer tx.
  - pUSD must then be approved for the two CLOB exchange contracts so the
    matching operator can settle orders (operator pays that gas).

Gas cost: ~0.01 POL per ERC-20 tx at typical Polygon prices; 3 tx total.

No web3 dependency: raw JSON-RPC via curl + eth-account local signing.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Dict, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from eth_account import Account
except ImportError:  # pragma: no cover
    Account = None

CHAIN_ID = 137
WALLET = "0xEd42785Bb96799b957cB39D987553A9E8b71c9E6"

# pUSD-era contracts (docs.polymarket.com/resources/contracts, 2026-10-05)
EXCHANGE_STANDARD = "0xE111180000d2663C0091e4f400237545B87B996B"
EXCHANGE_NEG_RISK = "0xe2222d279d744050d28e00520010520000310F59"
PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
USDC_NATIVE = "0x3c499c542cEF5E3811E1192ce70d8cC03d5c3359"  # "USD Coin"
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"       # "USD Coin (PoS)"
COLLATERAL_ONRAMP = "0x93070a847efEf7F70739046A929D47a521F5B8ee"

BRIDGE_API = "https://bridge.polymarket.com"
RPCS = [
    "https://polygon-bor-rpc.publicnode.com",
    "https://polygon-mainnet.public.blastapi.io",
    "https://1rpc.io/matic",
    "https://polygon.drpc.org",
]

MAX_UINT256 = 2 ** 256 - 1
MIN_POL_FOR_FUNDING = 0.05  # 3 ERC-20 tx with headroom
GAS_LIMIT = 100000


class FundingError(Exception):
    pass


# ---------------------------------------------------------------------------
# raw JSON-RPC
# ---------------------------------------------------------------------------

def rpc_call(method: str, params: list, timeout: int = 20) -> Optional[object]:
    """Try the RPC fallbacks in order; raise FundingError if all fail."""
    last_err = None
    for url in RPCS:
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                              "params": params})
        try:
            p = subprocess.run(
                ["curl", "-sS", "-m", str(timeout), "-X", "POST",
                 "-H", "Content-Type: application/json",
                 "--data", payload, url],
                capture_output=True, text=True)
            j = json.loads(p.stdout)
        except Exception as e:  # curl fail / bad json
            last_err = e
            continue
        if "error" in j:
            last_err = FundingError("rpc error %s: %s" % (
                method, json.dumps(j["error"])[:200]))
            continue
        return j.get("result")
    raise FundingError("all Polygon RPCs failed for %s: %s" % (method, last_err))


def hex2int(h) -> int:
    return int(h, 16) if isinstance(h, str) else int(h)


def pad(addr: str) -> str:
    return addr.lower().replace("0x", "").rjust(64, "0")


def erc20_balance(token: str, holder: str) -> float:
    r = rpc_call("eth_call", [
        {"to": token, "data": "0x70a08231" + pad(holder)}, "latest"])
    return hex2int(r) / 1e6


def balances() -> Dict[str, float]:
    return {
        "usdc": erc20_balance(USDC_NATIVE, WALLET),
        "usdc_e": erc20_balance(USDC_E, WALLET),
        "pusd": erc20_balance(PUSD, WALLET),
        "pol": hex2int(rpc_call("eth_getBalance", [WALLET, "latest"])) / 1e18,
    }


# ---------------------------------------------------------------------------
# bridge (Polymarket-managed wrap)
# ---------------------------------------------------------------------------

def bridge_address(wallet: str = WALLET, timeout: int = 20) -> str:
    """Per-wallet EVM deposit address (auto-wraps USDC -> pUSD)."""
    if requests is None:
        raise FundingError("requests not installed")
    r = requests.post(BRIDGE_API + "/deposit", json={"address": wallet},
                      timeout=timeout)
    if not (200 <= r.status_code < 300):
        raise FundingError("bridge /deposit HTTP %s" % r.status_code)
    data = r.json()
    evm = (data.get("address") or {}).get("evm")
    if not evm:
        raise FundingError("bridge /deposit returned no evm address")
    return evm


def bridge_status(bridge_addr: str, timeout: int = 20) -> list:
    if requests is None:
        raise FundingError("requests not installed")
    try:
        r = requests.get(BRIDGE_API + "/status/" + bridge_addr,
                         timeout=timeout)
        if 200 <= r.status_code < 300:
            data = r.json()
            return data.get("transactions") or []
    except (requests.RequestException, ValueError):
        pass
    return []


# ---------------------------------------------------------------------------
# transaction building / sending
# ---------------------------------------------------------------------------

def _private_key() -> str:
    key = os.environ.get("POLYMARKET_PRIVATE_KEY", "").strip()
    if not key:
        raise FundingError("POLYMARKET_PRIVATE_KEY missing in .env")
    return key if key.startswith("0x") else "0x" + key


def _next_nonce() -> int:
    return hex2int(rpc_call("eth_getTransactionCount", [WALLET, "pending"]))


def _gas_price_wei() -> int:
    return hex2int(rpc_call("eth_gasPrice", []))


def _sign(tx_dict: dict, key: str):
    if Account is None:
        raise FundingError("eth-account not installed")
    signed = Account.sign_transaction(tx_dict, key)
    raw = getattr(signed, "rawTransaction", None)
    if raw is None:
        raw = signed.raw_transaction
    return raw


def send_tx(to: str, data: str, value: int = 0, gas: int = GAS_LIMIT,
            gas_price_wei: Optional[int] = None, nonce: Optional[int] = None
            ) -> str:
    """Sign + broadcast a legacy EIP-155 Polygon tx; return the tx hash."""
    key = _private_key()
    tx = {
        "chainId": CHAIN_ID,
        "nonce": hex2int(nonce) if nonce is not None else _next_nonce(),
        "to": to,
        "value": value,
        "gas": gas,
        "gasPrice": gas_price_wei if gas_price_wei is not None
        else _gas_price_wei(),
        "data": data,
    }
    raw = _sign(tx, key)
    raw_hex = raw.hex() if isinstance(raw, (bytes, bytearray)) else str(raw)
    if not raw_hex.startswith("0x"):
        raw_hex = "0x" + raw_hex
    tx_hash = rpc_call("eth_sendRawTransaction", [raw_hex])
    if not tx_hash:
        raise FundingError("eth_sendRawTransaction returned no hash")
    return tx_hash


def wait_receipt(tx_hash: str, timeout: int = 240, poll: int = 3) -> dict:
    """Poll until the receipt lands; raise on failure / timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        rcpt = rpc_call("eth_getTransactionReceipt", [tx_hash])
        if rcpt:
            if rcpt.get("status") == "0x1":
                return rcpt
            raise FundingError("tx %s reverted (status 0x%s)" % (
                tx_hash, rcpt.get("status")))
        time.sleep(poll)
    raise FundingError("no receipt for %s within %ss" % (tx_hash, timeout))


# ---------------------------------------------------------------------------
# funding flows
# ---------------------------------------------------------------------------

def usdc_transfer_data(to_addr: str, amount_wei: int) -> str:
    return "0xa9059cbb" + pad(to_addr) + format(amount_wei, "x").rjust(64, "0")


def approve_data(spender: str, amount_wei: int) -> str:
    return "0x095ea7b3" + pad(spender) + format(amount_wei, "x").rjust(64, "0")


def plan(usd_amount: Optional[float] = None) -> dict:
    """Compute the funding plan from live on-chain state.

    Returns {balances, bridge, transfer_wei, actions[], warnings[]}.
    """
    bal = balances()
    warnings = []
    transfer_amount = usd_amount
    if transfer_amount is None:
        transfer_amount = bal["usdc"]
    transfer_amount = round(float(transfer_amount), 6)
    if transfer_amount <= 0:
        warnings.append("no USDC in wallet — nothing to transfer")
    if bal["pol"] < MIN_POL_FOR_FUNDING:
        warnings.append(
            "POL balance %.4f < %.2f needed for gas (~3 tx)" % (
                bal["pol"], MIN_POL_FOR_FUNDING))
    bridge = None
    try:
        bridge = bridge_address()
    except FundingError as e:
        warnings.append("bridge address unavailable: %s" % e)
    actions = []
    if transfer_amount > 0 and bal["pol"] >= MIN_POL_FOR_FUNDING and bridge:
        actions.append({
            "kind": "usdc-transfer",
            "to": bridge,
            "amount": transfer_amount,
            "amount_wei": int(round(transfer_amount * 1e6)),
        })
    if bal["pusd"] > 0 or transfer_amount > 0:
        for ex in (EXCHANGE_STANDARD, EXCHANGE_NEG_RISK):
            actions.append({
                "kind": "pusd-approve",
                "spender": ex,
                "amount": "max",
            })
    return {
        "balances": bal,
        "bridge": bridge,
        "transfer_wei": int(transfer_amount * 1e6),
        "actions": actions,
        "warnings": warnings,
    }


def execute_plan(plan_dict: dict, wait_wrap: bool = True) -> dict:
    """Execute the plan's actions on-chain. Requires clean plan (no warnings).

    Returns {hashes: [...], pUSD: float, bridge_txs: [...]}.
    """
    if plan_dict["warnings"]:
        raise FundingError("refusing to execute with warnings: " +
                           "; ".join(plan_dict["warnings"]))
    hashes = []
    key = _private_key()  # fail fast if the key is missing
    nonce = _next_nonce()
    gas_price = _gas_price_wei()
    for act in plan_dict["actions"]:
        if act["kind"] == "usdc-transfer":
            data = usdc_transfer_data(act["to"], act["amount_wei"])
            tx_hash = send_tx(USDC_NATIVE, data, nonce=nonce,
                              gas_price_wei=gas_price)
        elif act["kind"] == "pusd-approve":
            data = approve_data(act["spender"], MAX_UINT256)
            tx_hash = send_tx(PUSD, data, nonce=nonce,
                              gas_price_wei=gas_price)
        else:
            raise FundingError("unknown action %r" % act["kind"])
        rcpt = wait_receipt(tx_hash)
        hashes.append({"hash": tx_hash, "kind": act["kind"],
                       "gasUsed": hex2int(rcpt.get("gasUsed", "0x0"))})
        nonce += 1
    # poll for the wrapped pUSD to land
    pusd = erc20_balance(PUSD, WALLET)
    if wait_wrap and plan_dict["transfer_wei"] > 0:
        deadline = time.time() + 600
        while pusd <= 0 and time.time() < deadline:
            time.sleep(15)
            pusd = erc20_balance(PUSD, WALLET)
    return {
        "hashes": hashes,
        "pusd": pusd,
        "bridge_txs": bridge_status(plan_dict["bridge"])
        if plan_dict.get("bridge") else [],
    }


def report(plan_dict: dict) -> str:
    b = plan_dict["balances"]
    lines = [
        "🏦 Polymarket funding plan",
        "   USDC (native):    $%.2f" % b["usdc"],
        "   USDC.e:           $%.2f" % b["usdc_e"],
        "   pUSD (tradable):  $%.2f" % b["pusd"],
        "   POL (gas):        %.4f" % b["pol"],
    ]
    if plan_dict.get("bridge"):
        lines.append("   bridge deposit:   %s" % plan_dict["bridge"])
    for act in plan_dict["actions"]:
        if act["kind"] == "usdc-transfer":
            lines.append("   → transfer $%.2f USDC → bridge (auto-wraps to pUSD)"
                         % (act["amount"] * 1e6 / 1e6))
        else:
            lines.append("   → approve pUSD → exchange %s…" % act["spender"][2:10])
    for w in plan_dict["warnings"]:
        lines.append("   ⚠ " + w)
    if not plan_dict["actions"]:
        lines.append("   nothing to do")
    return "\n".join(lines)
