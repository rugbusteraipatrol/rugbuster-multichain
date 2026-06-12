#!/usr/bin/env python3
"""
check_outcome.py - RugBuster Backtest Outcome Checker

Run 2-4 weeks after collection to verify what happened to each tracked token.
Checks DexScreener to determine if the token RUGGED, SURVIVED, or is UNCLEAR.
"""

from __future__ import annotations

import datetime
import sqlite3
import time
from typing import Any

import requests

# Constants
DB_NAME = "rugbuster_backtest.db"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens"


def get_tokens_to_check() -> list[tuple[int, str, str]]:
    """Retrieve all tokens with api_status = 'ok' and actual_outcome IS NULL."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, chain, token_address
        FROM predictions
        WHERE api_status = 'ok' AND actual_outcome IS NULL
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_token_outcome(token_id: int, outcome: str) -> None:
    """Update the actual_outcome and outcome_checked_at in the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cursor.execute(
        """
        UPDATE predictions
        SET actual_outcome = ?, outcome_checked_at = ?
        WHERE id = ?
        """,
        (outcome, now_str, token_id)
    )
    conn.commit()
    conn.close()


def fetch_dexscreener_data(address: str) -> dict[str, Any] | None:
    """Fetch token data from DexScreener API with retries."""
    url = f"{DEXSCREENER_API}/{address}"
    retries = 2
    delay = 2

    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
            else:
                print(f"[!] DexScreener returned status {r.status_code} (attempt {attempt + 1}/{retries + 1})")
        except requests.RequestException as e:
            print(f"[!] Connection to DexScreener failed: {e} (attempt {attempt + 1}/{retries + 1})")

        if attempt < retries:
            time.sleep(delay)

    return None


def determine_outcome(chain: str, data: dict[str, Any] | None) -> str:
    """
    Determine the actual outcome of the token: RUGGED, SURVIVED, or UNCLEAR.
    
    Rules:
    - RUGGED if:
        * No pairs are returned by DexScreener (or pairs array is empty)
        * Total liquidity across all pairs on the target chain is < $500
        * Price dropped 90%+ (indicated by priceChange metrics <= -90%)
    - SURVIVED if:
        * Has at least one pair on the target chain with liquidity > $1000
        * Has active trading volume in the last 24 hours (volume.h24 > 0)
    - UNCLEAR if:
        * Borderline case or ambiguous metrics.
    """
    if not data or not data.get("pairs"):
        # No pairs at all = RUGGED
        return "RUGGED"

    pairs = data.get("pairs") or []
    # Filter pairs matching the scan chain
    chain_pairs = [p for p in pairs if str(p.get("chainId")).lower() == chain.lower()]

    if not chain_pairs:
        # No pairs left on the scanned chain = RUGGED
        return "RUGGED"

    total_liquidity = 0.0
    total_volume_24h = 0.0
    max_price_drop = 0.0

    for p in chain_pairs:
        # Liquidity
        liq_usd = p.get("liquidity", {}).get("usd")
        if liq_usd is not None:
            total_liquidity += float(liq_usd)

        # Volume
        vol_24h = p.get("volume", {}).get("h24")
        if vol_24h is not None:
            total_volume_24h += float(vol_24h)

        # Price changes (m5, h1, h6, h24)
        price_change = p.get("priceChange") or {}
        for period in ["m5", "h1", "h6", "h24"]:
            val = price_change.get(period)
            if val is not None:
                change = float(val)
                if change < max_price_drop:
                    max_price_drop = change

    print(f"    - Stats: Liquidity=${total_liquidity:,.2f}, 24h Vol=${total_volume_24h:,.2f}, Max Drop={max_price_drop:.1f}%")

    # Check RUGGED conditions
    if total_liquidity < 500.0:
        return "RUGGED"
    if max_price_drop <= -90.0:
        return "RUGGED"

    # Check SURVIVED conditions
    if total_liquidity > 1000.0 and total_volume_24h > 0.0:
        return "SURVIVED"

    # Fallback to UNCLEAR if it fits neither clearly
    return "UNCLEAR"


def main() -> None:
    print("[*] Starting RugBuster Backtest Outcome Checker")
    
    tokens = get_tokens_to_check()
    total_to_check = len(tokens)
    print(f"[*] Found {total_to_check} tokens with status='ok' requiring outcome checks.")

    if total_to_check == 0:
        print("[+] No pending outcome checks. Exiting.")
        return

    rugged_count = 0
    survived_count = 0
    unclear_count = 0

    for idx, (token_id, chain, address) in enumerate(tokens):
        print(f"\n[{idx + 1}/{total_to_check}] Checking outcomes for token {address} on chain '{chain}'...")
        
        # Rate limiting delay
        time.sleep(1.5)

        data = fetch_dexscreener_data(address)
        outcome = determine_outcome(chain, data)
        
        print(f"    - Determined outcome: {outcome}")
        update_token_outcome(token_id, outcome)

        if outcome == "RUGGED":
            rugged_count += 1
        elif outcome == "SURVIVED":
            survived_count += 1
        else:
            unclear_count += 1

    print("\n" + "=" * 40)
    print(" OUTCOME CHECK SUMMARY")
    print("=" * 40)
    print(f"Total processed: {total_to_check}")
    print(f"  - RUGGED: {rugged_count}")
    print(f"  - SURVIVED: {survived_count}")
    print(f"  - UNCLEAR: {unclear_count}")
    print("=" * 40)


if __name__ == "__main__":
    main()
