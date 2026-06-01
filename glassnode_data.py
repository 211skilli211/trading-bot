#!/usr/bin/env python3
"""
Glassnode On-Chain Data (ported from Fincept-Corporation/FinceptTerminal)
============================================================================
Bitcoin/Ethereum on-chain metrics — active addresses, tx count, hash rate, NVT.

Adapted from: fincept-qt/scripts/glassnode_data.py

Usage:
    from glassnode_data import GlassnodeClient
    
    client = GlassnodeClient(api_key="your_key")
    data = client.get_active_addresses("BTC")
"""

import json
import os
import time
from typing import Any, Dict, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class GlassnodeClient:
    """Fetch on-chain metrics from Glassnode API."""

    BASE_URL = "https://api.glassnode.com/v1/metrics"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('GLASSNODE_API_KEY', '')
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 min cache

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        if not HAS_REQUESTS:
            return {"error": "requests library not installed"}

        if not self.api_key:
            return {"error": "GLASSNODE_API_KEY not set"}

        # Check cache
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                return cached_data

        url = f"{self.BASE_URL}/{endpoint}"
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            self._cache[cache_key] = (data, time.time())
            return data
        except Exception as e:
            return {"error": str(e)}

    def _params(self, asset: str, interval: str = "24h", **extra) -> Dict:
        p = {"a": asset, "i": interval, "api_key": self.api_key}
        p.update(extra)
        return p

    def active_addresses(self, asset: str = "BTC", interval: str = "24h") -> Any:
        """Number of active addresses."""
        return self._request("addresses/active_count", self._params(asset, interval))

    def transaction_count(self, asset: str = "BTC", interval: str = "24h") -> Any:
        """Total transactions."""
        return self._request("transactions/count", self._params(asset, interval))

    def hash_rate(self, asset: str = "BTC", interval: str = "24h") -> Any:
        """Mining hash rate."""
        return self._request("mining/hash_rate_mean", self._params(asset, interval))

    def nvt_ratio(self, asset: str = "BTC", interval: str = "24h") -> Any:
        """Network Value to Transactions ratio."""
        return self._request("indicators/nvt", self._params(asset, interval))

    def sopr(self, asset: str = "BTC", interval: str = "24h") -> Any:
        """Spent Output Profit Ratio."""
        return self._request("indicators/sopr", self._params(asset, interval))

    def get_all_metrics(self, asset: str = "BTC") -> Dict[str, Any]:
        """Fetch all key metrics at once."""
        return {
            "active_addresses": self.active_addresses(asset),
            "transaction_count": self.transaction_count(asset),
            "hash_rate": self.hash_rate(asset),
            "nvt_ratio": self.nvt_ratio(asset),
            "sopr": self.sopr(asset),
            "fetched_at": int(time.time())
        }


# CLI interface
def main():
    import sys
    client = GlassnodeClient()
    args = sys.argv[1:]

    if not args:
        print(json.dumps({"error": "No command"}))
        return

    cmd = args[0]
    asset = args[1] if len(args) > 1 else "BTC"

    commands = {
        "active_addresses": client.active_addresses,
        "transactions": client.transaction_count,
        "hash_rate": client.hash_rate,
        "nvt": client.nvt_ratio,
        "sopr": client.sopr,
        "all": client.get_all_metrics,
    }

    fn = commands.get(cmd)
    if fn:
        print(json.dumps(fn(asset)))
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))


if __name__ == "__main__":
    main()
