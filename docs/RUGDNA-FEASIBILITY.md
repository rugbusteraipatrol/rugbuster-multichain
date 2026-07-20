# RugDNA Feasibility

**Date:** 2026-07-20  
**Scope:** Read-only audit of the shared Railway PostgreSQL database (`blissful-cat`). No collector, production service, schema, blockchain state, or AVAX burn path was changed.

## Method

- PostgreSQL session was explicitly opened as `READ ONLY` and rolled back after every query.
- Queries used short statement timeouts (15-25 seconds). The only full-table operations were small `COUNT` / `GROUP BY label` aggregates on the five scan tables; no writes occurred.
- This report treats a repeated address as a **candidate repeated-risk creator**, not proof that a real-world person committed fraud. Stored labels include historical scanner behavior and must not be used as an accusation without independent review.

## Phase 1 - Available Data

All five tables have the same outer shape: `id`, `contract_address`, `chain`, `label`, `full_record` (`jsonb`), and `created_at`. The detailed evidence lives inside `full_record`.

| Chain | Table | Total records | DANGER records | Raw creator/deployer on DANGER | Structured raw funding addresses | Main retained fingerprint fields |
|---|---:|---:|---:|---:|---:|---|
| Avalanche | `avax_scans` | 8,893 | 1,291 | 1,244 valid EVM addresses | No; only `cia_funding_hops` scalar | creator, deployment-latency scalar, entropy, wash boolean, holder-age scalar, top-5 concentration %, backdoor function signatures/scores |
| BNB | `bnb_scans` | 6,528 | 392 | 0 | No; only `cia_funding_hops` scalar | Risk/confidence fields, scalar CIA/v6 fields, GoPlus-derived flags; creator is empty |
| Base | `base_scans` | 2,752 | 52 | 1 | No; only `cia_funding_hops` scalar | Scalar CIA/v6 fields, Base score/reasons; creator is almost always empty |
| Solana | `solana_scans` | 52,432 | 22,596 | 22,017 valid base58 addresses | No; only `cia_funding_hops` scalar | creator, mint, deployment-latency scalar, entropy, wash boolean, top-5 holder %, serial-rugger/pattern fields, backdoor fields |
| TRON | `tron_scans` | 89 | 4 | 0 | Yes, but only in 12/89 total records and none of the 4 DANGER rows | Nested CIA objects with statuses, raw `funders[]` entries when available, `deployer`, pair string, deploy/scan timestamps, v5/v6 objects |

### What is raw vs. derived

**Raw and directly matchable now**

- AVAX/Solana `creator` addresses are stored as valid addresses for most DANGER records.
- TRON can store raw `deployer` plus `cia.funding.funders[]` entries (`from`, amount, timestamp), but current coverage is poor: 13/89 rows have a deployer and 12/89 have non-empty funder arrays. The DANGER subset has neither.
- Contract/mint addresses and scan timestamps are retained everywhere through outer columns.

**Derived only, not sufficient for address-level matching**

- AVAX/BNB/Base/Solana funding uses `cia_funding_hops`, not the actual hop addresses.
- Holder data is a concentration percentage / age score, not a retained top-holder address list.
- Wash is a boolean or score; there is no retained transaction-edge graph on the EVM/Solana records.
- EVM/Solana deployment latency is a scalar; there are no retained deploy, first-liquidity, or exit event timestamps.
- TRON `pair` is a pair-address string, not LP history or a liquidity-event timeline.

### Data-quality notes relevant to fingerprints

| Chain | Useful values on DANGER records | Material limitation |
|---|---|---|
| AVAX | 870 have funding hops > 0; 1,138 have positive deployment latency; 309 have positive concentration; 57 have positive backdoor score | 153 latency values are negative; funding counterparties and holder addresses are absent |
| BNB | 119 have positive backdoor score | All 392 DANGER rows have empty creator, `cia_funding_hops=0`, negative latency, zero concentration and no positive wash flag |
| Base | 52 have positive concentration; 5 have positive backdoor score | 51/52 creators empty, no positive latency, no funding-hop signal |
| Solana | 1,910 have funding hops > 0; 10,694 positive latency; 13,061 positive concentration; 63 wash-positive | 7,781 latency values are negative; funding/holder counterparties are not retained |
| TRON | Raw funder array exists in 12 total rows; CIA status distinguishes `ok` from `unavailable` | 76/89 funding and latency modules are `unavailable`; all four DANGER rows lack deployer, funding, and deployment timestamp |

