# Iran Market Data Operating Addendum

Reviewed 2026-11-17 against the user-supplied `iran-mcp` v2.3 archive.

## Verified from archive catalog (not live-tested)

The catalog lists read-only tools for:

- **TGJU:** free-market FX, gold, coins, summary tables and daily history (`tj_market_summary`, `tj_get_prices`, `tj_price_history`).
- **TSETMC:** symbols/quotes/history, movers, order book, indices and real/legal flows (`ts_search_symbols`, `ts_get_quote`, `ts_price_history`, `ts_market_movers`, `ts_indices`, `ts_real_legal`).
- **CBI:** official FX references in Rial per currency unit, inflation, liquidity, policy rates and bond auction results.
- **Complementary context:** Fara Bourse bonds/yields/market summaries, FIPIRAN fund NAV/returns/flows and indices, IME commodity trading/supply, and Codal company disclosures.

The archive is a catalog and documentation package; it does not include the server source implementations/submodules. The documented package servers are generally unofficial Python stdio MCP servers that call undocumented site APIs. Some sites answer only from Iranian IPs and document optional per-server proxy settings. A tool's presence in this archive does not demonstrate that it is installed, reachable, fresh, entitled for redistribution, or connected to GRIOS. No dedicated NIMA/transactional FX source is identified in the catalog.

## Source options checked 2026-11-17

| Source | Useful coverage | Access and cost | Suitability / limits |
| --- | --- | --- | --- |
| [TSETMC CDN](https://cdn.tsetmc.com/api) | Broad market watch, quotes, order books, history, indices and individual/legal flows. | Public endpoints are described by reverse-engineered clients; no stable public API contract or redistribution license was verified. May block non-Iranian IPs. | Strongest breadth and native exchange identity, but operationally brittle. Do not build a public commercial feed on it without written permission and a robust locally hosted collector. |
| [Tindex API](https://tindex.app/en/developers/) | Tehran equities, market indicators, FX, news, inflation and broader indicators. | Vendor currently documents a free account/token, Bearer authentication, 3 requests/minute and 300/day on free tier. | Good low-volume evaluation candidate. Public docs do not establish freshness per every dataset or permission to redistribute raw/derived data to followers; obtain written confirmation before public posts. |
| [FundAI API](https://fundai.ir/developers) | Market-wide watch, quote/history, depth, trading state, flows, screeners, Codal statements/monthly sales, company ratios and commodity trades. | Account API key, credit-based; docs provide 100 trial credits with first key, endpoint costs and rate limits. | Most complete single API surfaced in this check. Its docs list daily prices/indicators/indexes/market flows/trading state/depth/trades as commercial-use exceptions. The screener itself is not listed in that exception, and publication of derived recommendations from it is not established. |
| [Codal](https://www.codal.ir/) | Official issuer disclosures, financial statements, monthly activity, material events. | Public website; the Codal MCP docs describe an unofficial client over undocumented search endpoints, no API key, with regional access and rate limits. | Primary source for company disclosures, not quotes/history. Link/cite original filing and publication date; do not republish whole reports without rights. |
| `iran-mcp` package set | MCP wrappers for TSETMC, Codal, FIPIRAN, IFB, CBI, IME, TGJU. | Mostly `uvx` stdio packages, unofficial, undocumented source APIs, sometimes Iranian IP/proxy required. | Useful for analyst-assisted research; does not by itself give the scheduled scanner a persistent service or a public redistribution license. |

The Tindex and FundAI terms, quotas, endpoint availability, vendor identity, and permissions must be rechecked at onboarding. FundAI's developer docs were reviewed on 2026-11-17; the user's key was live-tested for `/me/`, market flow and three individual histories, but the redesigned screener path has not yet been live-tested. A website's statement that rates update “live” is not proof of exchange-grade timestamps or delivery latency.

## Daily report and opportunity rules

- Keep conventional listed shares outside the global trade universe. Iranian listed shares may be considered only in a distinct **Iran market** section.
- Preserve TSETMC ticker and ISIN when available, market/board, session, quote currency/unit (TSETMC prices are cataloged as Rial), source timestamp, retrieval timestamp and freshness. Retain the native Jalali date and a validated Gregorian equivalent where available.
- Show market breadth and real/legal flow as observed aggregates with their date and methodology; they do not prove insider or institutional intent. A price-only snapshot is data context, not an opportunity.
- Never merge exchange rates: CBI official reference (Rial/currency unit), explicitly sourced transactional/NIMA rate, and TGJU free-market quote must be separate series. If a source does not name the rate type, label it unknown and do not substitute it for another series.
- Gold/coin opportunities require exact product (18k gram, ounce, or named coin), native unit, provider timestamp, history and, where available, spread/fees. Keep quote-only observations as DATA_ONLY.
- Macro and flows (CBI inflation/liquidity/policy rates, government auction yields, IME commodity volumes, FIPIRAN flows, Codal disclosures) require publication/observation date and release lag. Do not use publication time as observation time or imply real-time availability.
- No candidate is ranked if source identity, symbol mapping, unit, timestamp, freshness or required history is missing. On timeout, RPC/HTTP error, region block, malformed response, stale/future timestamp or unknown unit, print the Iran section as unavailable and do not fall back silently.
- Public social publication (Telegram, Instagram, X/Twitter, LinkedIn, Medium, Substack) requires a provider entitlement that explicitly allows the relevant redistribution/display and derived analyses. The report must identify source and as-of time, distinguish facts from analysis, include key risks/invalidation, and must not say “buy” as a personalized instruction or imply guaranteed returns. If permission is unclear, keep the report private and link to the original source rather than republishing a feed.

## Integration status

The `apps/iran_market_daily/` FundAI adapter is changing from a fixed three-symbol pilot to a broad-market first pass: screen for positive latest-session individual money flow, then validate up to three distinct non-halted candidates against 30 adjusted daily sessions. Expected cost is 58 credits per run (25 for the screen's first 20 results, up to 18 for three histories, 15 for market flow), with a once-per-day spend guard and Thursday/Friday skips. This is not an exhaustive whole-market ranking, and fewer than three may pass evidence gates. The screener path has not been live-tested; broad-market ingestion is not confirmed operational. Credentials and `.last_paid_scan.json` are excluded from Git.

Live verification on 2026-11-17: FundAI `/me/` returned HTTP 200 and a non-Sandbox account. A market-flow request returned dated market breadth and net individual flow. The three sample-symbol price histories were fetched, but a leftover 60-close code check rejected them; no valid candidate was produced. That bug was fixed and a synthetic 30-session check passed. The paid run consumed 33 credits. The broad-market screener redesign is not yet live-tested and has produced no validated live candidate. Do not claim the new coverage is operational until the next eligible run verifies response schema, freshness, candidate history and actual credit charge.

The daily Codex report is scheduled for 09:00 Asia/Tehran in this conversation. It should produce up to three private research candidates from the broad-market screen, but return fewer or none when evidence gates fail; never pad the list to reach a minimum count. It does not publish to Telegram, Instagram, X, LinkedIn, Medium or Substack. The score is experimental, without Codal fundamentals or a backtest. Public redistribution rights for screener-derived analysis are not established. The automation must report no qualified candidates when data fail quality gates.
