# GRIOS v15 — Daily Editorial Intelligence Standard

## Mission

Replace numeric market dumps with a readable Persian daily intelligence briefing that explains what changed, why it may matter, how the effect can transmit across asset classes, what evidence supports the interpretation, and which investment candidates merit further work.

## Editorial rules

- Do not publish routine prices, percentages, raw scores, factor tables, contract counts, or technical indicator values in the Telegram body.
- Keep calculations internal. Translate their results into plain-language descriptions such as strengthening, weakening, crowded positioning, divergence, trend confirmation, or insufficient evidence.
- A news headline is not proof of causality. Distinguish verified facts, reported claims, market observations, and GRIOS interpretation.
- Never infer an institutional flow from a price move or from weekly CFTC positioning.
- Never call an ETF proxy an underlying spot or futures contract.
- If data is missing, stale, contradictory, or unavailable, say so and suppress the related opportunity.
- Every investment candidate must include its rationale, confirmation condition, and key invalidation/risk. Labels are research candidates, not personalized orders.
- Do not fabricate consensus, earnings, valuation multiples, release times, ETF flows, order-book data, or 13F holdings.

## Source hierarchy

### Primary / official

- Federal Reserve monetary-policy releases.
- SEC press releases and verified Company Facts / 13F records.
- EIA Today in Energy and official petroleum data.
- BIS media releases.
- CFTC Commitments of Traders datasets and stored, validated Futures Only snapshots.
- FRED official release-date calendar and macro observations.

### Established financial journalism

- Reuters, Bloomberg, CNBC, Wall Street Journal, Financial Times and Associated Press.

### Specialist context

- CoinDesk for digital-asset industry coverage.

News ingestion uses a rolling 72-hour RSS window, publisher attribution, publication timestamps, topic classification and duplicate suppression. A feed outage is non-blocking but reduces the report's evidence coverage. Headlines and RSS excerpts are not represented as full-article research; source links are provided for verification.

## Required market coverage

- Global equities: broad US indices, sectors, small caps, developed and emerging market proxies.
- Technology and AI infrastructure: semiconductors, cloud, data centers, networks, power and capex returns.
- Fixed income and credit: Treasury-duration ETFs, investment-grade and high-yield credit proxies, plus FRED yields.
- FX: ECB EUR crosses and the broad dollar reference series; no executable bid/ask claims.
- Commodities: gold, silver, copper/base metals, broad commodities and agriculture ETF proxies.
- Energy: oil/gas proxies and official EIA supply, stocks, refinery and product-supplied context.
- Digital assets: validated crypto universe and breadth; do not infer ETF flows without a verified flow source.
- Institutional positioning: latest validated CFTC Futures Only categories for equity-index, FX, gold, WTI and natural-gas contracts.
- SEC 13F: include only after a verified snapshot is available; always disclose its quarterly delay and long-position reporting limitations.

## Daily narrative structure

1. Main message and market regime.
2. Leading catalysts and cause/effect transmission across markets.
3. Equities, sectors, geography and AI.
4. Treasury yields, dollar, bonds and credit.
5. FX.
6. Energy, precious/industrial metals, agriculture and broad commodities.
7. Crypto.
8. CFTC participant positioning and SEC 13F availability.
9. Megatrends.
10. Bull/base/bear scenarios.
11. Conditional investment candidates and invalidation risks.
12. Economic calendar and what would change the view.
13. Source links and social footer.

## Opportunity discipline

- A trend alone is not a buy thesis.
- A headline alone is not a buy thesis.
- CFTC positioning is weekly exposure, not real-time flow; extreme positioning can be a crowding warning or a squeeze setup, not an automatic reversal signal.
- A proxy ETF's behavior is not the same as the underlying instrument.
- Without valuation and issuer-level fundamentals, equity ideas remain watchlist candidates, not valuation-backed buy recommendations.
- If evidence does not converge, cash / waiting is a valid conclusion.

## Technical implementation

- `market_news.py`: RSS news retrieval and evidence metadata.
- `cftc_context.py`: read-only, service-role Supabase query for fresh CFTC Futures Only records.
- `daily_narrative_report.py`: Persian editorial synthesis and conditional opportunity screen.
- `scanner.py`: passes the current macro calendar, news and CFTC context to the renderer.
- `market-pulse/.github/workflows/grios-data-hub-scan.yml`: builds news and CFTC context before the daily scan; collectors are non-blocking; the integrated report is published once.

The current synthesis is deterministic and rule-based. It does not scrape paywalled article bodies or call a hosted generative model. This limitation is intentional until a separately approved model service and credentials are available.
