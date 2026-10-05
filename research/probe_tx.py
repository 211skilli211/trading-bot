#!/usr/bin/env python3
"""Trace a Polygon tx by hash + check our Polymarket wallet on-chain. Disposable probe.

Usage: python3 research/probe_tx.py [0xhash]
"""
import json
import subprocess
import sys

TX = sys.argv[1] if len(sys.argv) > 1 else "0x9def87297988275427218ff43a5a8f63629f31a4525103533e76ca456bbea0c9"
WALLET = "0xEd42785Bb96799b957cB39D987553A9E8b71c9E6"
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_NATIVE = "0x3c499c542cef5e3811f12ae2e5637d3d9f17dc7f"
USDT = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

CHAINS = [
    ("Polygon", [
        "https://polygon-bor-rpc.publicnode.com",
        "https://polygon-mainnet.public.blastapi.io",
        "https://1rpc.io/matic",
        "https://polygon.drpc.org",
        "https://polygon-rpc.com",
        "https://polygon.llamarpc.com",
        "https://endpoints.omniatech.io/v1/matic/mainnet/public",
    ]),
    ("Ethereum", [
        "https://ethereum-rpc.publicnode.com",
        "https://eth.drpc.org",
        "https://1rpc.io/eth",
    ]),
    ("BSC", ["https://bsc-rpc.publicnode.com"]),
    ("Arbitrum", ["https://arbitrum-rpc.publicnode.com"]),
    ("Optimism", ["https://optimism-rpc.publicnode.com"]),
]


def rpc(url, method, params):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    p = subprocess.run(
        ["curl", "-sS", "-m", "15", "-X", "POST",
         "-H", "Content-Type: application/json", "--data", payload, url],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        raise RuntimeError("curl %s: %s" % (p.returncode, p.stderr[:200]))
    try:
        j = json.loads(p.stdout)
    except Exception:
        raise RuntimeError("bad json: %s" % p.stdout[:200])
    if "error" in j:
        raise RuntimeError("rpc error: %s" % json.dumps(j["error"])[:200])
    return j.get("result")


def pad_addr(a):
    return a.lower().replace("0x", "").rjust(64, "0")


def hex2int(h):
    return int(h, 16) if isinstance(h, str) else int(h)


def find_tx():
    for chain, rpcs in CHAINS:
        for url in rpcs:
            try:
                tx = rpc(url, "eth_getTransactionByHash", [TX])
            except Exception as e:
                print("  %-10s %s  FAIL: %s" % (chain, url, str(e)[:120]))
                continue
            if tx:
                print("  %-10s %s  FOUND" % (chain, url))
                return chain, url, tx
            else:
                print("  %-10s %s  null" % (chain, url))
    return None, None, None


def decode_logs(logs):
    print("\n-- receipt logs: %d --" % len(logs))
    for lg in logs:
        topics = lg.get("topics", [])
        data = lg.get("data", "0x")
        addr = lg.get("address", "").lower()
        if topics and topics[0].lower() == TRANSFER_TOPIC and len(topics) == 3:
            frm = "0x" + topics[1][-40:]
            to = "0x" + topics[2][-40:]
            amt = hex2int(data) / 1e6
            print("  Transfer: %s -> %s  amt=%s (6dp)" % (frm, to, amt))
        else:
            print("  log addr=%s t0=%s data=%s" % (addr, topics[:1], data[:80]))


def erc20_bal(url, token, holder):
    data = "0x70a08231" + pad_addr(holder)
    r = rpc(url, "eth_call", [{"to": token, "data": data}, "latest"])
    return hex2int(r) / 1e6


def main():
    print("TX:", TX)
    chain, url, tx = find_tx()
    if not tx:
        print("\nNOT FOUND on any chain tried -> still pending at RedotPay (or wrong hash).")
        return
    print("\n-- tx --")
    print("  chain:     ", chain)
    print("  from:      ", tx.get("from"))
    print("  to:        ", tx.get("to"))
    print("  value:     ", hex2int(tx.get("value", "0x0")) / 1e18)
    print("  block:     ", tx.get("blockNumber"))
    print("  input[:96]:", tx.get("input", "0x")[:96])

    receipt = rpc(url, "eth_getTransactionReceipt", [TX])
    print("\n-- receipt --")
    print("  status:    ", receipt.get("status"))
    print("  block:     ", receipt.get("blockNumber"))
    decode_logs(receipt.get("logs", []))

    if chain != "Polygon":
        print("\nNOTE: tx is NOT on Polygon — Polymarket needs USDC on Polygon.")
        return

    print("\n-- our wallet on Polygon (latest) --")
    for name, tok in [("USDC.e (Polymarket collateral)", USDC_E),
                      ("USDC native", USDC_NATIVE),
                      ("USDT", USDT)]:
        try:
            print("  %-30s %s" % (name, erc20_bal(url, tok, WALLET)))
        except Exception as e:
            print("  %-30s ERR %s" % (name, str(e)[:100]))
    try:
        print("  %-30s %s POL" % ("POL (gas)", hex2int(rpc(url, "eth_getBalance", [WALLET, "latest"])) / 1e18))
    except Exception as e:
        print("  %-30s ERR %s" % ("POL", str(e)[:100]))
    # allowance of USDC.e to CTF exchange
    try:
        data = "0xdd62ed3e" + pad_addr(WALLET) + pad_addr(CTF_EXCHANGE)
        r = rpc(url, "eth_call", [{"to": USDC_E, "data": data}, "latest"])
        print("  %-30s %s USDC.e allowance -> CTF exchange" % ("allowance", hex2int(r) / 1e6))
    except Exception as e:
        print("  allowance ERR %s" % str(e)[:100])


if __name__ == "__main__":
    main()
