# AVAX Preflight Shield — Live Demo

Same pattern as the RugBuster Solana Preflight Shield: a pre-transaction ALLOW/WARN/BLOCK
gate that a bot, wallet, or AI agent calls *before* signing a swap. This is the Avalanche
C-Chain equivalent, running against a real flagged token pulled live from RugBuster's
Avalanche scan history — not a fabricated example.

Status as of 2026-07-10: confirmed working locally (`api/server.py`, `chains/avalanche`
DB-direct AVAX path). Not yet committed/deployed — see main status report for details.

## The token

**Integrity DAO (ID)** — `0x34a528da3b2ea5c6ad1796eba756445d1299a577`

Scanned by the live AVAX collector on 2026-07-10 08:52 UTC and stored in the production
`avax_scans` table with `label = DANGER`. Real risk signals from that scan:

- Near-zero deployer balance
- Fewer than 10 holders
- Mint function present in bytecode (owner can inflate supply at will)
- Holder concentration CRITICAL — top 5 wallets hold 91.0% of supply

Explorer: https://snowtrace.io/address/0x34a528da3b2ea5c6ad1796eba756445d1299a577

## The call

A bot/agent about to buy this token calls preflight first:

```bash
curl "http://<preflight-host>/v1/preflight?target=0x34a528da3b2ea5c6ad1796eba756445d1299a577&chain=avax&action=buy"
```

## The response — BLOCK

```json
{
  "cache": false,
  "chain": "avax",
  "engine": "rugbuster_v2",
  "latency_ms": 1888,
  "reasons": [
    "near_zero_deployer_balance",
    "less_than_10_holders",
    "mint_authority_enabled",
    "holder_concentration",
    "high_risk_score"
  ],
  "risk": 90,
  "target_type": "token",
  "verdict": "BLOCK"
}
```

**A bot enforcing this gate never calls the swap function when `verdict == "BLOCK"`.** Same
enforcement pattern as the Solana Shield: the block happens before signing, not after a loss.

Latency note: 1,888ms here is a cold call from a local dev machine to Railway's public
Postgres proxy over the internet. A warm cache hit (see below) drops to ~400ms, and a
same-region production deployment (internal `DATABASE_URL`, no public proxy hop) will be
faster still on both paths.

## Contrast — a legitimate token, same call shape

**WAVAX (Wrapped AVAX)** — `0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7`, the canonical
blue-chip Avalanche asset.

```bash
curl "http://<preflight-host>/v1/preflight?target=0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7&chain=avax&action=buy"
```

First call (token not yet in the live scan cache, kicks off a background scan):

```json
{
  "cache": false,
  "verdict": "WARN",
  "risk": 50,
  "reasons": ["unknown_token_scanning"],
  "latency_ms": 1005
}
```

Second call, ~6s later, cache warm:

```json
{
  "cache": true,
  "verdict": "ALLOW",
  "risk": 12,
  "reasons": [
    "token_name_readable_on_chain",
    "token_symbol_readable_on_chain",
    "decimals_value_is_within_normal_erc_20_range",
    "total_supply_readable_on_chain",
    "thin_liquidity",
    "strong_24h_volume_at_26_360_204",
    "24h_volatility_is_moderate_at_0_3"
  ],
  "latency_ms": 395
}
```

## Spectrum spot-check (2026-07-10, real `avax_scans` rows)

| Token | Address | DB label | Preflight verdict |
|---|---|---|---|
| Integrity DAO | `0x34a528da3b2ea5c6ad1796eba756445d1299a577` | DANGER | **BLOCK** |
| Gator Dont Play | `0x1a31a8fd8bacb64b32dbcdcf5b2215f58baf70c1` | DANGER | **BLOCK** |
| Nexus | `0x751ceba0aaeb09dcf6b69d1a93fd561b2633a6ca` | WARN | **WARN** |
| BITS | `0x48d64aef167ccc764b11d4ee6e657665c05eaec5` | GOOD | **ALLOW** |
| WAVAX | `0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7` | (not in dataset, blue-chip) | **ALLOW** |

Verdicts line up with the underlying scan labels across the full spectrum, not just the one
headline BLOCK case.