## Phase 2 - Exact-Match Probe

### A. Same creator on multiple DANGER tokens

The query used only valid address formats, excluded blank values, and required `COUNT(*) >= 2`.

| Chain | Valid DANGER creator coverage | Exact-match clusters (2+ tokens) | DANGER tokens inside clusters | Largest cluster |
|---|---:|---:|---:|---:|
| Avalanche | 1,244 / 1,291 | 13 | 1,237 | 573 |
| Solana | 22,017 / 22,596 | 2,101 | 18,765 | 382 |
| BNB | 0 / 392 | 0 | 0 | 0 |
| Base | 1 / 52 | 0 | 0 | 0 |
| TRON | 0 / 4 | 0 | 0 | 0 |

Representative clusters are below. They are **candidate repeated-risk creator clusters**, not confirmed criminal identities.

| Chain | Creator | DANGER tokens | First scan | Last scan | Scan-window span |
|---|---|---:|---|---|---:|
| AVAX | `0x1f6908b79ae1f2c87c16f0facc9084d93601c8eb` | 573 | 2026-06-23 | 2026-06-26 | 70.0 h |
| AVAX | `0xda8cf4c89480716367ec4c8216cd1f208cad9fb3` | 305 | 2026-06-29 | 2026-06-30 | 31.3 h |
| AVAX | `0x9190e5cc46cae753c13c4c07ea5ce8ba48edb275` | 239 | 2026-06-16 | 2026-06-17 | 21.5 h |
| Solana | `7FVfSdnR9VPGjMtmBP1Hz9C2DFTpoNX8gVVRmnimnGt9` | 382 | 2026-05-29 | 2026-07-15 | 47.1 d |
| Solana | `8gM4gnxdLdkvifM9TCwkGAxrnNw4NiSiHbAdE1RqY96e` | 270 | 2026-07-05 | 2026-07-20 | 15.0 d |
| Solana | `bwamJzztZsepfkteWRChggmXuiiCQvpLqPietdNfSXa` | 224 | 2026-06-02 | 2026-07-19 | 47.2 d |

This is the central positive result: the existing database already contains enough raw creator identity to build a first **deployer-memory** layer for AVAX and Solana without retroactively querying those chains.

### B. Same one-hop funding source across different deployers

**Not feasible for AVAX/BNB/Base/Solana from existing records.** Those chains retain only a hop count, not the source address.

TRON is the only current schema with a raw `funders[]` list. Across all 89 TRON rows, one source address appeared for two different deployers, but both linked tokens were `GOOD`/`WARN`, not DANGER. The DANGER rows have unavailable funding modules and blank deployers. Therefore there is no DANGER-quality funding-source cluster to report.

### C. Similar deploy -> liquidity -> exit rhythm

**Not feasible as stated.** AVAX/BNB/Base/Solana retain `created_at` and a derived deployment-latency scalar, not the three raw lifecycle event timestamps. `created_at` is scan/discovery time, so a burst of scans is not proof of a deploy/liquidity/exit rhythm.

The AVAX and Solana cluster windows above show scan cadence only. They are useful triage context, but cannot be promoted to lifecycle evidence.

### Cross-chain candidates

Exact matching of valid creator/deployer addresses across all five DANGER sets found **0 cross-chain candidates**. This is unsurprising: BNB/Base/TRON currently lack usable creator values; Solana and TRON use non-EVM address formats. Cross-chain matching will need funding-source, bridge, CEX-sweep, or behavioral fingerprints rather than raw creator equality alone.

## Factory Filter Results

The largest clusters were checked before treating them as creator-memory candidates. The check was intentionally conservative: AVAX used a read-only `eth_getCode` RPC call; Solana used read-only `getAccountInfo` and exact-address web/Solscan label searches. An executable Solana program or EVM bytecode is not automatically a factory: it is excluded only when there is evidence it is an infrastructure/platform contract.

