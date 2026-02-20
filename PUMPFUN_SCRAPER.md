# Pump.fun Scraper for Solana Token Discovery

A high-performance scraper for discovering new tokens on Pump.fun and monitoring them for arbitrage opportunities.

## Features

- **Real-time Token Discovery**: Fetches newly created tokens from Pump.fun
- **Bonding Curve Monitoring**: Tracks progress toward Raydium migration (~$69k market cap)
- **Migration Detection**: Identifies tokens nearing migration (85%+ bonding curve)
- **Multi-source Data**: Falls back to DexScreener API if Pump.fun API is unavailable
- **Rate Limiting**: Built-in rate limiting to avoid API bans
- **Arbitrage Analysis**: Compares prices between Pump.fun and Raydium

## Installation

The scraper is included in the trading bot. No additional installation required.

```bash
# Test the scraper
python scrapers/pumpfun.py

# Run integration examples
python pumpfun_integration.py --scan
```

## Usage

### Basic Usage

```python
from scrapers.pumpfun import PumpFunScraper, TokenCandidate

# Initialize scraper
scraper = PumpFunScraper()

# Get new tokens
tokens = scraper.get_new_tokens(limit=20)

for token in tokens:
    print(f"{token.symbol}: ${token.usd_market_cap:,.0f} ({token.bonding_curve_progress:.1f}% bonded)")
```

### Find Tokens Nearing Migration

```python
# Get tokens about to migrate to Raydium
migrating = scraper.get_migrating_tokens()

for token in migrating:
    print(f"🚀 {token.symbol}: {token.bonding_curve_progress:.1f}% bonded")
    print(f"   Estimated migration: ~{token.migration_eta_minutes:.0f} minutes")
```

### Configuration

```python
from scrapers.pumpfun import PumpFunScraper, PumpFunConfig

config = PumpFunConfig(
    min_request_interval=1.0,      # Seconds between requests
    max_requests_per_minute=30,    # Rate limit
    migration_alert_threshold=85.0, # Alert at 85% bonding
    max_token_age_minutes=60,      # Only tokens < 1 hour old
)

scraper = PumpFunScraper(config=config)
```

## Command Line Interface

```bash
# Scan for new tokens
python pumpfun_integration.py --scan --limit 50

# Find tokens nearing migration
python pumpfun_integration.py --migrations

# Find arbitrage opportunities
python pumpfun_integration.py --arbitrage

# Continuous monitoring
python pumpfun_integration.py --monitor --interval 60

# Export to JSON
python pumpfun_integration.py --export tokens.json --limit 100
```

## TokenCandidate Object

```python
@dataclass
class TokenCandidate:
    mint_address: str          # Token mint address
    name: str                  # Token name
    symbol: str                # Token symbol
    description: str           # Token description
    creator_address: str       # Creator wallet
    creation_time: datetime    # When token was created
    usd_market_cap: float      # Market cap in USD
    price_usd: float           # Price in USD
    bonding_curve_progress: float  # 0-100%
    is_nearing_migration: bool     # True if >85% bonded
    is_migrated: bool              # True if on Raydium
    raydium_pool: str          # Raydium pool address (if migrated)
    priority: str              # HIGH, NORMAL, or LOW
```

## Bonding Curve Mechanics

Pump.fun uses a bonding curve pricing model:

1. **Launch**: Token starts at ~$0 market cap
2. **Growth**: Price increases as more people buy
3. **Migration**: At ~$69k market cap (100% bonded), token migrates to Raydium
4. **Arbitrage**: Price differences between Pump.fun and Raydium during/after migration

## API Endpoints

The scraper tries multiple data sources:

1. **Primary**: `https://pump.fun/api/coins/for-you`
2. **Fallback**: DexScreener API (`https://api.dexscreener.com`)

## Integration with Discovery Engine

```python
from discovery_engine import DiscoveryEngine

# Initialize engine with Pump.fun enabled
engine = DiscoveryEngine()

# Scan for arbitrage opportunities
opportunities = engine.find_arbitrage_opportunities()

for opp in opportunities:
    if 'pumpfun' in opp.sources:
        print(f"💰 {opp.symbol}: {opp.price_spread_pct:.2f}% spread")
```

## Rate Limiting

The scraper includes built-in rate limiting:
- Default: 30 requests per minute
- Minimum interval: 1 second between requests
- Automatic retry with exponential backoff

## Error Handling

- Automatic fallback to alternative data sources
- Graceful handling of API failures
- Detailed logging for debugging

## Monitoring Checklist

When monitoring tokens nearing migration:

- [ ] **85%+ Bonded**: Token is nearing migration
- [ ] **Liquidity**: Check if there's sufficient liquidity
- [ ] **Volume**: High volume indicates interest
- [ ] **Creator**: Check creator's wallet for legitimacy
- [ ] **Age**: Newer tokens have higher volatility
- [ ] **Social**: Check if token has social links/description

## Example Output

```
======================================================================
🔍 SCANNING PUMP.FUN FOR NEW TOKENS
======================================================================

✅ Found 5 new tokens

  ============================================================
  🪙 BONK (Bonk Token)
  ============================================================
  Mint: 7n8...pump
  Market Cap: $45,231.00
  Price: $0.000045231000
  Bonding Curve: 65.6%
  Age: 12.5 minutes

  ============================================================
  🪙 SAMO (Samoyedcoin)
  ============================================================
  Mint: 3x6...pump
  Market Cap: $62,451.00
  Price: $0.000062451000
  Bonding Curve: 90.5%
  🚨 MIGRATION IMMINENT! (~19 min)
  Age: 8.3 minutes

======================================================================
📊 SUMMARY: 2 tokens, 1 nearing migration
======================================================================
```

## Best Practices

1. **Run multiple instances**: Use different data sources for redundancy
2. **Monitor continuously**: Use `--monitor` mode for real-time alerts
3. **Validate tokens**: Always check creator and liquidity before trading
4. **Be quick**: Opportunities disappear fast during migration
5. **Risk management**: Never risk more than you can afford to lose

## Troubleshooting

### No tokens found
- Check internet connection
- Verify rate limits haven't been exceeded
- Try using `--verbose` for debug output

### API errors
- The scraper automatically falls back to DexScreener
- If both fail, check if APIs are temporarily down

### Incorrect data
- Market cap is estimated from price and supply
- Bonding curve progress is approximate
- Always verify with official Pump.fun site

## License

Part of the trading bot project.
