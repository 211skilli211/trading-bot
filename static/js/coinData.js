// Coin symbol to CoinGecko ID mapping
const COIN_IDS = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
    'BNB': 'binancecoin',
    'XRP': 'ripple',
    'ADA': 'cardano',
    'DOGE': 'dogecoin',
    'TRX': 'tron',
    'AVAX': 'avalanche-2',
    'LINK': 'chainlink',
    'DOT': 'polkadot',
    'MATIC': 'matic-network',
    'SHIB': 'shiba-inu',
    'LTC': 'litecoin',
    'BCH': 'bitcoin-cash',
    'USDC': 'usd-coin',
    'USDT': 'tether',
    'TON': 'the-open-network',
    'SUI': 'sui',
    'APT': 'aptos',
    'NEAR': 'near',
    'UNI': 'uniswap',
    'ATOM': 'cosmos',
    'ETC': 'ethereum-classic',
    'XLM': 'stellar',
    'FIL': 'filecoin',
    'ALGO': 'algorand',
    'VET': 'vechain',
    'ICP': 'internet-computer',
    'AAVE': 'aave',
    'GRT': 'the-graph',
    'MANA': 'decentraland',
    'SAND': 'the-sandbox',
    'AXS': 'axie-infinity',
    'THETA': 'theta-token',
    'XTZ': 'tezos',
    'FTM': 'fantom',
    'HBAR': 'hedera-hashgraph',
    'EGLD': 'elrond-erd-2'
};

// CoinGecko image URLs (reliable CDN)
function getCoinIconUrl(symbol) {
    const id = COIN_IDS[symbol.toUpperCase()];
    if (id) {
        return `https://assets.coingecko.com/coins/images/1/small/${id}.png`;
    }
    // Fallback to UI avatars
    return `https://ui-avatars.com/api/?name=${symbol}&background=random&color=fff&size=64&bold=true`;
}

// Get CoinGecko ID
function getCoinGeckoId(symbol) {
    return COIN_IDS[symbol.toUpperCase()] || symbol.toLowerCase();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { COIN_IDS, getCoinIconUrl, getCoinGeckoId };
}