| Chain | Address | DANGER tokens | Read-only evidence | Classification |
|---|---|---:|---|---|
| AVAX | `0x1f6908b79ae1f2c87c16f0facc9084d93601c8eb` | 573 | `eth_getCode = 0x` | VEROVATNO EOA |
| AVAX | `0xda8cf4c89480716367ec4c8216cd1f208cad9fb3` | 305 | `eth_getCode = 0x` | VEROVATNO EOA |
| AVAX | `0x9190e5cc46cae753c13c4c07ea5ce8ba48edb275` | 239 | `eth_getCode = 0x` | VEROVATNO EOA |
| AVAX | `0xbe76cd1bb72702ace2be58a9fce233722058d731` | 63 | `eth_getCode = 0x` | VEROVATNO EOA |
| AVAX | `0xb43120c4745967fa9b93e79c149e66b0f2d6fe0c` | 21 | 12,021 bytes of code; no reliable public verification/name recovered | NEJASNO (contract) |
| AVAX | `0x4226dd7419b1431f512d82a2c9e5fa1597fb1077` | 12 | `eth_getCode = 0x` | VEROVATNO EOA |
| AVAX | `0x141a593945004640fe19857c455d3e7a393a1835` | 8 | `eth_getCode = 0x` | VEROVATNO EOA |
| AVAX | `0x9ad6c38be94206ca50bb0d90783181662f0cfa10` | 4 | 11,088 bytes of code; public Avalanche/Trader Joe references identify it as the Joe factory | FACTORY/PLATFORM |
| AVAX | `0x1a267d3f9f5116df6ae00a4ad698cdcf27b71920` | 3 | `eth_getCode = 0x` | VEROVATNO EOA |
| AVAX | `0x91c2980ae13769093fbbd15699bc97fd79ab3096` | 3 | `eth_getCode = 0x` | VEROVATNO EOA |
| Solana | `7FVfSdnR9VPGjMtmBP1Hz9C2DFTpoNX8gVVRmnimnGt9` | 382 | System-owned, `executable=false`; no platform label found | VEROVATNO EOA |
| Solana | `8gM4gnxdLdkvifM9TCwkGAxrnNw4NiSiHbAdE1RqY96e` | 270 | System-owned, `executable=false`; no platform label found | VEROVATNO EOA |
| Solana | `bwamJzztZsepfkteWRChggmXuiiCQvpLqPietdNfSXa` | 224 | System-owned, `executable=false`; public sources describe a high-frequency pump.fun deployer wallet | VEROVATNO EOA |
| Solana | `AWGAwNm53RTSjxPEqxiYwwhXjcjLnMVFrd4gYK2scQT6` | 206 | System-owned, `executable=false`; deployer-list appearance, no program label | VEROVATNO EOA |
| Solana | `9RrKUhRpbPDNxR7x88ZsCgdtqPHUfwYPjj4JdpV4FBj9` | 202 | System-owned, `executable=false`; public wallet/trader profile, not a program | VEROVATNO EOA |
| Solana | `BuBMjNCr1UBpnPfywwAYcrjpSySzPDtGU5cNav2Y7SWU` | 197 | System-owned, `executable=false`; deployer-list appearance, no program label | VEROVATNO EOA |
| Solana | `EwNVgVLjVXbKfi1S1yh6T1MZr3SQ6QHPAoBtwi2cnqYE` | 188 | System-owned, `executable=false`; public launch feed names it as creator | VEROVATNO EOA |
| Solana | `DhSELHEnjs3rFyamjbfW5yxV1mm5kyDCJju2p7E3wgmy` | 184 | System-owned, `executable=false`; no platform label found | VEROVATNO EOA |
| Solana | `4UKLdTBiz6pGRccq9CGw9n53UwmAdd4UX1sJKeUohSiP` | 178 | System-owned, `executable=false`; public launch feed names it as creator | VEROVATNO EOA |
| Solana | `8eRqKaZProoVrmhUtCPtUotP3XT2xq9Pj7697jjoHiQB` | 166 | System-owned, `executable=false`; no platform label found | VEROVATNO EOA |

### Result after the conservative filter

- **Top-10 AVAX clusters:** 1 confirmed platform cluster (Trader Joe factory, 4 DANGER rows) excluded. **9 clusters / 1,227 DANGER rows remain**; one 21-token contract cluster is deliberately left `NEJASNO`, not counted as a person-level signal.
- **Top-10 Solana clusters:** 0 executable programs or labeled platform accounts. **10 clusters / 2,197 DANGER rows remain.**
- **All previously measured exact-creator clusters:** after excluding the one confirmed factory, the conservative lower bound is **2,113 clusters and 19,998 DANGER rows** (AVAX 12 / 1,233; Solana 2,101 / 18,765). This is not a claim that every remaining account belongs to one individual; it establishes that the signal is not explained away by the confirmed factory.

