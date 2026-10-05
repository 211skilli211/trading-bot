"""Tests for pm_funding (pUSD on-chain funding, Polygon).

All on-chain / bridge calls are mocked — no network, no key.
"""
import json
import sys

import pytest

sys.path.insert(0, ".")
import pm_funding as pf


# ---------------------------------------------------------------------------
# encodings
# ---------------------------------------------------------------------------

def test_transfer_data_encoding():
    d = pf.usdc_transfer_data(
        "0xF160d9f53542Aba107b92EeE516b2d56610cb41F", 9890000)
    assert d.startswith("0xa9059cbb")
    assert len(d) == 2 + 8 + 64 + 64
    assert d[10:74] == "0" * 24 + "f160d9f53542aba107b92eee516b2d56610cb41f"
    assert int(d[74:138], 16) == 9890000


def test_approve_data_encoding_max():
    d = pf.approve_data(pf.EXCHANGE_STANDARD, pf.MAX_UINT256)
    assert d.startswith("0x095ea7b3")
    assert d[10:74] == "0" * 24 + pf.EXCHANGE_STANDARD.lower().replace("0x", "")
    assert int(d[74:138], 16) == pf.MAX_UINT256


# ---------------------------------------------------------------------------
# plan()
# ---------------------------------------------------------------------------

def _monkey_state(monkeypatch, pol=0.2, usdc=9.89, pusd=0.0):
    monkeypatch.setattr(pf, "balances", lambda: {
        "usdc": usdc, "usdc_e": 0.0, "pusd": pusd, "pol": pol})
    monkeypatch.setattr(pf, "bridge_address",
                        lambda wallet=None, timeout=20:
                        "0xF160d9f53542Aba107b92EeE516b2d56610cb41F")


def test_plan_full_with_pol(monkeypatch):
    _monkey_state(monkeypatch)
    p = pf.plan()
    kinds = [a["kind"] for a in p["actions"]]
    assert kinds == ["usdc-transfer", "pusd-approve", "pusd-approve"]
    assert p["actions"][0]["amount_wei"] == 9890000
    assert p["actions"][0]["to"].endswith("b41F")
    assert p["warnings"] == []


def test_plan_without_pol_drops_transfer(monkeypatch):
    _monkey_state(monkeypatch, pol=0.0)
    p = pf.plan()
    kinds = [a["kind"] for a in p["actions"]]
    assert "usdc-transfer" not in kinds
    assert any("POL balance" in w for w in p["warnings"])


def test_plan_with_pusd_already_present(monkeypatch):
    _monkey_state(monkeypatch, usdc=0.0, pusd=5.0)
    p = pf.plan()
    # no transfer (no USDC), approvals still offered
    assert all(a["kind"] == "pusd-approve" for a in p["actions"])
    assert any("no USDC" in w for w in p["warnings"])


def test_plan_custom_amount(monkeypatch):
    _monkey_state(monkeypatch, usdc=9.89)
    p = pf.plan(usd_amount=4.00)
    assert p["actions"][0]["amount_wei"] == 4000000


# ---------------------------------------------------------------------------
# execute_plan()
# ---------------------------------------------------------------------------

def test_execute_refuses_with_warnings(monkeypatch):
    with pytest.raises(pf.FundingError, match="warnings"):
        pf.execute_plan({"actions": [], "warnings": ["x"],
                         "transfer_wei": 0, "bridge": None})


