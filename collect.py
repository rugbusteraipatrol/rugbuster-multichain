#!/usr/bin/env python3
"""
collect.py - RugBuster Backtest Data Collector

Discover new Solana (or other chain) tokens using DexScreener endpoints,
query the RugBuster score API, and log the predictions to SQLite.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sqlite3
import time
from typing import Any

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
DEFAULT_API_BASE = "https://rugbuster-api-production.up.railway.app"
DB_NAME = "rugbuster_backtest.db"

# API Base URL from env
API_BASE = os.getenv("RUGBUSTER_SCORE_API_BASE", DEFAULT_API_BASE).rstrip("/")


def init_db() -> None:
    """Initialize the SQLite database schema if it does not exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chain TEXT NOT NULL,
            token_address TEXT UNIQUE NOT NULL,
            token_symbol TEXT,
            scan_date TEXT NOT NULL,
            predicted_label TEXT,
            predicted_risk INTEGER,
            api_status TEXT NOT NULL,
            raw_response TEXT,
            actual_outcome TEXT,
            outcome_checked_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def token_is_already_collected(token_address: str) -> bool:
    """Check if the token is already in the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM predictions WHERE token_address = ?", (token_address,)
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def fetch_latest_token_profiles(chain: str) -> list[dict[str, Any]]:
    """Fetch the latest token profiles from DexScreener API."""
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    print(f"[*] Querying DexScreener latest token profiles: {url}")
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        profiles = r.json()
        if not isinstance(profiles, list):
            return []
        # Filter by chain
        filtered = [p for p in profiles if str(p.get("chainId")).lower() == chain.lower()]
        print(f"[+] Found {len(filtered)} latest profiles matching chain '{chain}'")
        return filtered
    except Exception as e:
        print(f"[!] Failed to fetch token profiles: {e}")
        return []


def fetch_search_pairs(chain: str) -> list[dict[str, Any]]:
    """Fetch pairs matching a search query on DexScreener API."""
    url = f"https://api.dexscreener.com/latest/dex/search?q={chain}"
    print(f"[*] Querying DexScreener search endpoint: {url}")
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        pairs = data.get("pairs") or []
        # Filter and extract base token profiles
        tokens = []
        seen_addresses = set()
        for p in pairs:
            if str(p.get("chainId")).lower() == chain.lower():
                base_token = p.get("baseToken") or {}
                addr = base_token.get("address")
                symbol = base_token.get("symbol")
                if addr and addr not in seen_addresses:
                    seen_addresses.add(addr)
                    tokens.append({
                        "tokenAddress": addr,
                        "symbol": symbol
                    })
        print(f"[+] Extracted {len(tokens)} unique base tokens from search matching chain '{chain}'")
        return tokens
    except Exception as e:
        print(f"[!] Failed to fetch search pairs: {e}")
        return []


def query_rugbuster_score(address: str, chain: str) -> tuple[str, dict[str, Any] | None, str | None]:
    """
    Query the RugBuster API for a token's risk score.
    Returns: (api_status, raw_response_dict_or_none, error_message_or_none)
    """
    url = f"{API_BASE}/score?address={address}&chain={chain}"
    retries = 2
    delay = 2

    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=15)
            # Check response status
            if r.status_code == 200:
                try:
                    data = r.json()
                except ValueError:
                    return "api_error", None, f"Invalid JSON response: {r.text[:200]}"

                ok = data.get("ok")
                label = data.get("label")

                # If OK is true and we got a valid label
                if ok is True and label:
                    return "ok", data, None
                # If label is empty/missing or ok is false, mark as unknown / not cached
                else:
                    return "unknown_not_cached", data, None

            elif r.status_code == 400:
                # 400 bad request (e.g., chain mismatch or invalid address)
                try:
                    data = r.json()
                except ValueError:
                    data = {}

                err_msg = data.get("error", "")
                if "Invalid BNB Chain token address" in err_msg or "BNB Chain" in err_msg:
                    return "backend_not_ready", data, err_msg
                else:
                    return "unknown_not_cached", data, err_msg
            else:
                print(f"[!] API returned status code {r.status_code} (attempt {attempt + 1}/{retries + 1})")
        except requests.RequestException as e:
            print(f"[!] Connection failed to API: {e} (attempt {attempt + 1}/{retries + 1})")

        if attempt < retries:
            time.sleep(delay)

    return "api_error", None, "Max retries reached"


def save_prediction(
    chain: str,
    address: str,
    symbol: str | None,
    api_status: str,
    predicted_label: str | None,
    predicted_risk: int | None,
    raw_response: str | None
) -> None:
    """Save the prediction into the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now_str = datetime.datetime.utcnow().isoformat()
    try:
        cursor.execute(
            """
            INSERT INTO predictions (
                chain, token_address, token_symbol, scan_date,
                predicted_label, predicted_risk, api_status, raw_response
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chain, address, symbol, now_str, predicted_label, predicted_risk, api_status, raw_response)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Token already exists, ignore or log
        pass
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect newly launched tokens and record RugBuster predictions.")
    parser.add_argument("--chain", required=True, help="Chain to scan (e.g., solana, bnb, avax)")
    parser.add_argument("--limit", type=int, default=300, help="Number of unique tokens to collect predictions for")
    args = parser.parse_args()

    chain = args.chain.lower()
    limit = args.limit

    print(f"[*] Starting RugBuster Backtest Collector")
    print(f"[*] Chain: {chain}")
    print(f"[*] Limit: {limit}")
    print(f"[*] Using API Base: {API_BASE}")

    init_db()

    # Step 1: Discover candidate tokens
    candidates: list[dict[str, Any]] = []
    seen_addresses = set()

    # 1a. Latest Profiles
    profiles = fetch_latest_token_profiles(chain)
    for p in profiles:
        addr = p.get("tokenAddress")
        if addr and addr not in seen_addresses:
            seen_addresses.add(addr)
            candidates.append({
                "address": addr,
                "symbol": p.get("symbol") or "Unknown"
            })

    # 1b. Search Pairs (Fallback or complement)
    if len(candidates) < limit:
        search_tokens = fetch_search_pairs(chain)
        for s in search_tokens:
            addr = s.get("tokenAddress")
            if addr and addr not in seen_addresses:
                seen_addresses.add(addr)
                candidates.append({
                    "address": addr,
                    "symbol": s.get("symbol") or "Unknown"
                })

    # Keep querying profiles periodically if we still don't have enough candidates
    # (Only applies if limit is high, e.g. 300)
    polling_attempts = 0
    max_polling_attempts = 50
    while len(candidates) < limit and polling_attempts < max_polling_attempts:
        polling_attempts += 1
        print(f"[*] Need more candidates. Polling again in 10s... ({len(candidates)}/{limit})")
        time.sleep(10)
        profiles = fetch_latest_token_profiles(chain)
        new_found = 0
        for p in profiles:
            addr = p.get("tokenAddress")
            if addr and addr not in seen_addresses:
                seen_addresses.add(addr)
                candidates.append({
                    "address": addr,
                    "symbol": p.get("symbol") or "Unknown"
                })
                new_found += 1
        if new_found == 0:
            # If no new profiles, try another search query to get more
            time.sleep(2)
            search_tokens = fetch_search_pairs(chain)
            for s in search_tokens:
                addr = s.get("tokenAddress")
                if addr and addr not in seen_addresses:
                    seen_addresses.add(addr)
                    candidates.append({
                        "address": addr,
                        "symbol": s.get("symbol") or "Unknown"
                    })

    print(f"[+] Total discovered candidates: {len(candidates)}")
    print(f"[*] Proceeding to score up to {limit} tokens...")

    # Step 2: Score candidates
    scanned_count = 0
    api_status_counts: dict[str, int] = {
        "ok": 0,
        "unknown_not_cached": 0,
        "backend_not_ready": 0,
        "api_error": 0
    }
    label_distribution: dict[str, int] = {
        "GOOD": 0,
        "WARN": 0,
        "DANGER": 0
    }

    for idx, c in enumerate(candidates[:limit]):
        addr = c["address"]
        symbol = c["symbol"]

        print(f"\n[{idx + 1}/{min(len(candidates), limit)}] Scanning token {addr} ({symbol})...")

        # Skip if already in DB to avoid double charging / rate limits
        if token_is_already_collected(addr):
            print(f"[-] Token {addr} already exists in database. Skipping API call.")
            continue

        # Rate limiting pause
        time.sleep(1.5)

        status, response_data, error_msg = query_rugbuster_score(addr, chain)
        
        predicted_label = None
        predicted_risk = None
        raw_response = None

        if response_data:
            raw_response = json.dumps(response_data)
            predicted_label = response_data.get("label")
            predicted_risk = response_data.get("risk_score")

        print(f"[+] Result: status={status}, label={predicted_label}, risk={predicted_risk}")
        if error_msg:
            print(f"[!] Details: {error_msg}")

        # Update stats
        api_status_counts[status] = api_status_counts.get(status, 0) + 1
        if status == "ok" and predicted_label in label_distribution:
            label_distribution[predicted_label] += 1

        # Save to SQLite
        save_prediction(
            chain=chain,
            address=addr,
            symbol=symbol,
            api_status=status,
            predicted_label=predicted_label,
            predicted_risk=predicted_risk,
            raw_response=raw_response
        )
        scanned_count += 1

    print("\n" + "=" * 40)
    print(" COLLECTION SUMMARY")
    print("=" * 40)
    print(f"Total processed: {scanned_count}")
    print("API Status Counts:")
    for k, v in api_status_counts.items():
        print(f"  - {k}: {v}")
    print("Label Distribution (for status=ok):")
    for k, v in label_distribution.items():
        print(f"  - {k}: {v}")
    print("=" * 40)


if __name__ == "__main__":
    main()