For the EOA candidates, the database shows strongly repeated behaviour. The three largest AVAX wallets account for 573 / 305 / 239 DANGER rows in 70.0 / 31.3 / 21.5 hours respectively. The ten Solana candidates range from 166 to 382 DANGER rows; stored average risk where available is 85.2-93.5%. Token names are available on the AVAX rows and show frequent brand/meme reuse; Solana records generally retain the name inside their `input` text rather than a normalized name field, so name-similarity needs a small normalizer before it can be reported reliably.

## Phase 3 - Gaps and MVP Work

| Gap | Why it blocks RugDNA | Smallest forward-looking fix | Effort |
|---|---|---|---|
| BNB creator is absent on all 392 DANGER rows | No identity key for exact deployer memory | Resolve and persist contract creator/creation transaction address at collection time | Medium |
| Base creator is absent on 51/52 DANGER rows | Same blocker as BNB | Same EVM creator extraction and persistence path | Medium |
| TRON DANGER deployer/timestamp modules are unavailable | No DANGER identity, no reliable funding/lifecycle fingerprint | Harden contract-creation lookup; persist deployer and creation timestamp with module status | Medium-high |
| EVM/Solana funding retains only hop count | Cannot link new wallets funded by the same source | Persist first-hop source address plus a bounded 3-hop normalized list/hash and status | Medium-high |
| No raw holder list | Cannot detect recurring holder clusters across token launches | Persist top 10-20 holder addresses and balances, or a privacy-preserving stable holder-cluster hash | Medium |
| No LP lifecycle events | Cannot test deploy -> liquidity -> exit cadence | Append first-liquidity, liquidity-removal and major-sell timestamps | High |
| Historical labels are not all equally reliable | A creator cluster can include historical false positives | Store classifier version, module availability, confidence, and only surface high-confidence/verified clusters | Small-medium |

### Retroactive enrichment potential

- **AVAX/Solana creator clustering:** already available; no chain calls needed for an MVP.
- **BNB/Base creator backfill:** plausible for the top 500 DANGER contracts using a contract-creation/explorer lookup. Roughly one primary lookup per contract plus retries/verification; moderate provider quota cost.
- **Funding backfill:** feasible but materially more expensive. A first-hop investigation commonly needs a deployer history lookup plus several transfer/transaction reads; a 3-hop graph for 500 tokens can easily become thousands to tens of thousands of provider reads. It should be rate-limited, cached, and started with exact creator clusters rather than every token.
- **Solana funding backfill:** creator is already present, but attribution of the funding wallet needs transaction-history/enriched-transaction reads. Start with the highest-volume creator clusters.
- **TRON backfill:** deployer and contract-creation retrieval can be retried from TronGrid/Tronscan history; funding enrichment is feasible only after deployer reliability is fixed.

## GO / NO-GO

**GO - constrained MVP.** Existing AVAX and Solana data already supports a useful deployer-memory feature:

1. On a new AVAX/Solana scan, obtain the creator exactly as today.
2. Query a private creator-history index for prior high-confidence DANGER/WARN tokens, count, first/last seen, and consistent retained signals.
3. Surface a cautious explanation such as: "Creator previously associated with *N* high-risk token scans; data confidence: X." Do not label a person a scammer.
4. Start with exact creator matches only. Add funding, holder and lifecycle graph matching after raw inputs are retained.

**No-go for a five-chain "serial scammer registry" today.** BNB, Base, and TRON are not yet identity-complete, and funding/lifecycle matching is unavailable in historical EVM/Solana records. The smallest high-value first step is therefore an AVAX + Solana **deployer-memory MVP**, with a clear confidence/provenance label, followed by creator persistence on BNB/Base/TRON.

## Reproducibility Notes

- Tables audited: `avax_scans`, `bnb_scans`, `base_scans`, `solana_scans`, `tron_scans`.
- Database timestamps observed: AVAX/Solana from 2026-05-29 through 2026-07-20; BNB from 2026-06-05; Base from 2026-07-06; TRON from 2026-07-08.
- The numbers in this document are a point-in-time read on 2026-07-20 and will naturally grow with collectors.