def test_execute_flow(monkeypatch):
    _monkey_state(monkeypatch)
    p = pf.plan()
    sent = {}

    def fake_send_tx(to, data, value=0, gas=100000, gas_price_wei=None,
                     nonce=None):
        sent.setdefault("calls", []).append(
            (to, data[:10], nonce, gas_price_wei))
        return "0xhash%d" % len(sent["calls"])

    monkeypatch.setattr(pf, "send_tx", fake_send_tx)
    monkeypatch.setattr(pf, "_next_nonce", lambda: 7)
    monkeypatch.setattr(pf, "_gas_price_wei", lambda: 300_000_000_000)
    monkeypatch.setattr(pf, "_private_key", lambda: "0x" + "11" * 31 + "22")
    monkeypatch.setattr(pf, "wait_receipt",
                        lambda h: {"status": "0x1", "gasUsed": "0x186a0"})
    monkeypatch.setattr(pf, "erc20_balance",
                        lambda t, h: 9.89 if t == pf.PUSD else 0.0)
    monkeypatch.setattr(pf, "bridge_status",
                        lambda a: [{"sourceToken": "USDC",
                                    "sourceAmount": "9.89",
                                    "pUSDReceived": "9.89",
                                    "status": "completed"}])
    out = pf.execute_plan(p, wait_wrap=False)
    # 3 tx, nonces 7,8,9 in order, gas price pinned once
    assert [c[2] for c in sent["calls"]] == [7, 8, 9]
    assert sent["calls"][0][0] == pf.USDC_NATIVE
    assert sent["calls"][0][1] == "0xa9059cbb"
    assert sent["calls"][1][0] == pf.PUSD
    assert sent["calls"][2][0] == pf.PUSD
    assert out["pusd"] == 9.89
    assert out["bridge_txs"][0]["status"] == "completed"
    assert len(out["hashes"]) == 3


# ---------------------------------------------------------------------------
# send_tx() / wait_receipt()
# ---------------------------------------------------------------------------

def test_send_tx_builds_eip155(monkeypatch):
    captured = {}

    class FakeAccount:
        @staticmethod
        def sign_transaction(tx_dict, key):
            captured["tx"] = tx_dict
            captured["key"] = key

            class _R:
                rawTransaction = b"\x01\x02"
            return _R()

    monkeypatch.setattr(pf, "Account", FakeAccount)
    monkeypatch.setattr(pf, "_private_key", lambda: "0x" + "ab" * 32)
    monkeypatch.setattr(pf, "rpc_call", lambda m, p, timeout=20: {
        "eth_getTransactionCount": "0x2a",
        "eth_gasPrice": "0x45d8",
        "eth_sendRawTransaction": "0x" + "11" * 32,
    }[m])
    h = pf.send_tx(pf.USDC_NATIVE, "0xa9059cbb" + "00" * 64,
                   nonce=None, gas_price_wei=None)
    assert h == "0x" + "11" * 32
    assert captured["tx"]["chainId"] == 137
    assert captured["tx"]["nonce"] == 42
    assert captured["tx"]["gasPrice"] == 0x45d8
    assert captured["tx"]["to"] == pf.USDC_NATIVE
    assert captured["tx"]["value"] == 0
    assert captured["key"] == "0x" + "ab" * 32


def test_send_tx_missing_key(monkeypatch):
    monkeypatch.delenv("POLYMARKET_PRIVATE_KEY", raising=False)
    with pytest.raises(pf.FundingError, match="PRIVATE_KEY"):
        pf.send_tx(pf.USDC_NATIVE, "0x")


def test_wait_receipt_success(monkeypatch):
    calls = {"n": 0}

    def fake_rpc(m, p, timeout=20):
        calls["n"] += 1
        return None if calls["n"] < 3 else \
            {"status": "0x1", "gasUsed": "0x5208"}

    monkeypatch.setattr(pf, "rpc_call", fake_rpc)
    monkeypatch.setattr(pf.time, "sleep", lambda s: None)
    rcpt = pf.wait_receipt("0xabc", timeout=60, poll=0)
    assert rcpt["status"] == "0x1"
    assert calls["n"] == 3


def test_wait_receipt_revert(monkeypatch):
    monkeypatch.setattr(pf, "rpc_call",
                        lambda m, p, timeout=20:
                        {"status": "0x0", "gasUsed": "0x5208"})
    monkeypatch.setattr(pf.time, "sleep", lambda s: None)
    with pytest.raises(pf.FundingError, match="reverted"):
        pf.wait_receipt("0xabc", timeout=5, poll=0)


# ---------------------------------------------------------------------------
# report()
# ---------------------------------------------------------------------------

def test_report_renders(monkeypatch):
    _monkey_state(monkeypatch)
    p = pf.plan()
    out = pf.report(p)
    assert "USDC (native):    $9.89" in out
    assert "bridge deposit:" in out
    assert "0xF160d9f53542Aba107b92EeE516b2d56610cb41F" in out
    _monkey_state(monkeypatch, pol=0.0)
    out2 = pf.report(pf.plan())
    assert "⚠" in out2
