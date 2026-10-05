#!/usr/bin/env python3
"""
Apply the pUSD-migration patch to py-clob-client 0.34.6 + py_order_utils (py3.8 install).

Since 2026-04-28 Polymarket settles in pUSD (Polymarket USD), not USDC.e:
  * CTF Exchange           -> 0xE111180000d2663C0091e4f400237545B87B996B
  * Neg-Risk CTF Exchange  -> 0xe2222d279d744050d28e00520010520000310F59
  * Collateral (pUSD)      -> 0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB
  * CTF (ERC-1155)         -> unchanged 0x4D97DCd97eC945f40cF65F87097ACe5EA0476045
  * EIP-712 domain version -> "1" -> "2" (verified in Polymarket/ctf-exchange-v2 Hashing.sol)
  * USDC -> pUSD wrap      -> CollateralOnramp 0x93070a847efEf7F70739046A929D47a521F5B8ee
                              .wrap(USDC, to, amount)  (1:1, gas only)

Idempotent. Re-run after any PRoot-overlay wipe that re-installs the packages.
"""
import os, re, sys

PUSDEX   = "0xE111180000d2663C0091e4f400237545B87B996B"
PUSNEGR  = "0xe2222d279d744050d28e00520010520000310F59"
PUSD     = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"

OLD_EX      = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
OLD_NEGR    = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
OLD_USDCE_U = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
OLD_USDCE_L = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"

def patch(path, subs):
    src = open(path).read()
    changed = False
    for old, new in subs:
        if old in src:
            src = src.replace(old, new)
            changed = True
            print(f"  patched: {old[:44]}... -> {new}")
        elif new in src:
            print(f"  already patched: {new[:44]}...")
        else:
            print(f"  WARNING: neither found in {path}: {old[:44]}...")
    if changed:
        open(path, "w").write(src)
    return changed

def site():
    import py_clob_client, py_order_utils
    return os.path.dirname(py_clob_client.__file__), os.path.dirname(py_order_utils.__file__)

def main():
    clob, ou = site()
    print("py_clob_client:", clob)
    print("py_order_utils:", ou)
    patch(os.path.join(clob, "config.py"), [
        (f'exchange="{OLD_EX}"',      f'exchange="{PUSDEX}"'),
        (f'exchange="{OLD_NEGR}"',    f'exchange="{PUSNEGR}"'),
        (f'collateral="{OLD_USDCE_U}"', f'collateral="{PUSD}"'),
        (f'collateral="{OLD_USDCE_L}"', f'collateral="{PUSD}"'),
    ])
    patch(os.path.join(ou, "builders", "base_builder.py"), [
        ('version="1"', 'version="2"'),
    ])
    # verify
    import importlib, py_clob_client.config as cfg, py_order_utils.builders.base_builder as bb
    importlib.reload(cfg); importlib.reload(bb)
    cc = cfg.get_contract_config(137, False)
    cn = cfg.get_contract_config(137, True)
    import inspect
    domv = "2" in inspect.getsource(bb.BaseBuilder._get_domain_separator)
    print(f"verify: exchange={cc.exchange}")
    print(f"verify: negrisk ={cn.exchange}")
    print(f"verify: collateral={cc.collateral}")
    print(f"verify: domain v2 = {domv}")
    ok = (cc.exchange == PUSDEX and cn.exchange == PUSNEGR and cc.collateral == PUSD and domv)
    print("PATCH OK" if ok else "PATCH INCOMPLETE")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
