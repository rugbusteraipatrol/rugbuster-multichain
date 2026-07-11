# AVAX Preflight Shield - Live Demo

Public endpoint: `https://rugbuster-api-production.up.railway.app/v1/preflight`

The preflight endpoint is a read-only gate for a bot, wallet, or agent to call before
signing a buy, swap, transfer, or approval. It uses the existing Avalanche scan data when
available and returns `ALLOW`, `WARN`, or `BLOCK`. It does not submit transactions, connect
wallets, or invoke the collector.

## Live transcript

Verified against the public Railway deployment on 2026-07-11. `latency_ms` below is measured
inside the live API; network round-trip time from the test client was 220-745 ms.

### Integrity DAO (ID) - BLOCK

`0x34a528da3b2ea5c6ad1796eba756445d1299a577`

```bash
curl "https://rugbuster-api-production.up.railway.app/v1/preflight?target=0x34a528da3b2ea5c6ad1796eba756445d1299a577&chain=avax&action=buy"
```

```json
{
  "verdict": "BLOCK",
  "risk": 90,
  "reasons": [
    "near_zero_deployer_balance",
    "less_than_10_holders",
    "mint_authority_enabled",
    "holder_concentration",
    "high_risk_score"
  ],
  "latency_ms": 198
}
```

### Nexus - WARN

`0x751ceba0aaeb09dcf6b69d1a93fd561b2633a6ca`

```json
{
  "verdict": "WARN",
  "risk": 55,
  "reasons": ["bot_activity", "near_zero_deployer_balance", "less_than_10_holders"],
  "latency_ms": 106
}
```

### BITS - ALLOW

`0x48d64aef167ccc764b11d4ee6e657665c05eaec5`

```json
{
  "verdict": "ALLOW",
  "risk": 20,
  "reasons": ["less_than_10_holders"],
  "latency_ms": 103
}
```

### WAVAX - ALLOW fallback

`0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7`

An untracked token returns `WARN` and `unknown_token_scanning` while the fallback assessment
starts. The next request returned the completed live result:

```json
{
  "verdict": "ALLOW",
  "risk": 12,
  "cache": true,
  "reasons": [
    "token_name_readable_on_chain",
    "token_symbol_readable_on_chain",
    "decimals_value_is_within_normal_erc_20_range",
    "total_supply_readable_on_chain",
    "thin_liquidity",
    "strong_24h_volume_at_14_872_794",
    "24h_volatility_is_moderate_at_0_2"
  ],
  "latency_ms": 47
}
```

## Public demo

The static interactive page is published at `https://rugbuster.io/shield-demo/`. It calls the
same live endpoint directly and includes the four real examples above.

| Token | Expected verdict | Live result |
| --- | --- | --- |
| Integrity DAO | BLOCK | BLOCK |
| Nexus | WARN | WARN |
| BITS | ALLOW | ALLOW |
| WAVAX fallback | ALLOW | ALLOW after the initial background assessment |
