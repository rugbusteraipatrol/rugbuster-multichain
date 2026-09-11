// Shared by the scanner pages: confirmed token identity and plain error text.
//
// Identity is shown beside a verdict, never instead of one. An entry is here
// only when the issuer itself publishes the exact address (source below, read
// 2026-09-11). A copy with the same name at another address gets nothing.
(() => {
  const IDENTITY = {
    avax: {
      "0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e": { symbol: "USDC", issuer: "Circle", source: "https://developers.circle.com/stablecoins/usdc-contract-addresses" },
      "0x9702230a8ea53601f5cd2dc00fdbc13d4df4a8c7": { symbol: "USDt", issuer: "Tether", source: "https://tether.to/en/supported-protocols" },
      "0x2b2c81e08f1af8835a78bb2a90ae924ace0ea4be": { symbol: "sAVAX", issuer: "BENQI", source: "https://docs.benqi.fi/resources/contracts/liquid-staking" }
    },
    base: {
      "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": { symbol: "USDC", issuer: "Circle", source: "https://developers.circle.com/stablecoins/usdc-contract-addresses" }
    }
  };

  function confirmedIdentity(chain, address) {
    const table = IDENTITY[String(chain || "").toLowerCase()] || {};
    return table[String(address || "").trim().toLowerCase()] || null;
  }

  function identityText(chain, address) {
    const id = confirmedIdentity(chain, address);
    if (!id) return "";
    return `Official ${id.symbol} address confirmed · Issuer: ${id.issuer}. This confirms who issued the token, not that its contract is safe; the verdict is separate.`;
  }

  // Raw API codes and fetch errors are not sentences. Map what users can act on.
  function friendlyScanError(err) {
    const raw = String((err && err.message) || err || "");
    if (/invalid .*address|unsupported address/i.test(raw)) {
      return "That is not a valid token address for this chain. Check the address and the selected chain.";
    }
    if (/not found on .*liquidity venues|token not found|no pairs/i.test(raw)) {
      return "No live market was found for this address on this chain, and our scanner could not complete the check. Check that the address and the selected chain are right, then try again.";
    }
    return "The check did not complete: our scanner could not read this token right now. That is a failure on our side, not a finding about the token. Try again in a minute.";
  }

  window.RugBusterShared = { confirmedIdentity, identityText, friendlyScanError };
})();
